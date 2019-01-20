# -*- coding: utf-8 -*-


from app import logging
from app import config as config
from telegram.ext import Updater, CommandHandler
from telegram import Bot
from app.telegram.commands.debug import debug as debug_command
from app.telegram.commands.start import start as start_command
import logging


def bot_initialize():
    try:
        bot_updater = Updater(config.BOT_TOKEN, workers=config.WORKERS)
        bot_dispatcher = bot_updater.dispatcher

        bot_dispatcher.add_handler(CommandHandler("debug", debug_command))
        bot_dispatcher.add_handler(CommandHandler("start", start_command))
        bot_dispatcher.add_error_handler(error_handler)

        bot_updater.start_polling(clean=True, poll_interval=0.01)
        return Bot(config.BOT_TOKEN).get_me()
    except Exception as e:
        logging.critical("Произошла ошибка при инициализации бота.", exc_info=True)
        return e


def error_handler(bot, update, error):
    logging.error("Произошла ошибка при получении обновления {0}, ошибка: {1}.".format(update, error))
