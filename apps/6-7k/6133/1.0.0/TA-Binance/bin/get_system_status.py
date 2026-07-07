import hashlib

import hmac

import time

from urllib.parse import urlencode


import requests


KEY = '<API KEY HERE>'

SECRET = '<API SECRET HERE>'

BASE_URL = 'https://api.binance.com'



def hashing(query_string):

    return hmac.new(SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()



def get_timestamp():

    return int(time.time() * 1000)



def dispatch_request(http_method):

    session = requests.Session()

    session.headers.update({

        'Content-Type': 'application/json;charset=utf-8',

        'X-MBX-APIKEY': KEY

    })

    return {

        'GET': session.get,

        'DELETE': session.delete,

        'PUT': session.put,

        'POST': session.post,

    }.get(http_method, 'GET')



def send_signed_request(http_method, url_path, payload=None):

    if payload is None:

        payload = {}

    query_string = urlencode(payload, True)

    if query_string:

        query_string = "{}&timestamp={}".format(query_string, get_timestamp())

    else:

        query_string = 'timestamp={}'.format(get_timestamp())


    url = BASE_URL + url_path + '?' + query_string + '&signature=' + hashing(query_string)

    # print("{} {}".format(http_method, url))

    params = {'url': url, 'params': {}}

    response = dispatch_request(http_method)(**params)

    return response.json()



def send_public_request(url_path, payload=None):

    if payload is None:

        payload = {}

    query_string = urlencode(payload, True)

    url = BASE_URL + url_path

    if query_string:

        url = url + '?' + query_string

    # print("{}".format(url))

    response = dispatch_request('GET')(url=url)

    return response.json()


response = send_signed_request('GET', '/sapi/v1/system/status')

print(str(response).replace("'", '"'))
