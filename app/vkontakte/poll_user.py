# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.utils.parse_as_boolean import parse_as_boolean
import asyncio
import logging


async def poll_user(user, user_id, session):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            user['VK_TOKEN']
        except (KeyError, TypeError):
            return {"status": "ERROR", "details": "У пользователя нет токена VK"}
        try:
            user['VK_LP_KEY']
            user['VK_LP_SERVER']
            user['VK_LP_TS']
        except (KeyError, TypeError):
            async with session.post("https://api.vk.com/method/messages.getLongPollServer",
                                    params={"access_token": user['VK_TOKEN'], "lp_version": 3, "v": "5.92"}) as response_lp:
                response_lp = (await response_lp.json())['response']
                await redis.execute("HSET", user_id, "VK_LP_KEY", response_lp['key'])
                await redis.execute("HSET", user_id, "VK_LP_SERVER", response_lp['server'])
                await redis.execute("HSET", user_id, "VK_LP_TS", response_lp['ts'])

        await session.close()
    except Exception as e:
        logging.error("Произошла ошибка при попытке начала polling'а всех аккаунтов VK.", exc_info=True)
        return e
