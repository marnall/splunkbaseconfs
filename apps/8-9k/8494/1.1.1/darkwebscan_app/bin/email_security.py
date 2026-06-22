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
class EmailSecurity(GeneratingCommand):
    """
    The darkwebscanemailsecurity command returns info about SPF, DMARC and DANE of a given companyId.

    Example:

    ``| darkwebscanemailsecurity companyId=418``

    Returns info about SPF, DMARC and DANE for company id 418.
    """

    companyId = Option(require=True, validate=validators.Integer(0))

    def generate(self):
        # Access the Splunk service using the current search context
        headers = get_headers(self.service)

        self.logger.debug("Getting email security info for companyId %s" % self.companyId)

        returned_data = None
        try:
            r = requests.get(
                    f'{DWSA_BASE_API_URL}/scan/email-security', 
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

        spf = returned_data.get('spf', [])
        if spf:
            try:
                dt = datetime.strptime(spf.get('created'), "%Y-%m-%d %H:%M:%S")
                epoch_time = int(time.mktime(dt.timetuple()))
                yield {
                        '_time': epoch_time, 
                        'domain': spf.get('domain'), 
                        'spfRecord': spf.get('spfRecord'),
                        'dmarcRecord': None,
                        'emailHosts': None,
                        'parts': spf.get('parts'),
                        'summary': spf.get('summary'),
                        'warning': spf.get('warning'),
                        'warningColor': spf.get('warningColor'),
                        'companyId': self.companyId,
                        '_raw': spf
                    }
            except Exception as e:
                self.logger.debug("darkwebscan_app: Unable to parse SPF data: %s" % str(e))
        
        dmarc = returned_data.get('dmarc', [])
        if dmarc:
            try:
                dt = datetime.strptime(dmarc.get('created'), "%Y-%m-%d %H:%M:%S")
                epoch_time = int(time.mktime(dt.timetuple()))
                yield {
                        '_time': epoch_time, 
                        'domain': dmarc.get('domain'), 
                        'spfRecord': None,
                        'dmarcRecord': dmarc.get('dmarcRecord'),
                        'emailHosts': None,
                        'parts': dmarc.get('parts'),
                        'summary': dmarc.get('summary'),
                        'warning': dmarc.get('warning'),
                        'warningColor': dmarc.get('warningColor'),
                        'companyId': self.companyId,
                        '_raw': dmarc
                    }
            except Exception as e:
                self.logger.debug("darkwebscan_app: Unable to parse DMARC data: %s" % str(e))
            
        dane = returned_data.get('dane', [])
        if dane:
            try:
                yield {
                        '_time': time.time(), 
                        'domain': dane.get('domain'), 
                        'spfRecord': None,
                        'dmarcRecord': None,
                        'emailHosts': dane.get('emailHosts'),
                        'dmarcRecord': None,
                        'summary': dane.get('summary'),
                        'warning': dane.get('warning'),
                        'warningColor': dane.get('warningColor'),
                        'companyId': self.companyId,
                        '_raw': dane
                    }
            except Exception as e:
                self.logger.debug("darkwebscan_app: Unable to yield DANE data: %s" % str(e))

dispatch(EmailSecurity, sys.argv, sys.stdin, sys.stdout, __name__)
