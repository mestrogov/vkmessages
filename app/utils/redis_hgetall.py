# -*- coding: utf-8 -*-

from app.remote.redis import Redis as redis
from itertools import zip_longest


# Делаем dict из list'а (метод HGETALL в Redis возвращает list); взято отсюда: https://stackoverflow.com/a/6900977
async def redis_hgetall(key):
    return dict(zip_longest(*[iter((await (redis.execute("HGETALL", key)))['details'])] * 2, fillvalue=""))
