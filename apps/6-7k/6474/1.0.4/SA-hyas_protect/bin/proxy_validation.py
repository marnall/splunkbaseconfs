from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from url import url


@Configuration()
class proxy_validation(GeneratingCommand):

    proxy_port = Option(require=True)
    proxy_host = Option(require=True)

    def generate(self):
        try:
            if (
                self.proxy_port
                and 0 <= int(self.proxy_port) <= 65354
                and url(self.proxy_host)
            ):
                yield {"cred_status": "success"}
            else:
                yield {"cred_status": "failed"}

        except Exception as err:
            yield {"Error": err}


dispatch(proxy_validation, sys.argv, sys.stdin, sys.stdout, __name__)
