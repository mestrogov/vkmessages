# -*- coding: utf-8 -*-

from app import logging
import logging


def start(bot, message):
    try:
        message = message.message

        bot.send_message(message.from_user.id,
                         "Приветствую тебя, {0} {1}!"
                         "\n\nБлагодарю за возникший интерес ко мне. Я являюсь очень полезным Ботом, который "
                         "поможет тебе избавиться от использования VK (как мессенджера, ведь так каждый "
                         "использует его в наши дни?) и полностью перейти на темную сторону — в Telegram! "
                         "В VK до сих пор сидит огромное количество людей (друзей), которые не хотят "
                         "переходить в Telegram, поэтому я буду переадресовывать их сообщения из VK в твой "
                         "уютный Telegram и таким образом помогу тебе навсегда забыть про VK!".format(
                             message.chat.first_name, message.chat.last_name))
    except Exception as e:
        try:
            bot.send_message(message.from_user.id,
                             "❗ Произошла непредвиденная ошибка при выполнении метода. Сообщите об этом "
                             "администратору для более быстрого ее исправления.")
        except:
            pass

        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
