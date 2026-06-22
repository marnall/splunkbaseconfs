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
class FindCompromised(GeneratingCommand):
    """
    The darkwebscangetcompanies command returns company names and companyId's of companys for the given API key.

    Example:

    ``| darkwebscangetcompanies``

    Returns company names and companyId's of companies for the given API key.
    """

    def generate(self):
        # Access the Splunk service using the current search context
        headers = get_headers(self.service)

        self.logger.debug("Getting user companies")

        returned_data = None
        try:
            r = requests.get(
                    f'{DWSA_BASE_API_URL}/user/companies', 
                    headers=headers, 
                    timeout=DWSA_DEFAULT_TIMEOUT
                )
            if r.status_code != 200:
                raise Exception("Unable to fetch data")
            returned_data = r.json()
        except Exception as e:
            self.logger.debug("darkwebscan_app: Got error %s" % str(e))
            raise Exception(e)

        for item in returned_data:
            company_name = item.get('printableName')
            fqdn = item.get('fqdn')
            company_id = item.get('company_id')
            scan_credits_amount = item.get('scanCreditsAmount')
            yield {
                    '_time': time.time(), 
                    'companyName': f'{company_name} ({fqdn})', 
                    'companyId': company_id,
                    'scan_credits_amount': scan_credits_amount,
                    '_raw': returned_data
                }


dispatch(FindCompromised, sys.argv, sys.stdin, sys.stdout, __name__)
