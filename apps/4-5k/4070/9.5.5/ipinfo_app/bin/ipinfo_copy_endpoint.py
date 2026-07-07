import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import splunk
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from ipinfo.logging import get_logger


logger = get_logger(__file__)


class CopyMmdb(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        logger.debug("Handling POST request for MMDB copy")
        sessionKey = self.sessionKey
        try:
            self.response.setHeader("content-type", "binary/mmdb")
            query = self.request.get("query")
            requested_file = query.get("name")
            logger.debug("Requested file: %s", requested_file)

            mmdb_file_path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "lookups", requested_file])
            logger.debug("MMDB file path: %s", mmdb_file_path)

            logger.debug("Opening file for reading: %s", requested_file)
            f = open(mmdb_file_path, "rb")
            while True:
                chunk = f.read(51200)
                if chunk:
                    logger.debug("Writing chunk")
                    self.response.write(chunk)
                else:
                    break

            logger.info("MMDB file copied successfully: %s", requested_file)
            return

        except Exception as e:
            logger.error("Error while copying MMDB: %s", e)
            logger.error("Requested file: %s", requested_file if "requested_file" in locals() else "unknown")
            self.response.status = 500
            self.response.setHeader("content-type", "text/html")
            self.response.write("Error while copying MMDB.")

    handle_GET = handle_POST
