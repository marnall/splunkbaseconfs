import sys

from download_mmdb import download_mmdb_file
from app_utils import get_logger


MMDB = "db_sec_pro_ip_residential_proxy"

logger = get_logger("db-" + MMDB + "-mmdb")
logger.info("Request to Download '" + MMDB + "' MMDB from ipgeolocation.io")
session_key = sys.stdin.read()

download_mmdb_file(session_key, "", MMDB)
