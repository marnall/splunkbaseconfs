import ConfigParser
import sys
import urllib
import urllib2
import os
import sys
import json
from shutil import move
from ReadConf import ReadConf
from UrlPostRequest import UrlPostRequest

import logging as logger
from logging import handlers

import logging.config
logging.config.fileConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "default", "log.ini"))
logger = logging.getLogger('deepdiscovery')

def main(argv):
    try:
        me = os.path.dirname(os.path.realpath(__file__))

        filename = os.path.join(me, "..", "lookups", argv[0])
        filename_tmp = os.path.join(me, "..", "lookups", argv[0]+'.tmp')

        readconf = ReadConf(os.path.join(me, "..", "default", "ADS-base.conf"), ['ADS-base', 'APIServer'])

        url = "http://{HOST}:{PORT}/retroapiserver/{DOWNLOAD}.php".format(HOST = readconf.host, PORT = readconf.port, DOWNLOAD = argv[1])
        values = {'ackey' : readconf.ackey}

        urlpost = UrlPostRequest(url, values)
        json_str = urlpost.request()
        jj = json.loads(json_str)

        if (jj[0]['ret'] == 0):
            fp = open(filename_tmp, 'w')
            fp.write(jj[0]['data'])
            fp.close()
            move(filename_tmp, filename)
            logger.info("download successful")

    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        fp = open(filename_tmp, 'w')
        fp.write(str(e))
        fp.write(". Traceback:")
        fp.write(str(stack))
        fp.close()
        logger.error("download failed")
        logger.error(str(e) + ". Traceback: " + str(stack))

if __name__ == "__main__":
    main(sys.argv[1:])
