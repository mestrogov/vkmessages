# -*- coding: utf-8 -*-

from app import logging
from app import config as config
import logging


def debug(client, message):
    try:
        client.send_message(
            message.from_user.id,
            "Ниже находится информация, которая может оказаться полезной."
            "\n\n**Информация о приложении:** `\nVersion: {0}`\n`Commit: {1}`\n`Developer Mode: {2}`"
            "\n\n**Информация о пользователе:** \n`User ID: {3}`\n`Message ID: {4}`\n`Language Code: {5}`".format(
                config.VERSION, config.COMMIT, config.DEVELOPER_MODE, message.from_user.id, message.message_id,
                message.from_user.language_code), parse_mode="Markdown")
    except Exception as e:
        try:
            client.send_message(
                message.from_user.id,
                "❗ Произошла непредвиденная ошибка при выполнении метода. Сообщите об этом администратору для более "
                "быстрого ее исправления.")
        except:
            pass

        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
