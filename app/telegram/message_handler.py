# -*- coding: utf-8 -*-

from app import logging
from app.utils.redis_hgetall import redis_hgetall as hgetall
from app.remote.redis import Redis as redis
from app import config as config
from app.vk.utils.sign_data import sign_data
from PIL import Image
from tempfile import NamedTemporaryFile
from secrets import randbits
import requests
import logging
import asyncio


def message_handler(client, message):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assert message.reply_to_message
        except AssertionError:
            return
        tg_message_id = "{0}_{1}".format(message.reply_to_message.chat.id, message.reply_to_message.message_id)
        vk_message_id = asyncio.get_event_loop().run_until_complete(
            redis.execute("GET", "message:telegram:{0}".format(tg_message_id)))['details']
        if not vk_message_id:
            logging.debug("Сообщение, на которое ответил пользователь, не содержит ID сообщения из VK.")
            if config.DEVELOPER_MODE:
                message.reply("ℹ️ К сообщению, на которое вы ответили, не привязано ID сообщения из VK.",
                              disable_notification=True)
            return

        user = asyncio.get_event_loop().run_until_complete(hgetall("user:{0}".format(message.from_user.id)))

        try:
            assert message.sticker.file_id
            with NamedTemporaryFile(suffix=".webp") as sticker_webp_file:
                logging.debug("Стикер скачивается во временный файл.")
                client.download_media(message.sticker.file_id, sticker_webp_file.name)
                sticker_webp = Image.open(sticker_webp_file.name)
                with NamedTemporaryFile(suffix=".png") as sticker_png_file:
                    sticker_webp.save(sticker_png_file.name, format="PNG")
                    logging.debug(
                        "Стикер переконвертирован в формат PNG, сохранен в файл: {0}".format(sticker_png_file.name))

                    data = {"type": "graffiti", "access_token": user['VK_TOKEN'], "v": 5.92}
                    upload_server = requests.post("https://api.vk.com/method/docs.getUploadServer",
                                                  data=sign_data(data, "docs.getUploadServer", user['VK_SECRET'])).json()
                    logging.debug("URL сервера, на который будет происходить загрузка файла: {0}".format(
                        upload_server['response']['upload_url']))

                    files = {'file': open(sticker_png_file.name, 'rb')}
                    uploaded_file = requests.post(upload_server['response']['upload_url'], files=files).json()
                    logging.debug("Загружен стикер на сервера VK, результат: {0}".format(uploaded_file))

                    data = {"title": "sticker.png", "tags": "стикер", "file": uploaded_file['file'],
                            "access_token": user['VK_TOKEN'], "v": 5.92}
                    saved_document = requests.post("https://api.vk.com/method/docs.save",
                                                   data=sign_data(data, "docs.save", user['VK_SECRET'])).json()
                    logging.debug("Сохранен стикер как документ, результат: {0}".format(saved_document))

                    data = {"peer_id": vk_message_id.split("_")[0], "random_id": randbits(32),
                            "attachment": "doc{0}_{1}".format(saved_document['response']['graffiti']['owner_id'],
                                                              saved_document['response']['graffiti']['id']),
                            "access_token": user['VK_TOKEN'],
                            "v": 5.92}
                    graffiti_message = requests.post("https://api.vk.com/method/messages.send",
                                                     data=sign_data(data, "messages.send", user['VK_SECRET'])).json()
                    logging.debug("Сообщение со стикером отправлено, результат: {0}".format(graffiti_message))
        except AssertionError:
            logging.debug("Похоже, что это сообщение не является стикером..")

        data = {"peer_id": vk_message_id.split("_")[0], "random_id": randbits(32), "message": message.text,
                "access_token": user['VK_TOKEN'], "v": 5.92}
        response = requests.post("https://api.vk.com/method/messages.send",
                                 data=sign_data(data, "messages.send", user['VK_SECRET'])).json()
        logging.debug("Была совершена попытка отправки сообщения, VK вернул ответ: {0}".format(response))
        if config.DEVELOPER_MODE:
            message.reply("ℹ️ Была совершена попытка отправки сообщения, VK вернул ответ:\n\n`{0}`.".format(response),
                          disable_notification=True)

        return response
    except Exception as e:
        logging.error("Произошла ошибка при попытке выполнения метода.", exc_info=True)
        return e
