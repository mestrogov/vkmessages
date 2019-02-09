# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from pyrogram import InputMediaPhoto, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from io import BytesIO
from hashlib import sha1
from app.utils.redis_hgetall import redis_hgetall as hgetall
from app.vk.utils.sign_data import sign_data
from app.vk.utils.markup_fixes import markup_multipurpose_fixes
from tempfile import NamedTemporaryFile
from operator import itemgetter
import requests
import asyncio
import logging


def poll_user(user, user_id, client):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        telegram_user_id = int(user_id.split(":")[1])
        logging.debug("Выполняется polling пользователя c ID: {0}".format(user_id))

        try:
            assert user['VK_TOKEN']
            assert user['VK_SECRET']
        except (AssertionError, KeyError, TypeError):
            return {"status": "ERROR", "details": "У пользователя указан неверный VK токен (или он отстутствует)"}

        try:
            assert user['VK_LP_KEY']
            assert user['VK_LP_SERVER']
            assert user['VK_LP_PTS']
        except (AssertionError, KeyError, TypeError):
            logging.debug("У пользователя {0} нет данных о LongPoll сервере.".format(user_id))

            data = {"need_pts": 1, "lp_version": 3, "access_token": user['VK_TOKEN'], "v": 5.92}
            response_lps = requests.post("https://api.vk.com/method/messages.getLongPollServer",
                                         data=sign_data(data, "messages.getLongPollServer", user['VK_SECRET'])).json()
            logging.debug("Ответ на запрос метода messages.getLongPollServer: " + str(response_lps))
            response_lps = response_lps['response']

            user['VK_LP_KEY'] = response_lps['key']
            user['VK_LP_SERVER'] = response_lps['server']
            user['VK_LP_PTS'] = response_lps['pts']
            asyncio.get_event_loop().run_until_complete(
                redis.execute("HSET", user_id, "VK_LP_KEY", response_lps['key'], "VK_LP_SERVER", response_lps['server'],
                              "VK_LP_PTS", response_lps['pts']))

        data = {"key": user['VK_LP_KEY'], "server": user['VK_LP_SERVER'], "pts": user['VK_LP_PTS'],
                "fields": "screen_name", "mode": 2, "lp_version": 3, "access_token": user['VK_TOKEN'], "v": 5.92}
        response_lph = requests.post("https://api.vk.com/method/messages.getLongPollHistory",
                                     data=sign_data(data, "messages.getLongPollHistory", user['VK_SECRET'])).json()
        logging.debug("Ответ на запрос метода messages.getLongPollHistory: " + str(response_lph))
        response_lph = response_lph['response']

        for message in response_lph['messages']['items']:
            if int(message['out']) == 1:
                continue
            message_id = "{0}_{1}".format(message['peer_id'], message['conversation_message_id'])

            # Проверяем сообщение на наличие вложений в сообщении
            media = []
            # TODO: Добавить chat_action (загрузка видео, аудио)
            for attachment in message['attachments']:
                if attachment['type'] == "photo":
                    photo_sorted_sizes = sorted(attachment['photo']['sizes'], key=itemgetter('width'))
                    with NamedTemporaryFile(suffix=".jpg", delete=False) as photo:
                        photo.write(requests.get(photo_sorted_sizes[-1]['url'], stream=True).content)
                        media.extend([InputMediaPhoto(photo.name)])
                if attachment['type'] == "video":
                    # Получаем видео, которое сможем загрузить при лимите в 1.5 ГБ
                    video_url = None
                    for video_quality in attachment['video']['files']:
                        if video_quality == "hls" or video_quality == "external":
                            continue
                        video_size = int(requests.get(attachment['video']['files'][video_quality], stream=True).
                                         headers['Content-length'])
                        if video_size < 1500 * 1024 * 1024:
                            video_url = attachment['video']['files'][video_quality]
                    if not video_url:
                        continue

                    video_hash = sha1(video_url.split("?extra")[0].encode("UTF-8")).hexdigest()
                    video = asyncio.get_event_loop().run_until_complete(hgetall("files:video:{0}".format(video_hash)))

                    if not video:
                        logging.debug("Видео ({0}) не найдено в кэше, загружается новое.".format(video_hash))
                        with NamedTemporaryFile(suffix=".mp4") as video_file:
                            logging.debug("Видео ({0}) сохраняется во временный файл {1}.".format(
                                video_hash, video_file.name))
                            video_file.write(requests.get(video_url, stream=True).content)

                            # Отправляем видео и сразу удаляем (это необходимо, чтобы получить File ID видео)
                            video_message = client.send_video(telegram_user_id, video_file.name,
                                                              disable_notification=True)
                            client.delete_messages(telegram_user_id, video_message.message_id)

                            video['FILE_ID'] = video_message.video.file_id
                            video['CAPTION'] = attachment['video']['title']

                        asyncio.get_event_loop().run_until_complete(redis.execute(
                            "HSET", "files:video:{0}".format(video_hash), "FILE_ID", video['FILE_ID'],
                            "CAPTION", video['CAPTION']))

                    media.extend([InputMediaVideo(video['FILE_ID'], caption=video['CAPTION'])])
                # TODO: Добавить поддержку плейлистов (корректное отображение)
                if attachment['type'] == "audio":
                    audio_hash = sha1(attachment['audio']['url'].encode("UTF-8")).hexdigest()
                    audio = asyncio.get_event_loop().run_until_complete(
                        redis.execute("HGET", "files:audio:{0}".format(audio_hash), "FILE_ID"))['details']

                    # В Redis нет смысла сохранять исполнителя и название песни, так как при последующей отправке по
                    # File ID, данные об исполнителе и названии песни остаются.
                    if audio:
                        logging.debug("Аудио ({0}) находится в кэше, отправляется по File ID.".format(audio_hash))
                        client.send_audio(telegram_user_id, audio)
                    else:
                        logging.debug("Аудио ({0}) не найдено в кэше, загружается новое.".format(audio_hash))
                        # VK может вернуть пустое URL, проверяем это сначала
                        if not attachment['audio']['url']:
                            logging.debug("Аудио, которое было отправлено пользователю, не может быть загружено, "
                                          "так как в нем не содержится ссылки (скорее всего, оно защищено "
                                          "авторскими правами и может воспроизводиться только из РФ).")
                            client.send_message(telegram_user_id,
                                                "❗ Аудио ({0} — {1}) не может быть отправлено вам, так как "
                                                "оно защищено авторскими правами и может воспроизводиться только с "
                                                "территории Российской Федерации.".format(
                                                    attachment['audio']['title'], attachment['audio']['artist']))
                            continue

                        with NamedTemporaryFile(suffix=".mp3") as audio_file:
                            logging.debug("Аудио ({0}) сохраняется во временный файл {1}.".format(
                                audio_hash, audio_file.name))
                            audio_file.write(requests.get(attachment['audio']['url'], stream=True).content)
                            audio = client.send_audio(telegram_user_id, audio_file.name,
                                                      performer=attachment['audio']['artist'],
                                                      title=attachment['audio']['title']).audio.file_id

                        asyncio.get_event_loop().run_until_complete(
                            redis.execute("HSET", "files:audio:{0}".format(audio_hash), "FILE_ID", audio))
                if attachment['type'] == "sticker":
                    sticker_hash = sha1(attachment['sticker']['images'][4]['url'].encode("UTF-8")).hexdigest()
                    sticker = asyncio.get_event_loop().run_until_complete(
                        redis.execute("HGET", "files:sticker:{0}".format(sticker_hash), "FILE_ID"))['details']

                    if sticker:
                        logging.debug("Стикер ({0}) находится в кэше, отправляется по File ID.".format(sticker_hash))
                        client.send_sticker(telegram_user_id, sticker)
                    else:
                        logging.debug("Стикер ({0}) не найден в кэше, загружается новый.".format(sticker_hash))
                        sticker_png = Image.open(
                            BytesIO(requests.get(attachment['sticker']['images'][4]['url'], stream=True).content))

                        with NamedTemporaryFile() as sticker_file:
                            logging.debug("Стикер ({0}) сохраняется во временный файл {1}.".format(
                                sticker_hash, sticker_file.name))
                            sticker_png.save(sticker_file, format="WEBP", lossless=True, quality=100, method=6)
                            sticker = client.send_sticker(telegram_user_id, sticker_file.name).sticker.file_id

                        asyncio.get_event_loop().run_until_complete(
                            redis.execute("HSET", "files:sticker:{0}".format(sticker_hash), "FILE_ID", sticker))

            # Проверяем, есть ли какое-то медиа (фотографии, видео)
            if media:
                client.send_media_group(telegram_user_id, media)

            sender = [sender for sender in response_lph['profiles'] if sender['id'] == message['from_id']][0]
            formatted_message_text = markup_multipurpose_fixes(message['text'])
            message_text = "**{0} {1}**{2}".format(sender['first_name'], sender['last_name'],
                                                   # Если есть текст в сообщении, то добавляем его в сообщении
                                                   "\n\n" + formatted_message_text if formatted_message_text else "")

            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Подробнее", callback_data=b"TEST")]])
            message_data = client.send_message(telegram_user_id, message_text, reply_markup=markup)

            asyncio.get_event_loop().run_until_complete(
                redis.execute("SET", "message:telegram:{0}_{1}".format(message_data.chat.id, message_data.message_id),
                              message_id)
            )

        asyncio.get_event_loop().run_until_complete(redis.execute("HSET", user_id,
                                                                  "VK_LP_PTS", response_lph['new_pts']))
        return {"status": "OK", "details": None}
    except Exception as e:
        logging.error("Произошла ошибка при polling'е аккаунта VK пользователя {0}.".format(user_id), exc_info=True)
        return e
