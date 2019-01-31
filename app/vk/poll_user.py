# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from PIL import Image
from io import BytesIO
from hashlib import sha1
from app.utils.vk_sign_data import sign_data
from app.utils.markup_fixes import markup_multipurpose_fixes
from app import config
from operator import itemgetter
import requests
import asyncio
import logging


def poll_user(user, user_id, bot):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        telegram_user_id = int(user_id.split(":")[1])
        logging.debug("Выполняется polling пользователя c ID: {0}".format(user_id))

        try:
            assert user['VK_TOKEN']
            assert user['VK_SECRET']
        except (KeyError, TypeError):
            return {"status": "ERROR", "details": "У пользователя указан неверный VK токен (или он отстутствует)"}

        try:
            assert user['VK_LP_KEY']
            assert user['VK_LP_SERVER']
            assert user['VK_LP_PTS']
        except (KeyError, TypeError):
            logging.debug("У пользователя {0} нет данных о LongPoll сервере.".format(user_id))

            data = {"need_pts": 1, "lp_version": 3, "access_token": user['VK_TOKEN'], "v": "5.92"}
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

            # Проверяем сообщение на наличие вложений в сообщении
            for attachment in message['attachments']:
                if attachment['type'] == "photo":
                    photos = []
                    photo_sorted_sizes = sorted(attachment['photo']['sizes'], key=itemgetter('width'))
                    photos.extend([InputMediaPhoto(photo_sorted_sizes[-1]['url'])])

                    bot.send_media_group(telegram_user_id, photos)
                if attachment['type'] == "sticker":
                    sticker_hash = sha1(attachment['sticker']['images'][4]['url'].encode("UTF-8")).hexdigest()
                    sticker_file_id = asyncio.get_event_loop().run_until_complete(
                        redis.execute("HGET", "stickers:{0}".format(sticker_hash), "FILE_ID"))['details']

                    if sticker_file_id:
                        logging.debug("Sticker with hash {0} is in cache, sending it by file id.".format(sticker_hash))

                        bot.send_sticker(telegram_user_id, sticker=sticker_file_id)
                    else:
                        logging.debug("Sticker with hash {0} not found, creating it.".format(sticker_hash))

                        sticker_png = Image.open(BytesIO(requests.get(attachment['sticker']['images'][4]['url'], stream=True).raw))
                        sticker_webp = BytesIO()
                        sticker_png.save(sticker_webp, format="WEBP", lossless=True, quality=100, method=6)
                        sticker_webp.seek(0)

                        sticker = bot.send_sticker(telegram_user_id, sticker=sticker_webp)
                        asyncio.get_event_loop().run_until_complete(
                            redis.execute("HSET", "stickers:{0}".format(sticker_hash), "FILE_ID", sticker.sticker.file_id))

            sender = [sender for sender in response_lph['profiles'] if sender['id'] == message['from_id']][0]
            if message['text']:
                message_text = "*{0} {1}*\n\n{2}".format(sender['first_name'], sender['last_name'],
                                                         markup_multipurpose_fixes(message['text']))
            else:
                message_text = "*{0} {1}*".format(sender['first_name'], sender['last_name'])

            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Подробнее", callback_data="TEST")]])
            message_data = bot.send_message(telegram_user_id, message_text, reply_markup=markup, parse_mode="Markdown")

            # TODO: Возвратить, когда будет нужно
            # tg_message_id = str(message_data.chat.id) + "_" + str(message_data.message_id)
            # vk_message_id = str(message['peer_id']) + "_" + str(message['conversation_message_id'])
            # await redis.execute("HSET", "messages:{0}".format(tg_message_id), "VK_MESSAGE_ID", vk_message_id)
            # await redis.execute("EXPIRE", "messages:{0}".format(tg_message_id), config.MESSAGE_CACHE_TIME)

        asyncio.get_event_loop().run_until_complete(redis.execute("HSET", user_id, "VK_LP_PTS", response_lph['new_pts']))
        return {"status": "OK", "details": None}
    except Exception as e:
        logging.error("Произошла ошибка при поллинге аккаунта VK пользователя {0}.".format(user_id), exc_info=True)
        return e
