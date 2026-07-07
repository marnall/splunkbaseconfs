# -*- coding: utf-8 -*-
# !/usr/bin/env python

import ConfigParser
import sys
import os


CONFIG_FILE = 'blueliv.cfg'
SECTION_NAME_KEY = 'API'
SECTION_NAME_BOTS = 'API_BOTS'
SECTION_NAME_PROXY = 'Proxy'
FREE_API_URL = 'https://freeapi.blueliv.com'
PAID_API_URL = 'https://api.blueliv.com'



def main():
    mode = sys.argv[1]
    apikey = sys.argv[2] if len(sys.argv) >= 3 and mode == 'key' is not None else ""
    apiurl = sys.argv[3] if len(sys.argv) >= 4 and mode == 'key' is not None else "https://freeapi.blueliv.com"
    refresh = sys.argv[4] if len(sys.argv) >= 5 and mode == 'key' is not None else "360"
    proxy_host = sys.argv[2] if len(sys.argv) >= 3 and mode == 'proxy' is not None else ""
    proxy_port = sys.argv[3] if len(sys.argv) >= 4 and mode == 'proxy' is not None else ""
    proxy_user = sys.argv[4] if len(sys.argv) >= 5 and mode == 'proxy' is not None else ""
    proxy_pass = sys.argv[5] if len(sys.argv) >= 6 and mode == 'proxy' is not None else ""
    
    Config = ConfigParser.RawConfigParser(allow_no_value=True)
    
    if not os.path.isfile(CONFIG_FILE):
        open(CONFIG_FILE, 'a').close()
    
    Config.read(CONFIG_FILE)
    
    if not Config.has_section(SECTION_NAME_KEY):
        Config.add_section(SECTION_NAME_KEY)

    if not Config.has_section(SECTION_NAME_BOTS):
        Config.add_section(SECTION_NAME_BOTS)

    if not Config.has_section(SECTION_NAME_PROXY):
        Config.add_section('Proxy')
        Config.set('Proxy', 'activated', False)
        Config.set('Proxy', 'host', '')
        Config.set('Proxy', 'port', '')
        Config.set('Proxy', 'user', '')
        Config.set('Proxy', 'pass', '')
        Config.set('Proxy', 'needCredentials', False)
    
    if mode == "key":
        Config.set(SECTION_NAME_KEY, "apikey", apikey)
        Config.set(SECTION_NAME_KEY, "url", apiurl)
        if apiurl == PAID_API_URL:
            Config.set(SECTION_NAME_KEY, "type", "PAID")
        else:
            Config.set(SECTION_NAME_KEY, "type", "FREE")
        Config.set(SECTION_NAME_KEY, "updatetime", refresh)
        Config.set(SECTION_NAME_BOTS, "updatetime", "10")
    else:
        Config.set('Proxy', 'type', 3)
        if proxy_host != '' and proxy_port != '':
            Config.set('Proxy', 'activated', True)
            Config.set('Proxy', 'host', proxy_host)
            Config.set('Proxy', 'port', proxy_port)
            Config.set('Proxy', 'user', proxy_user)
            Config.set('Proxy', 'pass', proxy_pass)
            if proxy_user != '' and proxy_pass != '':
                Config.set('Proxy', 'needCredentials', True)
            else:
                Config.set('Proxy', 'needCredentials', False)
        else:
            Config.set('Proxy', 'activated', False)
            Config.set('Proxy', 'host', '')
            Config.set('Proxy', 'port', '')
            Config.set('Proxy', 'user', '')
            Config.set('Proxy', 'pass', '')
            Config.set('Proxy', 'needCredentials', False)
        
    
    with open(CONFIG_FILE, 'wb') as configfile:
           Config.write(configfile)

    sys.stderr.write("ok")

main()
