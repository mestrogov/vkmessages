# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile
from PIL import Image
from secrets import randbits
from app.vk.utils.sign_data import sign_data
import requests
import logging


def parse_sticker(client, file_id, access_token, sig_secret, peer_id):
    logging.debug("Обрабатывается стикер с File ID: {0}...".format(file_id))
    with NamedTemporaryFile(suffix=".webp") as sticker_webp_file:
        logging.debug("Стикер ({0}) скачивается во временный файл {1}...".format(file_id, sticker_webp_file.name))
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

            data = {"peer_id": peer_id, "random_id": randbits(32),
                    "attachment": "doc{0}_{1}".format(saved_document['response']['graffiti']['owner_id'],
                                                      saved_document['response']['graffiti']['id']),
                    "access_token": access_token,
                    "v": 5.92}
            graffiti_message = requests.post("https://api.vk.com/method/messages.send",
                                             data=sign_data(data, "messages.send", sig_secret)).json()
            logging.debug("Сообщение со стикером было отправлено, получен ответ: {0}".format(graffiti_message))
