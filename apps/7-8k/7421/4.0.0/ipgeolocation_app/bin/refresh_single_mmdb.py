# Splunk specific dependencies
import os
import sys
import traceback

import requests
import splunk.clilib.cli_common as scc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (
    dispatch, 
    GeneratingCommand, 
    Configuration, 
    Option, 
    splunklib_logger as logger
)
from app_utils import get_logger


logger = get_logger("refresh_single_mmdb")


@Configuration(type="reporting")
class RefreshSingleMMDB(GeneratingCommand):
    MMDB = Option(
        doc='''
        **Syntax:** **MMDB=***<db_std_ip_country|db_std_ip_city|db_std_ip_isp|db_std_ip_city_isp|db_advanced_ip_abuse|db_advanced_ip_asn_ext|db_advanced_ip_asn|db_advanced_ip_city_company_asn_abuse|db_advanced_ip_city_company_asn_abuse_security|db_advanced_ip_city_company_asn|db_advanced_ip_city|db_advanced_ip_company_asn|db_advanced_ip_company|db_advanced_ip_whois|db_sec_pro_ip_city_isp_security|db_sec_pro_ip_city_security|db_sec_pro_ip_hosting|db_sec_pro_ip_residential_proxy|db_sec_pro_ip_security>*
        **Description:** Name of the ipgeolocation.io database that is to be downloaded''',
        require=True)

    def generate(self):
        try:
            MMDB = self.MMDB
            session_key = self.service.token
            peer = scc.getMgmtUri()
            params = {
                MMDB.lower(): "Yes"
            }
            headers = {
                "Authorization": "Splunk " + session_key,
                "Content-Type": "application/json",
            }
            url = peer + "/servicesNS/-/ipgeolocation_app/refresh_mmdb"
            disable_splunk_local_ssl_request = False

            refresh_mmdb_shc = requests.request(
                "GET", url, verify=disable_splunk_local_ssl_request, params=params, headers=headers
            )

            refresh_mmdb_shc_json = refresh_mmdb_shc.json()
            count = 0

            for key in refresh_mmdb_shc_json:
                for peer_key in refresh_mmdb_shc_json[key]:
                    count = count + refresh_mmdb_shc_json[key][peer_key]

            if count == 0:
                yield { "Message": f"Successfully Updated '{MMDB}' MMDB" }
            else:
                yield { "Message": "Error While Updating MMDB. Please Check ipgeolocation.log for troubleshooting." }
        except Exception as e:
            logger.error("Error while downloading " + MMDB)
            logger.exception(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

            yield { "Message": "Error While Updating MMDB. Please Check ipgeolocation.log for troubleshooting" }


dispatch(RefreshSingleMMDB, sys.argv, sys.stdin, sys.stdout, __name__)
