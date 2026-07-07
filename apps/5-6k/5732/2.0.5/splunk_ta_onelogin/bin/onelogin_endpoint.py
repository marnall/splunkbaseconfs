#!/usr/bin/env python

from config import Config


def api_server():
    server = Config('onelogin').get('onelogin_api', 'host') \
             or 'https://api.onelogin.com'
    return server.strip('/')
