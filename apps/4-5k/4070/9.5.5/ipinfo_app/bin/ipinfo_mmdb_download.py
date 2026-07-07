import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import requests
import splunk.clilib.cli_common as scc

from ipinfo.logging import get_logger
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch


logger = get_logger(__file__)


@Configuration()
class MMDBDownloadCommand(StreamingCommand):
    # Custom command mmdbdownload to download mmdbs passed as argument
    MMDB = Option(require=True)

    def stream(self, record):
        try:
            mmdb_names = self.MMDB.split(",")
            logger.debug("MMDB download command initiated for: %s", mmdb_names)
            session_key = self.service.token

            peer = scc.getMgmtUri()
            logger.debug("Management URI: %s", peer)
            params = {name: "Yes" for name in mmdb_names}
            headers = {
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            }
            url = f"{peer}/servicesNS/nobody/ipinfo_app/download_mmdb"
            logger.debug("Sending MMDB download request to: %s", url)
            disable_splunk_local_ssl_request = False
            refresh_mmdb_shc = requests.request(
                "GET", url, verify=disable_splunk_local_ssl_request, params=params, headers=headers, timeout=3600
            )

            logger.debug("Response status code: %d", refresh_mmdb_shc.status_code)
            if refresh_mmdb_shc.status_code != 200:
                logger.error("Failed to connect to IPinfo app on management URI: %s", peer)
                yield {
                    "Message": f"Cannot connect to IPinfo app on management URI {peer} to download MMDB. Make sure the IPInfo app is correctly set up there."
                }
                return

            logger.debug("Processing MMDB download response")
            refresh_mmdb_shc_json = refresh_mmdb_shc.json()
            count = 0
            for key in refresh_mmdb_shc_json:
                for peer_key in refresh_mmdb_shc_json[key]:
                    count = count + refresh_mmdb_shc_json[key][peer_key]

            logger.info("MMDB download completed with error count: %d", count)
            if count == 0:
                logger.info("MMDB download successful")
                yield {"Message": "Successfully downloaded MMDB"}
            else:
                logger.warning("MMDB download completed with errors")
                yield {"Message": "Error while downloading MMDB. Check Logs dashboard for troubleshooting."}
        except Exception as e:
            logger.error("Error while downloading MMDBs: %s", self.MMDB)
            logger.error(e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
            yield {"Message": "Error while downloading MMDB. Check Logs dashboard for troubleshooting."}


dispatch(MMDBDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
