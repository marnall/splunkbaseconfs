from __future__ import absolute_import, division, print_function, unicode_literals
import os,sys
import re
from url import url
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

@Configuration()
class proxy_validation(GeneratingCommand):

    proxy_port = Option(require=True)
    proxy_host = Option(require=True)

    def generate(self):
        try:
            port = self.proxy_port
            host = self.proxy_host
            if port != '':
                if 0<= int(port) <= 65353 and url(host):
                    yield {"cred_status":"success"}
                else:
                    yield {"cred_status":"failed"}
            else:
                yield {"cred_status":"failed"}

        except Exception as err:
            yield {"Error":err}

dispatch(proxy_validation, sys.argv, sys.stdin, sys.stdout, __name__)