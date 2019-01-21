# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
import logging
import asyncio


def token(bot, message):
    try:
        message = message.message
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        asyncio.get_event_loop().run_until_complete(
            redis.execute("HSET", "users:{0}".format(message.from_user.id), "active", "True", "VK_TOKEN",
                          message.text.split(" ")[1]))

        bot.send_message(message.from_user.id, "Отлично! Я запомнил твой токен доступа VK, теперь буду пересылать "
                                               "сообщения оттуда. Спасибо, что используешь меня!")
    except Exception as e:
        try:
            bot.send_message(message.from_user.id,
                             "❗ Произошла непредвиденная ошибка при выполнении метода. Сообщите об этом "
                             "администратору для более быстрого ее исправления.")
        except:
            pass

        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
