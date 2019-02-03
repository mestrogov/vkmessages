# -*- coding: utf-8 -*-
# Взято отсюда: https://github.com/eternnoir/pyTelegramBotAPI/blob/master/telebot/util.py


def is_command(text):
    """
    Checks if `text` is a command. Telegram chat commands start with the '/' character.
    :param text: Text to check.
    :return: True if `text` is a command, else False.
    """

    return text.startswith('/')
