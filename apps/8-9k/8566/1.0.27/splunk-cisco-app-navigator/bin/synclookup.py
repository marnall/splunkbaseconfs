# coding=utf-8
"""
synclookup.py — Custom search command for SCAN

Downloads a CSV from S3 and stores it in the app's lookups folder.
Handles gzip compression/decompression automatically.

Usage:
    | synclookup input_csv=splunkbase_assets/splunkbase_apps.csv.gz output_csv=scan_splunkbase_apps.csv.gz

Source:  https://is4s.s3.amazonaws.com/<input_csv>
Target:  $SPLUNK_HOME/etc/apps/splunk-cisco-app-navigator/lookups/<output_csv>
"""

import gzip
import logging
import os
import os.path
import sys
import time
from typing import Generator

import requests
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)

APP_NAME = "splunk-cisco-app-navigator"
# Denotes gzip data header
GZIP_MAGIC_NUMBER = b"\x1f\x8b"
GZIP_MAGIC_NUMBER_LEN = len(GZIP_MAGIC_NUMBER)
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
LOG_PATH = os.path.join(
    SPLUNK_HOME, "var", "log", "splunk", "synclookup.log"
)
LOOKUP_PATH = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "lookups")
S3_BASE_URL = "https://is4s.s3.amazonaws.com/"
LOGGER = logging.getLogger("synclookup")
LOG_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_STREAM_FORMAT = "[%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEBUG = LOGGER.debug
INFO = LOGGER.info
ERROR = LOGGER.error


class _UTCFormatter(logging.Formatter):
    """Formatter that always emits UTC timestamps with +0000 suffix."""
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(LOG_DATE_FORMAT, ct)
        return f"{s}+0000"


def set_up_logging():
    if LOGGER.handlers:
        return
    LOGGER.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(_UTCFormatter(LOG_FILE_FORMAT, LOG_DATE_FORMAT))
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(LOG_STREAM_FORMAT))
    sh.setLevel(logging.WARNING)
    LOGGER.addHandler(sh)
    LOGGER.propagate = False


@Configuration(type="events")
class SyncLookup(GeneratingCommand):
    """
    synclookup: download a file from S3, save it as a CSV optionally in gzipped format

    Example:

    ``| synclookup input_csv=splunkbase_assets/splunkbase_apps.csv.gz output_csv=scan_splunkbase_apps.csv.gz``

    Note: Overwrites existing file without warning
    """

    input_csv = Option(
        require=True,
        doc="""**Syntax:** input_csv=<string>
        **Description:** The S3 path (relative to bucket) to retrieve the CSV from.""",
    )

    output_csv = Option(
        require=False,
        doc="""**Syntax:** output_csv=<string>
        **Description:** The name for the output CSV in the lookups folder.""",
        default=None,
    )

    def get_csv_name(self) -> str:
        "Determine the output file name"
        if self.output_csv is None:
            return self.input_csv.split("/")[-1]
        return self.output_csv

    def check_want_compressed(self) -> bool:
        "Show whether the output name indicates we should save as gzip"
        if os.path.splitext(self.get_csv_name())[1].endswith("gz"):
            return True
        else:
            return False

    def check_compression(self, header) -> None:
        "Show if the data is gzipped"
        if header == GZIP_MAGIC_NUMBER:
            self.is_compressed: bool = True
        else:
            self.is_compressed: bool = False

    def correct_compression(self, content: bytes) -> bytes:
        "Ensure the gzipping is as requested"
        self.check_compression(content[:GZIP_MAGIC_NUMBER_LEN])
        DEBUG(f"is_compressed={self.is_compressed}")
        want_compressed: bool = self.check_want_compressed()
        if want_compressed and not self.is_compressed:
            DEBUG("Want compressed, got uncompressed")
            content = gzip.compress(content)
            self.is_compressed = True
        elif not want_compressed and self.is_compressed:
            DEBUG("Want uncompressed, got compressed")
            try:
                content = gzip.decompress(content)
                self.is_compressed = False
            except (gzip.BadGzipFile, OSError, EOFError) as e:
                ERROR(f"Failed to decompress data: {e}")
                raise
        return content

    def write_output(self, data: bytes) -> int:
        "Write the lookup. Overwrites current file"
        os.makedirs(LOOKUP_PATH, exist_ok=True)
        name: str = os.path.join(LOOKUP_PATH, self.get_csv_name())
        with open(name, "wb") as file:
            bytes_written = file.write(data)
        INFO(f"Wrote {bytes_written} bytes to {name}")
        return bytes_written

    def is_valid_url(self, url):
        return url.endswith(".csv") or url.endswith(".csv.gz")

    def generate(self) -> Generator[dict, None, None]:
        "Run the command at the direction of Splunk"
        INFO(f"command={self!r}")
        INFO(f"input_csv={self.input_csv!r}")
        INFO(f"output_csv={self.output_csv!r}")
        url: str = S3_BASE_URL + self.input_csv
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}. Expected *.csv or *.csv.gz")
        resp = requests.get(url, allow_redirects=True)
        INFO(f"status_code={resp.status_code}")
        resp.raise_for_status()
        data: bytes = self.correct_compression(resp.content)
        bytes_written: int = self.write_output(data)
        yield {
            "_time": time.time(),
            "status_code": resp.status_code,
            "url": url,
            "csv_name": self.get_csv_name(),
            "is_compressed": self.is_compressed,
            "data_length_bytes": len(resp.content),
            "bytes_written": bytes_written,
        }


set_up_logging()
dispatch(SyncLookup, sys.argv, sys.stdin, sys.stdout, __name__)
