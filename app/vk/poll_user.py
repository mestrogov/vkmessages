# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from operator import itemgetter
from time import sleep
import asyncio
import logging


async def poll_user(user, user_id, bot, session):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logging.debug("Entered poll_user method, user: {0}, user_id: {1}".format(user, user_id))

        try:
            user['VK_TOKEN']
        except (KeyError, TypeError):
            return {"status": "ERROR", "details": "У пользователя нет токена VK"}
        try:
            user['VK_LP_KEY']
            user['VK_LP_SERVER']
            user['VK_LP_PTS']
        except (KeyError, TypeError):
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

            # Проверяем сообщение на наличие вложений
            num = 0
            photos = []
            for attachment in message['attachments']:
                if attachment['type'] == "photo":
                    photo_sorted_sizes = sorted(message['attachments'][num]['photo']['sizes'], key=itemgetter('width'))
                    photos.extend([InputMediaPhoto(photo_sorted_sizes[-1]['url'])])
                num += 1

            sender = [sender for sender in response_lp['profiles'] if sender['id'] == message['from_id']][0]
            message_text = "*{0} {1}*\n> {2}".format(sender['first_name'], sender['last_name'], message['text'])

            # Проверяем наличие фото, если есть, то отправляем отдельным сообщением
            if photos:
                bot.send_media_group(int(user_id.split(":")[1]), photos)

            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Подробнее", callback_data="TEST")]])
            message_data = bot.send_message(int(user_id.split(":")[1]), message_text, reply_markup=markup,
                                            parse_mode="Markdown")

            tg_message_id = str(message_data.chat.id) + "_" + str(message_data.message_id)
            vk_message_id = str(message['peer_id']) + "_" + str(message['conversation_message_id'])
            await redis.execute("HSET", "messages:{0}".format(tg_message_id), "VK_MESSAGE_ID", vk_message_id)
            await redis.execute("EXPIRE", "messages:{0}".format(tg_message_id), 86400)

            sleep(0.1)
        await session.close()
    except Exception as e:
        logging.error("Произошла ошибка при поллинге аккаунта VK пользователя {0}.".format(user_id), exc_info=True)
        return e
