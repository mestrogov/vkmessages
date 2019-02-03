# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.telegram.app import get_client as telegram_get_client
from app.vk.run import start_polling as vk_start_polling
from threading import Thread
from time import sleep
import logging
import asyncio


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(redis.connection())

        client = telegram_get_client()
        Thread(target=client.start, name="telegram_client").start()

        # Telegram клиенту нужно немного времени, чтобы запуститься
        sleep(1)
        Thread(target=vk_start_polling, args=(client,), name="vk_polling").start()
    except Exception as e:
        logging.critical("Произошла ошибка в работе приложения.", exc_info=True)
