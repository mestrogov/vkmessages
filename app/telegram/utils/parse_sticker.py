# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile
from PIL import Image
from secrets import randbits
from hashlib import sha1
from app.remote.redis import Redis as redis
from app.vk.utils.sign_data import sign_data
import asyncio
import requests
import logging


def parse_sticker(client, file_id, access_token, sig_secret, peer_id):
    logging.debug("Обрабатывается стикер с File ID: {0}...".format(file_id))
    sticker_hash = sha1(file_id.encode("UTF-8")).hexdigest()
    sticker_id = asyncio.get_event_loop().run_until_complete(
        redis.execute("GET", "files:vk:sticker:{0}".format(sticker_hash)))['details']

    if not sticker_id:
        logging.debug("Стикер не содержится в кэше, выполняются необходимые процессы...".format(sticker_hash))
        with NamedTemporaryFile(suffix=".webp") as sticker_webp_file:
            logging.debug("Стикер скачивается во временный файл {1}...".format(file_id, sticker_webp_file.name))
            client.download_media(file_id, sticker_webp_file.name)
            sticker_webp = Image.open(sticker_webp_file.name)
            with NamedTemporaryFile(suffix=".png") as sticker_png_file:
                sticker_webp.save(sticker_png_file.name, format="PNG")
                logging.debug("Стикер переконвертирован в формат PNG, сохранен в файл: {0}".format(sticker_png_file.name))

                data = {"type": "graffiti", "access_token": access_token, "v": 5.92}
                upload_server = requests.post("https://api.vk.com/method/docs.getUploadServer",
                                              data=sign_data(data, "docs.getUploadServer", sig_secret)).json()
                logging.debug("URL сервера VK, на который будет происходить загрузка стикера: {0}".format(
                    upload_server['response']['upload_url']))

                files = {'file': open(sticker_png_file.name, 'rb')}
                uploaded_file = requests.post(upload_server['response']['upload_url'], files=files).json()
                logging.debug("После загрузки стикера на сервер VK, получен ответ: {0}".format(uploaded_file))

                data = {"file": uploaded_file['file'], "access_token": access_token, "v": 5.92}
                saved_document = requests.post("https://api.vk.com/method/docs.save",
                                               data=sign_data(data, "docs.save", sig_secret)).json()
                logging.debug("Стикер сохранен как документ, получен ответ: {0}".format(saved_document))

                sticker_id = "doc{0}_{1}_{2}".format(saved_document['response']['graffiti']['owner_id'],
                                                     saved_document['response']['graffiti']['id'],
                                                     saved_document['response']['graffiti']['access_key'])
                asyncio.get_event_loop().run_until_complete(redis.execute(
                    "SET", "files:vk:sticker:{0}".format(sticker_hash), sticker_id))

    data = {"peer_id": peer_id, "random_id": randbits(32),
            "attachment": sticker_id,
            "access_token": access_token,
            "v": 5.92}
    sent_message = requests.post("https://api.vk.com/method/messages.send",
                                 data=sign_data(data, "messages.send", sig_secret)).json()
    logging.debug("Сообщение со стикером было отправлено, получен ответ: {0}".format(sent_message))
