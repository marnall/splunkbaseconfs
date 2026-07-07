import os
import sys
import requests
import ConfigParser
from requests.auth import HTTPProxyAuth
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()


class UnshortenCommand(StreamingCommand):
    """ Expand shortened URLs.
    ##Syntax
    
    | expandurl field=<field_name> [redirect_limit=<limit>]

    ##Description

    Expands shortened URLs.
    """
    proxy_urls = {"http":None, "https":None}
    url_field = Option(name='field', require=True)
    redirect_limit = Option(name='redirect_limit', require=False, default=0)
    user_agent = "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:15.0) Gecko/20120910144328 Firefox/15.0.2"

    def get_config(self):
        try:
            appdir = os.path.dirname(os.path.dirname(__file__))
            default_path = os.path.join(appdir, "default", "urlexpander.conf")
            local_path = os.path.join(appdir, "local", "urlexpander.conf") 
            if os.path.exists(local_path):
                path = local_path
            else:
                path = default_path

            config = ConfigParser.ConfigParser()
            config.read(path)
    
            if config.has_section('settings'):

                if config.has_option('settings', 'user_agent'):
                    ua = config.get('settings', 'user_agent')
                    if ua:
                        self.user_agent = ua

                if config.has_option('settings', 'http_proxy'):
                    http_proxy = config.get('settings', 'http_proxy')
                    if http_proxy:
                        self.proxy_urls["http"] = http_proxy

                if config.has_option('settings', 'https_proxy'):
                    https_proxy = config.get('settings', 'https_proxy')
                    if https_proxy:
                        self.proxy_urls["https"] = https_proxy 

        except Exception, e:
            raise e

    def stream(self, events):
        self.get_config()
        for event in events:
            if self.url_field not in event:
                continue

            limit = str(self.redirect_limit)
            if not limit.isdigit():
              limit = 0
            event['expanded_url'] = self.unshorten_url(event[self.url_field].strip(), int(limit))
            yield event

    def unshorten_url(self, url, level):
        try:
            response = requests.request("HEAD", url,proxies=self.proxy_urls, headers={'User-Agent': self.user_agent},allow_redirects=False)
            if response.status_code/100 == 3 and 'Location' in response.headers:
                if level > 0: 
                    return self.unshorten_url(response.headers['Location'], level-1)
                else:
                    return response.headers['Location']
            else:
                return response.url
        except requests.ConnectionError, ce:
             return "CONNECTION ERROR: " + url
        except Exception, e:
            err = "PROCESSING ERROR: " + url
            return err

dispatch(UnshortenCommand, sys.argv, sys.stdin, sys.stdout, __name__)
