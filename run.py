# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.telegram.run import bot_initialize
import logging
import asyncio


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(redis.connection())

        logging.info("Информация о Боте в Telegram: " + str(bot_initialize()))
    except Exception as e:
        logging.critical("Произошла ошибка в работе приложения.", exc_info=True)
