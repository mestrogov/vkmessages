# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.utils.parse_as_boolean import parse_as_boolean
from app.vkontakte.poll_user import poll_user
from aiohttp import ClientSession
from itertools import zip_longest
import asyncio
import logging


def start_polling(bot):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        session = ClientSession()

        for user in (asyncio.get_event_loop().run_until_complete(redis.execute("SCAN", "0", "MATCH", "users:*"))['details'][1]):
            user_id = user
            # Взято отсюда: https://stackoverflow.com/a/6900977
            user = dict(zip_longest(*[iter((asyncio.get_event_loop().run_until_complete(redis.execute("HGETALL", user)))
                                           ['details'])] * 2, fillvalue=""))
            if parse_as_boolean(user['active']):
                asyncio.get_event_loop().run_until_complete(poll_user(user, user_id, bot, session))
    except Exception as e:
        logging.error("Произошла ошибка при попытке начала polling'а всех аккаунтов VK.", exc_info=True)
        return e
