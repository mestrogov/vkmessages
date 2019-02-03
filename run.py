# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.telegram.app import run as bot_run
from app.vk.run import start_polling as vk_start_polling
from threading import Thread
import logging
import asyncio


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(redis.connection())

        Thread(target=bot_run, name="telegram_client").start()
        Thread(target=vk_start_polling, args=(bot,), name="vk_polling").start()
    except Exception as e:
        logging.critical("Произошла ошибка в работе приложения.", exc_info=True)
