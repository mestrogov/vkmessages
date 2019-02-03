# -*- coding: utf-8 -*-
# Взято отсюда: https://github.com/eternnoir/pyTelegramBotAPI/blob/master/telebot/util.py


def split_string(text, chars_per_string):
    """
    Splits one string into multiple strings, with a maximum amount of `chars_per_string` characters per string.
    This is very useful for splitting one giant message into multiples.
    :param text: The text to split
    :param chars_per_string: The number of characters per line the text is split into.
    :return: The splitted text as a list of strings.
    """

    return [text[i:i + chars_per_string] for i in range(0, len(text), chars_per_string)]
