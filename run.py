# -*- coding: utf-8 -*-

from app import logging
from app import config as config
from app.remote.redis import Redis as redis
import logging
import asyncio


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(redis.connection())
    except Exception as e:
        logging.critical("Произошла ошибка при попытке запуска приложения.", exc_info=True)
