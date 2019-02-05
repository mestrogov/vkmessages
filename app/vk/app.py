# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.utils.redis_hgetall import redis_hgetall as hgetall
from app.utils.parse_as_boolean import parse_as_boolean
from app.vk.poll_user import poll_user
from time import sleep
import asyncio
import logging


def start_polling(client):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        users = asyncio.get_event_loop().run_until_complete(redis.execute("SMEMBERS", "users"))['details']
        logging.debug("Пользователи в Redis: " + str(users))
        while True:
            for user in users:
                user_id = user
                user = asyncio.get_event_loop().run_until_complete(hgetall(user))
                if parse_as_boolean(user['active']):
                    # TODO: Использовать Dramatiq вместо этого самопального кода
                    result = poll_user(user, user_id, client)
                    logging.debug("Выполнен polling пользователя {0}, результат: {1}".format(user_id, result))

            sleep(0.1)
    except Exception as e:
        logging.error("Произошла ошибка при попытке начала polling'а всех аккаунтов VK.", exc_info=True)
        return e
