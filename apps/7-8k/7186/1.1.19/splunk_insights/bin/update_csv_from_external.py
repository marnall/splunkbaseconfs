# coding=utf-8

import gzip
import configparser
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

APP_NAME = "splunk_insights"
# Denotes gzip data header
GZIP_MAGIC_NUMBER = b"\x1f\x8b"
GZIP_MAGIC_NUMBER_LEN = len(GZIP_MAGIC_NUMBER)
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
LOG_PATH = os.path.join(
    SPLUNK_HOME, "var", "log", "splunk", "update_csv_from_external.log"
)
LOG_LEVEL_ENV_VAR = "UPDATE_CSV_FROM_EXTERNAL_LOG_LEVEL"
LOGGING_CONF_NAME = "update_csv_from_external.conf"
LOGGING_CONF_PATHS = (
    os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "local", LOGGING_CONF_NAME),
    os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "default", LOGGING_CONF_NAME),
)
LOOKUP_PATH = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "lookups")
S3_BASE_URL = "https://is4s.s3.amazonaws.com/"
LOGGER = logging.getLogger("updatecsvfromexternal")
LOG_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_STREAM_FORMAT = "[%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S%z"
DEBUG = LOGGER.debug
INFO = LOGGER.info
ERROR = LOGGER.error


def resolve_log_level() -> int:
    """
    Resolve log level in this precedence order:
    1) environment variable UPDATE_CSV_FROM_EXTERNAL_LOG_LEVEL
    2) local/default conf file: [logging] level = <LEVEL>
    3) INFO
    """
    configured_level = os.environ.get(LOG_LEVEL_ENV_VAR)
    if configured_level is None:
        config = configparser.ConfigParser()
        for conf_path in LOGGING_CONF_PATHS:
            if os.path.exists(conf_path):
                config.read(conf_path)
                configured_level = config.get("logging", "level", fallback=None)
                if configured_level:
                    break
    level_name = (configured_level or "INFO").strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        # Keep startup reliable even when config is bad.
        print(
            f"[WARNING] Invalid log level '{level_name}'. Falling back to INFO.",
            file=sys.stderr,
        )
        return logging.INFO
    return level


def set_up_logging():
    if LOGGER.handlers:
        return
    LOGGER.setLevel(resolve_log_level())
    fh = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter(LOG_FILE_FORMAT, LOG_DATE_FORMAT)
    formatter.converter = time.gmtime
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    LOGGER.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(LOG_STREAM_FORMAT, LOG_DATE_FORMAT))
    sh.setLevel(logging.WARNING)
    LOGGER.addHandler(sh)
    LOGGER.propagate = False


@Configuration(type="events")
class UpdateCSVFromExternal(GeneratingCommand):
    """
    updatecsvfromexternal: download a file from a url, save it as a csv optionally in gzipped format

    Example:

    ``| updatecsvfromexternal input_csv=<input_csv> [outputcsv=<csv>]``

    Note: Overwrites existing file without warning
    """

    input_csv = Option(
        require=True,
        doc="""**Syntax:** input_csv=<string>
        **Description:** The input_csv to retrieve the csv from.""",
    )

    output_csv = Option(
        require=False,
        doc="""**Syntax:** output_csv=<string>
        **Description:** The name for the output csv.""",
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
        DEBUG(f"{self.is_compressed=}")
        want_compressed: bool = self.check_want_compressed()
        if want_compressed and not self.is_compressed:
            DEBUG("Wanted compressed, got uncompressed")
            content = gzip.compress(content)
            self.is_compressed = True
        elif not want_compressed and self.is_compressed:
            DEBUG("Wanted uncompressed, got compressed")
            try:
                content = gzip.decompress(content)
                self.is_compressed = False
            except (gzip.BadGzipFile, OSError, EOFError) as e:
                ERROR(f"Failed to decompress data: {e}")
                raise
        return content

    def write_output(self, data: bytes) -> int:
        "Write the lookup. Overwrites current file"
        name: str = os.path.join(LOOKUP_PATH, self.get_csv_name())
        with open(name, "wb") as file:
            bytes_written = file.write(data)
        INFO(f"Wrote {bytes_written} bytes to {name}")
        return bytes_written

    def is_valid_url(self, url):
        return url.endswith(".csv") or url.endswith(".csv.gz")

    def generate(self) -> Generator[dict, None, None]:
        "Run the command at the direction of Splunk"
        INFO(f"{self.input_csv=}")
        INFO(f"{self.output_csv=}")
        url: str = S3_BASE_URL + self.input_csv
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}. Expected *.csv or *.csv.gz")
        resp = requests.get(url, allow_redirects=True)
        INFO(f"{resp.status_code=}")
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
dispatch(UpdateCSVFromExternal, sys.argv, sys.stdin, sys.stdout, __name__)
