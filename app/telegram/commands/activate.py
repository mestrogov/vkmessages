# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
import logging
import asyncio


def activate(bot, message):
    try:
        message = message.message
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        asyncio.get_event_loop().run_until_complete(redis.execute("HSET", "users:{0}".format(message.from_user.id),
                                                                  "active", "True"))

        bot.send_message(message.from_user.id, "Хорошо! Я изменил твой статус на активный.")
    except Exception as e:
        try:
            bot.send_message(message.from_user.id,
                             "❗ Произошла непредвиденная ошибка при выполнении метода. Сообщите об этом "
                             "администратору для более быстрого ее исправления.")
        except:
            pass

        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
