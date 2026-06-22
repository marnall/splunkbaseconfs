#!/usr/bin/env python3
#
#   Copyright 2026 Bechtle GmbH IT-Systemhaus Rheinland
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from config.settings import *
from config.secrets import get_headers
from datetime import datetime
import requests
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import sys
import time

@Configuration()
class WAF(GeneratingCommand):
    """
    The darkwebscanwaf command returns info about the WAF (Web Application Firewall) status of a given companyId.

    Example:

    ``| darkwebscanwaf companyId=418``

    Returns info about the WAF (Web Application Firewall) status for company id 418.
    """

    companyId = Option(require=True, validate=validators.Integer(0))

    def generate(self):
        # Access the Splunk service using the current search context
        headers = get_headers(self.service)

        self.logger.debug("Getting WAF (Web Application Firewall) info for companyId %s" % self.companyId)

        returned_data = None
        try:
            r = requests.get(
                    f'{DWSA_BASE_API_URL}/scan/waf', 
                    params={'companyId': self.companyId},
                    headers=headers, 
                    timeout=DWSA_DEFAULT_TIMEOUT
                )
            if r.status_code != 200:
                raise Exception("Unable to fetch data")
            returned_data = r.json()
        except Exception as e:
            self.logger.debug("darkwebscan_app: Got error %s" % str(e))
            raise Exception(e)

        product = returned_data.get('product', None)
        summary = returned_data.get('summary', None)
        warning = returned_data.get('warning', None)
        warningColor = returned_data.get('warningColor', None)

        yield {
                '_time': time.time(), 
                'product': product,
                'summary': summary, 
                'warning': warning,
                'warningColor': warningColor,
                'companyId': self.companyId,
                '_raw': returned_data
            }

dispatch(WAF, sys.argv, sys.stdin, sys.stdout, __name__)
