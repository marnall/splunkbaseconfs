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



class RealTimeCurrencyConverter():

    def __init__(self, url):

        self.data = requests.get(url).json()

        self.currencies = self.data['rates']


    def convert(self, from_currency, to_currency, amount):

        initial_amount = amount

        if from_currency != 'USD':

            amount = amount / self.currencies[from_currency]


        amount = round(amount * self.currencies[to_currency], 8)

        return amount



class SpotCoin(object):

    coin = ""

    free = ""

    locked = ""

    usdprice = ""

    eurprice = ""


    # The class "constructor" - It's actually an initializer

    def __init__(self, coin, free, locked, usdprice, eurprice):

        self.coin = coin

        self.free = free

        self.locked = locked

        self.usdprice = usdprice

        self.eurprice = eurprice



def make_SpotCoin(coin, free, locked, usdprice, eurprice):

    spc = SpotCoin(coin, free, locked, usdprice, eurprice)

    return spc



response = send_signed_request('GET', '/api/v3/account')


url = 'https://api.exchangerate-api.com/v4/latest/USD'

converter = RealTimeCurrencyConverter(url)

print(converter.convert('USD', 'EUR', 100))


for asset in response['balances']:

    response_asset = send_public_request('/api/v3/ticker/price', {"symbol": asset['asset'] + "USDT"})

    asset_usdprice = response_asset.get('price', 0)

    asset_eurprice = converter.convert('USD', 'EUR', float(asset_usdprice))

    spc = make_SpotCoin(asset['asset'], asset['free'], asset['locked'], asset_usdprice, str(asset_eurprice))

    print(str(vars(spc)).replace("'", '"'))

