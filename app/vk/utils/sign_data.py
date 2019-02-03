# -*- coding: utf-8 -*-

from urllib.parse import urlencode, quote_plus
from hashlib import md5


def sign_data(data, method, secret):
    # Взято отсюда: https://stackoverflow.com/a/40557716
    sig = md5("/method/{0}?{1}{2}".format(method, urlencode(data, quote_via=quote_plus), secret).encode("UTF-8")).hexdigest()
    data['sig'] = sig

    return data
