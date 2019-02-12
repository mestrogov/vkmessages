# -*- coding: utf-8 -*-

from app import logging
from app.utils.redis_hgetall import redis_hgetall as hgetall
from app.remote.redis import Redis as redis
from app import config as config
from app.vk.utils.sign_data import sign_data
from app.telegram.utils.parse_sticker import parse_sticker
from secrets import randbits
import requests
import logging
import asyncio


def message_handler(client, message):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assert message.reply_to_message
        except AssertionError:
            return
        tg_message_id = "{0}_{1}".format(message.reply_to_message.chat.id, message.reply_to_message.message_id)
        vk_message_id = asyncio.get_event_loop().run_until_complete(
            redis.execute("GET", "message:telegram:{0}".format(tg_message_id)))['details']
        if not vk_message_id:
            logging.debug("Сообщение, на которое ответил пользователь, не содержит ID сообщения из VK.")
            if config.DEVELOPER_MODE:
                message.reply("ℹ️ К сообщению, на которое вы ответили, не привязано ID сообщения из VK.",
                              disable_notification=True)
            return

        user = asyncio.get_event_loop().run_until_complete(hgetall("user:{0}".format(message.from_user.id)))
        peer_id = vk_message_id.split("_")[0]

        try:
            assert message.sticker.file_id
            parse_sticker(client, message.sticker.file_id, user['VK_TOKEN'], user['VK_SECRET'], peer_id)
        except AssertionError:
            logging.debug("Похоже, что это сообщение не является стикером..")

        data = {"peer_id": peer_id, "random_id": randbits(32), "message": message.text,
                "access_token": user['VK_TOKEN'], "v": 5.92}
        response = requests.post("https://api.vk.com/method/messages.send",
                                 data=sign_data(data, "messages.send", user['VK_SECRET'])).json()
        logging.debug("Была совершена попытка отправки сообщения, VK вернул ответ: {0}".format(response))
        if config.DEVELOPER_MODE:
            message.reply("ℹ️ Была совершена попытка отправки сообщения, VK вернул ответ:\n\n`{0}`.".format(response),
                          disable_notification=True)

        return response
    except Exception as e:
        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
