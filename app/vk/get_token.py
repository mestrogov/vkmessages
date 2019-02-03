# -*- coding: utf-8 -*-
# Оригинальная реализация на PHP: https://github.com/vodka2/vk-audio-token

import requests
from secrets import token_hex
from app.vk.utils.sign_data import sign_data

clients = [
    {
        # Официальное приложение VK на Android
        "user_agent": "VKAndroidApp/5.23-2978 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en; 320x240)",
        "client_id": "2274003",
        "client_secret": "hHbZxrka2uZ6jB1inYsH",
        "version": "5.92"
    }
]


def get_token(username, password, code=None, clients_number=0, scope="nohttps,all"):
    device_id = token_hex(8)
    client_id = clients[clients_number]['client_id']
    client_secret = clients[clients_number]['client_secret']
    client_user_agent = clients[clients_number]['user_agent']
    version = clients[clients_number]['version']

    non_refreshed = get_non_refreshed(username, password, device_id, scope, client_id, client_secret,
                                      client_user_agent, version, code)
    try:
        assert non_refreshed['access_token']
    except (KeyError, TypeError):
        return non_refreshed

    refreshed = refresh_token(non_refreshed['access_token'], non_refreshed['secret'], device_id, client_user_agent,
                              version)
    try:
        return {"secret": non_refreshed['secret'], "token": refreshed['response']['token'],
                "user_agent": client_user_agent}
    except (KeyError, TypeError):
        return refreshed


def get_non_refreshed(username, password, device_id, scope, client_id, client_secret, client_user_agent, version, code):
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "device_id": device_id,
        "scope": scope,
        "username": username,
        "password": password,
        "2fa_supported": 1,
        "code": code,
        "lang": "ru",
        "v": version
    }
    headers = {
        "User-Agent": client_user_agent
    }

    response = requests.post("https://oauth.vk.com/token", data=data, headers=headers).json()
    return response


def refresh_token(token, secret, device_id, client_user_agent, version):
    data = {
        "device_id": device_id,
        "receipt": "",
        "receipt2": "",
        "lang": "ru",
        "access_token": token,
        "v": version
    }
    headers = {
        "User-Agent": client_user_agent
    }

    response = requests.post("https://api.vk.com/method/auth.refreshToken",
                             data=sign_data(data, "auth.refreshToken", secret), headers=headers).json()
    return response
