# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from PIL import Image
from io import BytesIO
from hashlib import sha1
from app.utils.markup_fixes import markup_multipurpose_fixes
from app import config
from operator import itemgetter
import asyncio
import logging


async def poll_user(user, user_id, bot, session):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tg_user_id = int(user_id.split(":")[1])
        logging.debug("Entered poll_user method, user: {0}, user_id: {1}".format(user, user_id))

        try:
            assert user['VK_TOKEN']
        except (KeyError, TypeError):
            return {"status": "ERROR", "details": "У пользователя нет токена VK"}

        try:
            assert user['VK_LP_KEY']
            assert user['VK_LP_SERVER']
            assert user['VK_LP_PTS']
        except (KeyError, TypeError):
            logging.debug("У пользователя {0} нет данных о LongPoll сервере; запрашиваю.".format(user_id))
            async with session.post("https://api.vk.com/method/messages.getLongPollServer", params={
                                    "access_token": user['VK_TOKEN'], "need_pts": 1, "lp_version": 3, "v": "5.92"}) as response_lps:
                logging.debug("Returned response for getLongPollServer: " + str(await response_lps.json()))
                response_lps = (await response_lps.json())['response']
                user['VK_LP_KEY'] = response_lps['key']
                user['VK_LP_SERVER'] = response_lps['server']
                user['VK_LP_PTS'] = response_lps['pts']
                await redis.execute("HSET", user_id, "VK_LP_KEY", response_lps['key'],
                                    "VK_LP_SERVER", response_lps['server'], "VK_LP_PTS", response_lps['pts'])

        async with session.get("https://api.vk.com/method/messages.getLongPollHistory",
                               params={"access_token": user['VK_TOKEN'], "key": user['VK_LP_KEY'],
                                       "server": user['VK_LP_SERVER'], "pts": user['VK_LP_PTS'],
                                       "mode": 2, "fields": "screen_name", "lp_version": 3, "v": "5.92"}) as response_lp:
            logging.debug("Returned response for getLongPollHistory: " + str(await response_lp.json()))
            response_lp = (await response_lp.json())['response']
            await redis.execute("HSET", user_id, "VK_LP_PTS", response_lp['new_pts'])

        for message in response_lp['messages']['items']:
            if int(message['out']) == 1:
                continue

            # Проверяем сообщение на наличие вложений в сообщении
            photos = []
            for attachment in message['attachments']:
                if attachment['type'] == "photo":
                    photo_sorted_sizes = sorted(attachment['photo']['sizes'], key=itemgetter('width'))
                    photos.extend([InputMediaPhoto(photo_sorted_sizes[-1]['url'])])
                if attachment['type'] == "sticker":
                    sticker_hash = sha1(attachment['sticker']['images'][4]['url'].encode("UTF-8")).hexdigest()
                    sticker_file_id = (await redis.execute("HGET", "stickers:{0}".format(sticker_hash), "FILE_ID"))['details']

                    if sticker_file_id:
                        logging.debug("Sticker with hash {0} is in cache, sending it by file id.".format(sticker_hash))

                        bot.send_sticker(tg_user_id, sticker=sticker_file_id)
                    else:
                        logging.debug("Sticker with hash {0} not found, creating it.".format(sticker_hash))

                        sticker_png = Image.open(BytesIO(await (await session.get(attachment['sticker']['images'][4]['url'])).read()))
                        sticker_webp = BytesIO()
                        sticker_png.save(sticker_webp, format="WEBP", lossless=True, quality=100, method=6)
                        sticker_webp.seek(0)

                        sticker = bot.send_sticker(tg_user_id, sticker=sticker_webp)
                        await redis.execute("HSET", "stickers:{0}".format(sticker_hash), "FILE_ID", sticker.sticker.file_id)

            sender = [sender for sender in response_lp['profiles'] if sender['id'] == message['from_id']][0]
            if message['text']:
                message_text = "*{0} {1}*\n\n{2}".format(sender['first_name'], sender['last_name'],
                                                         markup_multipurpose_fixes(message['text']))
            else:
                message_text = "*{0} {1}*".format(sender['first_name'], sender['last_name'])

            # Проверяем наличие фото, если есть, то отправляем отдельным сообщением
            if photos:
                bot.send_media_group(tg_user_id, photos)

            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Подробнее", callback_data="TEST")]])
            message_data = bot.send_message(tg_user_id, message_text, reply_markup=markup, parse_mode="Markdown")

            tg_message_id = str(message_data.chat.id) + "_" + str(message_data.message_id)
            vk_message_id = str(message['peer_id']) + "_" + str(message['conversation_message_id'])
            await redis.execute("HSET", "messages:{0}".format(tg_message_id), "VK_MESSAGE_ID", vk_message_id)
            await redis.execute("EXPIRE", "messages:{0}".format(tg_message_id), config.MESSAGE_CACHE_TIME)

        await session.close()
    except Exception as e:
        logging.error("Произошла ошибка при поллинге аккаунта VK пользователя {0}.".format(user_id), exc_info=True)
        return e
