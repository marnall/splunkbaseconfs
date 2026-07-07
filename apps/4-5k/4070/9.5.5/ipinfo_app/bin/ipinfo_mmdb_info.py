import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from ipinfo.logging import get_logger
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch


logger = get_logger(__file__)


@Configuration()
class MMDBinfoCommand(GeneratingCommand):
    # Custom command mmdbinfo to get genral info of mmdbs files in lookup folder
    def generate(self):
        logger.debug("MMDBinfo command started")
        lookup_directory = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "lookups"])
        logger.debug("Lookup directory: %s", lookup_directory)

        if os.path.exists(lookup_directory):
            logger.debug("Lookup directory exists, scanning for MMDB files")
            mmdb_count = 0
            for filename in os.listdir(lookup_directory):
                if filename.endswith(".mmdb"):
                    mmdb_count += 1
                    logger.debug("Found MMDB file: %s", filename)
                    lookupfile_location = os.path.join(lookup_directory, filename)
                    lookup_info = self._fetch_lookup_info(lookupfile_location)
                    if lookup_info:
                        logger.debug("Retrieved info for %s: %s MB", filename, lookup_info.get("File Size (MB)"))
                        yield {
                            "Name": filename,
                            "Size (GB)": lookup_info["File Size (GB)"],
                            "Size (MB)": lookup_info["File Size (MB)"],
                            "Last Modified": lookup_info["Last Modified Time"],
                            "Created": lookup_info["Created Time"],
                        }
            logger.info("Found %d MMDB files in lookup directory", mmdb_count)
        else:
            logger.warning("Lookup directory does not exist: %s", lookup_directory)
            self.write_warning("Lookup folder not exist try downloading MMDBS first")

    def _fetch_lookup_info(self, lookupfile_location):
        logger.debug("Fetching info for file: %s", lookupfile_location)
        file_info = {}
        try:
            file_path = lookupfile_location
            file_size = os.path.getsize(file_path)
            file_size_gb = file_size / (1024**3)
            file_size_mb = file_size / (1024**2)
            last_modified_timestamp = os.path.getmtime(file_path)
            last_modified_time = datetime.datetime.fromtimestamp(last_modified_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            created_timestamp = os.path.getctime(file_path)
            created_time = datetime.datetime.fromtimestamp(created_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            file_info["File Size (GB)"] = round(file_size_gb, 2)
            file_info["File Size (MB)"] = round(file_size_mb, 2)
            file_info["Last Modified Time"] = last_modified_time
            file_info["Created Time"] = created_time
            logger.debug("File info collected: %s GB, last modified: %s", file_info["File Size (GB)"], last_modified_time)
        except Exception as e:
            logger.error("Error fetching lookup info for %s: %s", lookupfile_location, e)
            file_info["Error"] = str(e)

        return file_info


if __name__ == "__main__":
    dispatch(MMDBinfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
