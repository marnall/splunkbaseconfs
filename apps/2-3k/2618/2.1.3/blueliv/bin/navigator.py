# -*- coding: utf-8 -*-

import sys
sys.path.append('lib')
import requests

from ConfigFile import *


class Navigator:

    __USER_AGENT = "Splunk v2.0.2"
    __API_CLIENT = "8c277cb4-5fab-451c-b053-f6f12a259ee5"

    def __init__(self):
        self.configuration = ConfigFile()
        proxy = self.configuration.readProxyConfig()
        if proxy.isActivated():
            if proxy.getType() == 3:  # http
                self.proxies = {"http": "http://"+proxy.getProxy(), "https": "http://"+proxy.getProxy()}
        else:
            self.proxies = None
        self.timeout = 120
        self.passwd = self.configuration.getCredentials()
        self.headers = dict()
        self.headers["Authorization"] = "bearer {0}".format(self.passwd) if self.passwd else None
        self.headers["User-Agent"] = self.__USER_AGENT
        self.headers["X-API-CLIENT"] = self.__API_CLIENT

    def go(self, url):
        url = url + "?key={0}".format(self.__API_CLIENT)
        if self.proxies:
            r = requests.get(url, proxies=self.proxies, verify=False, headers=self.headers, timeout=self.timeout)
        else:
            r = requests.get(url, verify=False, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
