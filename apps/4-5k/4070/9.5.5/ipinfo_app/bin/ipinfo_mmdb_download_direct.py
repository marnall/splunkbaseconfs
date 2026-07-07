import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import splunk.clilib.cli_common as scc

import splunklib.client as client
from ipinfo.logging import get_logger
from ipinfo_download import download_mmdb_file
from ipinfo_utils import get_bearer_token
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch


logger = get_logger(__file__)

STANDARD_ERROR_MESSAGE = "Error while direct-downloading MMDB. Make sure you have a working bearer token at /app/ipinfo_app/debug and check Logs dashboard for troubleshooting."


@Configuration()
class MMDBDownloadDirectCommand(StreamingCommand):
    # Custom command mmdbdownloaddirect to download mmdbs passed as argument
    MMDB = Option(require=True)

    def stream(self, _record):
        try:
            mmdb_names = self.MMDB.split(",")
            logger.debug("MMDB direct download command initiated for: %s", mmdb_names)

            session_key = self.service.token
            logger.debug("Retrieving bearer token")
            bearer_token = get_bearer_token(session_key, False)
            if not bearer_token:
                logger.error("Bearer token not found or empty")
            else:
                logger.debug("Bearer token retrieved successfully")

            error_count = 0
            for mmdb_name in mmdb_names:
                logger.debug("Starting direct download for MMDB: %s", mmdb_name)
                yield {"Message": f"Direct-downloading {mmdb_name}"}
                error_count += download_mmdb_file(session_key, bearer_token, mmdb_name)

            logger.info("Direct MMDB download completed with error count: %d", error_count)
            if error_count == 0:
                logger.info("All MMDBs direct-downloaded successfully")
                yield {"Message": "Successfully direct-downloaded MMDB"}
            else:
                logger.warning("MMDB direct download completed with errors")
                yield {"Message": STANDARD_ERROR_MESSAGE}
        except Exception as e:
            logger.error("Error while downloading MMDBs: %s", self.MMDB)
            logger.error(e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
            yield {"Message": STANDARD_ERROR_MESSAGE}


dispatch(MMDBDownloadDirectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
