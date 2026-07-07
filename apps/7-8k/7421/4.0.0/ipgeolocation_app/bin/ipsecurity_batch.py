#!/usr/bin/env python
# Splunk specific dependencies
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators
)

# Command specific dependencies
import json

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from api_request import query_ipsecurity_api
from app_utils import get_config
from app_utils import get_logger
from parse_api_response import fill_null_ip_securities_for_api
from parse_api_response import parse_ipsecurity_api_response


logger = get_logger("ipsecurity_batch")

method = get_config("method")
api_subscription_plan = get_config("api_subscription_plan")


@Configuration(type="reporting")
class IPSecurityBatch(GeneratingCommand):
    ips = Option(doc='''
                     **Syntax:** **ips=***ip1,ip2,ip3,..,ipn*
                     **Description:** Comma-separated list of IP addresses to search IP information for.''',
                 require=True)

    def generate(self):
        ip_address_list = list(self.ips.split(","))
        

        ip_securities = dict()

        if method == "MMDB":
            self.write_error("`ipsecuritybatch` command doesn't support MMDB lookup method. Use `ipgeolocationbatch` command instead.")
            # (geolocation_log_path, seucurity_log_path) = get_mmdb_readers(self, lookup_security=True)
            #
            # ip_securities = lookup_ip_addresses_from_mmdb(
            #     self,
            #     ip_address_list,
            #     geolocation_log_path,
            #     seucurity_log_path
            # )
        else:
            try:
                if api_subscription_plan == "PAID":
                    api_lookup_response = query_ipsecurity_api(
                        self,
                        splunk_lib_util,
                        ip_address_list,
                       
                    )

                    if api_lookup_response is None:
                        self.write_warning("Got no response from ipgeolocation.io API")
                        logger.error("Got none response from query_ipsecurity_api")
                        ip_securities = fill_null_ip_securities_for_api(
                            ip_address_list,
                            
                        )
                    else:
                        ip_securities = parse_ipsecurity_api_response(
                            api_lookup_response,
                          
                        )
                else:
                    self.write_warning(
                        "Your subscription plan must be 'PAID' to search IP security using `ipsecuritybatch` command.")
            except Exception as e:
                self.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
                self.write_warning(str(e))
                logger.error(e)
                logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

        for keys, values in ip_securities.items():
            yield values

    def parseHeaders(self, headers):
        # Replace single quotes with double quotes for valid json
        return json.loads(headers.replace("'", '"'))

    def parseData(self, data):
        data = '["' + data + '"]'
        return data.replace(",", '","')


if __name__ == "__main__":
    dispatch(IPSecurityBatch, sys.argv, sys.stdin, sys.stdout, __name__)
