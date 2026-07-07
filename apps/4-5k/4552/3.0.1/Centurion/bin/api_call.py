import os
import sys
import requests
from requests.auth import HTTPBasicAuth
#import urllib2
import urllib
import http.client
import splunk.entity
import splunk.Intersplunk
from splunk.clilib import cli_common as cli

try:
	import urllib2 as request_url
except ImportError:
	import urllib.request as request_url



splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger


class GetIOCScoreFromAPI:

    def __init__(self):
        self.host = 'NA'
        self.port = 'NA'
        self.proxy_use = "0"
        self.get_proxy_credentials()

    def get_proxy_credentials(self):
        try:
            # cfg = cli.getConfStanza('settings', 'proxies')
            local_conf_path = os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'local', 'settings.conf')
            default_conf_path = os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'default', 'settings.conf')

            if os.path.exists(local_conf_path):
                cfg = cli.readConfFile(local_conf_path)
            elif os.path.exists(default_conf_path):
                cfg = cli.readConfFile(default_conf_path)
            else:
                logger = setup_logger()
                logger.error("settings.conf file not found. "
                             "Please create proxy settings using setup page of the app")
                sys.exit()

            for name, content in cfg.items():
                if name == "proxies":
                    if 'proxy-enable' in content:
                        #self.proxy_use = content['proxy-enable']
                        self.proxy_use = "0"
                    else:
                        self.proxy_use = "0"

                    if self.proxy_use == "1":
                        if 'host' in content:
                            self.host = content['host']
                        else:
                            logger = setup_logger()
                            logger.error("Missing host detail for the proxy server")
                            sys.exit()

                        if 'port' in content:
                            self.port = content['port']
                        else:
                            logger = setup_logger()
                            logger.error("Missing port detail for the proxy server")
                            sys.exit()

        except Exception as e:
            logger = setup_logger()
            logger.error("Exception while getting proxy details : %s" % (str(e)))
            sys.exit()

    def get_score(self, proxy_username, proxy_pass, provider, params, url, headers=None, username=None, password=None):
        try:
            logger = setup_logger()

            if self.proxy_use == "1":
                proxy_url_https = "https://" + proxy_username + ":" + proxy_pass + "@" + self.host + ":" + self.port
                proxy_url_http = "http://" + proxy_username + ":" + proxy_pass + "@" + self.host + ":" + self.port
                proxies = {
                    'https': proxy_url_https,
                    'http': proxy_url_http
                }
                if username is None:
                    res = requests.get(url, params=params, proxies=proxies, headers=headers, verify=False)
                else:
                    res = requests.get(url, params=params, proxies=proxies, headers=headers, verify=False,
                                       auth=HTTPBasicAuth(username, password))
            else:
                if username is None:
                    res = requests.get(url, params=params, headers=headers)
                else:
                    res = requests.get(url, params=params, headers=headers, auth=(username, password))
            return res

        except requests.exceptions.HTTPError as e:
            logger = setup_logger()
            logger.error("%s HTTP Connection EXCEPTION: %s" % (str(provider), str(e)))
            sys.exit()

        except requests.exceptions.ConnectionError as e:
            logger = setup_logger()
            logger.error("%s Api Connection EXCEPTION: %s" % (str(provider), str(e)))
            sys.exit()

        except requests.exceptions.RequestException as e:
            logger = setup_logger()
            logger.error("%s Api EXCEPTION: %s" % (str(provider), str(e)))
            sys.exit()

    def get_score_using_urllib(self, proxy_username, proxy_pass, provider, params, url):
        try:
            if self.proxy_use == "1":
                proxy_url_https = "https://" + proxy_username + ":" + proxy_pass + "@" + self.host + ":" + self.port
                proxy_url_http = "http://" + proxy_username + ":" + proxy_pass + "@" + self.host + ":" + self.port
                proxies = {
                    "https": proxy_url_https,
                    "http": proxy_url_http
                }
                proxy =  request_url.ProxyHandler(proxies)
                opener =  request_url.build_opener(proxy)
                request_url.install_opener(opener)

                res_req =  request_url.Request(url, urllib.urlencode(params).encode("utf-8"))
                res =  request_url.urlopen(res_req)
            else:
                res_req =  request_url.Request(url, urllib.urlencode(params).encode("utf-8"))
                res =  request_url.urlopen(res_req)

            return res

        except Exception as e:
            logger = setup_logger()
            logger.error("%s Centurion EXCEPTION: %s" % (str(provider), str(e)))
            sys.exit()






