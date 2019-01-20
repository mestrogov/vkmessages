# -*- coding: utf-8 -*-

from app import logging
import logging


def debug(bot, message):
    try:
        message = message.message

        bot.send_message(message.from_user.id,
                         "Ниже находится информация, которая может быть полезна при разработке и не только."
                         "\n\nUser ID: `{0}`"
                         "\nMessage ID: `{1}`"
                         "\nLanguage Code: `{2}`".format(str(message.from_user.id), str(message.message_id),
                                                         str(message.from_user.language_code)), parse_mode="Markdown")
    except Exception as e:
        try:
            bot.send_message(message.from_user.id,
                             "❗ Произошла непредвиденная ошибка при выполнении метода, посмотрите в консоль для более "
                             "подробной информации (если вы не являеетесь администратором, то напишите ему).")
        except:
            pass

        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
