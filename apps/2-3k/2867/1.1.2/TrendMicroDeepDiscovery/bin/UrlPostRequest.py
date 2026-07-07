import urllib
import urllib2
import ConfigParser
import os

import logging as logger
from logging import handlers

import logging.config
logging.config.fileConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "default", "log.ini"))
logger = logging.getLogger('deepdiscovery')

me = os.path.dirname(os.path.realpath(__file__))
PROXY_CONFIG_FILE =         os.path.join(me, "..", "local", "proxy.conf")
PROXY_CONFIG_FILE_DEFAULT = os.path.join(me, "..", "default", "proxy.conf")

def read_config():
    proxy_conf = {}

    if os.path.isfile(PROXY_CONFIG_FILE):
        config_file = PROXY_CONFIG_FILE
    else:
        config_file = PROXY_CONFIG_FILE_DEFAULT

    logger.info("Use config: " + config_file)

    config = ConfigParser.ConfigParser()
    config.read(config_file)
    try:
        proxy_conf['enable'] = config.get('proxy', 'enable')
    except ConfigParser.NoOptionError:
        proxy_conf['enable'] = "0"
    try:
        proxy_conf['host'] = config.get('proxy', 'host')
    except ConfigParser.NoOptionError:
        proxy_conf['host'] = ""
    try:
        proxy_conf['port'] = config.get('proxy', 'port')
    except ConfigParser.NoOptionError:
        proxy_conf['port'] = ""
    try:
        proxy_conf['username'] = config.get('proxy', 'username')
    except ConfigParser.NoOptionError:
        proxy_conf['username'] = ""
    try:
        proxy_conf['password'] = config.get('proxy', 'password')
    except ConfigParser.NoOptionError:
        proxy_conf['password'] = ""

    return proxy_conf

class UrlPostRequest:
    def __init__(self, url, values):
        self.url = url
        self.values = values
        self.CHUNK = 16*1024

    def request(self):
        proxy_conf = read_config()
        if proxy_conf['enable'] == "1" and proxy_conf['host'] != "" and proxy_conf['port'] != "":
            logger.info("Use proxy")
            proxy_url = 'http://'+proxy_conf['host']+':'+proxy_conf['port']
            proxy_handler = urllib2.ProxyHandler({'http' : proxy_url})

            if proxy_conf['username'] != "" and proxy_conf['password'] != "":
                logger.info("Use proxy username password")
                password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_manager.add_password(None, proxy_url, proxy_conf['username'], proxy_conf['password'])
                basic_auth_handler = urllib2.ProxyBasicAuthHandler(password_manager)
                digest_auth_handler = urllib2.ProxyDigestAuthHandler(password_manager)
                opener = urllib2.build_opener(proxy_handler, digest_auth_handler, basic_auth_handler)
            else:
                opener = urllib2.build_opener(proxy_handler)
        else:
            logger.info("Do not use proxy")
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)

        try:
            req = urllib2.Request(self.url, urllib.urlencode(self.values))
            content = opener.open(req)
            json_str = ""
            while 0!=-1:
                chunk = content.read(self.CHUNK)
                json_str = json_str + chunk
                if not chunk:
                    break
        except Exception as e:
            logger.info('UrlPostRequest.request: {0}'.format(e))
            raise

        return json_str

if __name__ == '__main__':
    req = UrlPostRequest('''http://retrosplunk.trendmicro.com:8080/retroapiserver/license_activate.php''', {'ackey' : 'DD-A849-KHZBA-TA8DC-BZ86R-CS9TL-MUD2M'})
    print req.request()


        
        

        