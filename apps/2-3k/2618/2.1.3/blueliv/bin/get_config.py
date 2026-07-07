# -*- coding: utf-8 -*-
# !/usr/bin/env python

import ConfigParser
import sys
import os


CONFIG_FILE = 'blueliv.cfg'
SECTION_NAME_KEY = 'API'
SECTION_NAME_PROXY = 'Proxy'



def main():
    apikey = ''
    apiurl = 'https://freeapi.blueliv.com'
    refresh = '360'
    host = ''
    port = ''
    user = ''
    passwd = ''
    
    Config = ConfigParser.RawConfigParser(allow_no_value=True)

    if not os.path.isfile(CONFIG_FILE):
       sys.stderr.write(apikey+'|')
       sys.stderr.write(apiurl+'|')
       sys.stderr.write(refresh+'|')
       sys.stderr.write(host+'|')
       sys.stderr.write(port+'|')
       sys.stderr.write(user+'|')
       sys.stderr.write(passwd)
       return
    
    Config.read(CONFIG_FILE)
    
    if Config.has_section(SECTION_NAME_KEY):
        try:
            apikey = Config.get(SECTION_NAME_KEY, 'apikey')
            apikey = 'paste-your-apikey-here' if apikey is None or '' else apikey
        except:
            apikey = 'paste-your-apikey-here'
        try:
            refresh = Config.get(SECTION_NAME_KEY, 'updatetime')
        except:
            refresh = '360'
        try:
            apiurl = Config.get(SECTION_NAME_KEY, 'url')
            apiurl = 'htps://freeapi.blueliv.com' if apiurl is None or '' else apiurl
        except:
            apiurl = 'htps://freeapi.blueliv.com'

    if Config.has_section(SECTION_NAME_PROXY):
        try:
            host = Config.get(SECTION_NAME_PROXY, 'host')
        except:
            host = ''
        try:
            port = Config.get(SECTION_NAME_PROXY, 'port')
        except:
            port = ''
        try:
            user = Config.get(SECTION_NAME_PROXY, 'user')
        except:
            user = ''
        try:
            passwd = Config.get(SECTION_NAME_PROXY, 'pass')
        except:
            passwd = ''

    sys.stderr.write(apikey+'|')
    sys.stderr.write(apiurl+'|')
    sys.stderr.write(refresh+'|')
    sys.stderr.write(host+'|')
    sys.stderr.write(port+'|')
    sys.stderr.write(user+'|')
    sys.stderr.write(passwd)

main()
