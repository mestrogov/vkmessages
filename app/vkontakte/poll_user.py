# -*- coding: utf-8 -*-

from app import logging
from app.remote.redis import Redis as redis
from app.utils.parse_as_boolean import parse_as_boolean
from time import sleep
import asyncio
import logging


async def poll_user(user, user_id, bot, session):
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
            user['VK_LP_PTS']
        except (KeyError, TypeError):
            async with session.post("https://api.vk.com/method/messages.getLongPollServer", params={
                                    "access_token": user['VK_TOKEN'], "need_pts": 1, "lp_version": 3, "v": "5.92"}) as response_lps:
                response_lps = (await response_lps.json())['response']
                user['VK_LP_KEY'] = response_lps['key']
                user['VK_LP_SERVER'] = response_lps['server']
                user['VK_LP_PTS'] = response_lps['pts']
                await redis.execute("HSET", user_id, "VK_LP_KEY", response_lps['key'])
                await redis.execute("HSET", user_id, "VK_LP_SERVER", response_lps['server'])
                await redis.execute("HSET", user_id, "VK_LP_PTS", response_lps['pts'])

        async with session.get("https://api.vk.com/method/messages.getLongPollHistory",
                               params={"access_token": user['VK_TOKEN'], "key": user['VK_LP_KEY'],
                                       "server": user['VK_LP_SERVER'], "pts": user['VK_LP_PTS'],
                                       "mode": 2, "fields": "screen_name", "lp_version": 3, "v": "5.92"}) as response_lp:
            response_lp = (await response_lp.json())['response']
            await redis.execute("HSET", user_id, "VK_LP_PTS", response_lp['new_pts'])

        for message in response_lp['messages']['items']:
            sender = [sender for sender in response_lp['profiles'] if sender['id'] == message['from_id']][0]
            message = "*{0} {1}*\n\n{2}".format(sender['first_name'], sender['last_name'], message['text'])
            bot.send_message(int(user_id.split(":")[1]), message, parse_mode="Markdown")
            sleep(0.1)

        await session.close()
    except Exception as e:
        logging.error("Произошла ошибка при поллинге аккаунта VK пользователя {0}.".format(user_id), exc_info=True)
        return e
