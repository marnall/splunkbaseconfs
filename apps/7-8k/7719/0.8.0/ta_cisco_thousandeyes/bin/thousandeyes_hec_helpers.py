import os

import import_declare_test  # noqa: F401
from solnlib.server_info import ServerInfo
from solnlib.hec_config import HECConfig
from solnlib.splunkenv import get_splunkd_access_info

from thousandeyes_utils import is_url_valid
from thousandeyes_constant import (
    SPLUNK_CLOUD_HEC_PORT,
    ENTERPRISE_HEC_STREAM_URL,
    CLOUD_HEC_STREAM_URL,
)
from log_helper import setup_logging

FALLBACK_CLOUD_URL = "https://http-inputs-<host>.splunkcloud.com:<port>/services/collector/event"
FALLBACK_ENTERPRISE_URL = "https://<host>:<port>/services/collector/event"

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())

def generate_stream_url_list(session_key):
    """
    Return potential HEC target URLs for stream configuration.

    :param session_key: Splunk session key

    :return: list of urls
    """
    server = ServerInfo(session_key=session_key)
    hec_settings = HECConfig(session_key=session_key).get_settings()
    hec_port = hec_settings.get("port")
    hec_stack_name = server.server_name.split(".", 1)[-1]
    splunk_info = get_splunkd_access_info()

    valid_urls: list[str] = []

    if server.is_cloud_instance():
        url = CLOUD_HEC_STREAM_URL.format(hec_stack_name, SPLUNK_CLOUD_HEC_PORT)

        valid_urls.append(url if is_url_valid(url, logger) else FALLBACK_CLOUD_URL)
        return valid_urls

    enterprise_urls = [
        ENTERPRISE_HEC_STREAM_URL.format(server.server_name, hec_port),
        ENTERPRISE_HEC_STREAM_URL.format(hec_settings.get("host"), hec_port),
        ENTERPRISE_HEC_STREAM_URL.format(splunk_info[1], splunk_info[2]),
    ]

    for url in enterprise_urls:
        if is_url_valid(url, logger):
            valid_urls.append(url)

    return valid_urls if len(valid_urls) else [FALLBACK_ENTERPRISE_URL]
