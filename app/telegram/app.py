# -*- coding: utf-8 -*-

from app import logging
from app import config as config
from pyrogram import Client, MessageHandler, Filters
from app.telegram.commands.debug import debug as debug_command
from app.telegram.commands.start import start as start_command
import logging


def run():
    try:
        app = Client(session_name=config.BOT_TOKEN, api_id=config.API_ID, api_hash=config.API_HASH)
        app.add_handler(MessageHandler(start_command, Filters.command("start")))
        app.add_handler(MessageHandler(debug_command, Filters.command("debug")))
        app.run()

        return app
    except Exception as e:
        return e
