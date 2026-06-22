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
    The darkwebscanfindcompromised command returns compromised credentials of a given companyId.

    Example:

    ``| darkwebscanfindcompromised companyId=418``

    Returns compromised credentials for company id 418.
    """

    companyId = Option(require=True, validate=validators.Integer(0))
    amount = Option(require=False, validate=validators.Integer(0))
    offset = Option(require=False, validate=validators.Integer(0))

    def generate(self):
        # Access the Splunk service using the current search context
        headers = get_headers(self.service)

        self.logger.debug("Searching compromised credentials for companyId %s" % self.companyId)

        returned_data = None
        try:
            r = requests.get(
                f'{DWSA_BASE_API_URL}/user/lookout/my-leaked-data',
                params={'companyId': self.companyId, 'amount': self.amount, 'offset': self.offset},
                headers=headers,
                timeout=DWSA_DEFAULT_TIMEOUT
            )
            if r.status_code != 200:
                raise Exception("Unable to fetch data")
            returned_data = r.json()
        except Exception as e:
            self.logger.debug("darkwebscan_app: Got error %s" % str(e))
            raise Exception(e)


        try:
            search_results = returned_data.get('searchResults', [])
            for item in search_results:
                domain = item.get('domain')
                country = item.get('country')
                stealer = item.get('stealer')
                size = item.get('size')
                price = item.get('price')
                mDate = item.get('date')
                dt = datetime.strptime(mDate, "%Y-%m-%d")
                epoch_time = int(time.mktime(dt.timetuple()))
                yield {
                        '_time': epoch_time, 
                        'domain': domain, 
                        'country': country,
                        'stealer': stealer,
                        'size': size,
                        'price': price,
                        '_raw': item
                    }
        except Exception as e:
            self.logger.debug("darkwebscan_app: Unable to parse data: %s" % str(e))


dispatch(FindCompromised, sys.argv, sys.stdin, sys.stdout, __name__)
