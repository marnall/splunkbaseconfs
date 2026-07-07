import os
import sys

from state_store import Credentials

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import sys

from cyberintegrations import DRPPoller
from constants import AppConsts
from utils import Utils
from splunklib.modularinput import *
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch



@Configuration(type="reporting")
class gibgetbrands(GeneratingCommand):
    username = Option(require=False)

    def generate(self):
        logger = Utils.get_logger(
            use_small_log_size=Utils.read_conf("limit_the_size_of_logs_to_100_mb"),
            use_debug_log_level=Utils.read_conf("use_debug_log_level"),
            log_filename="modinput_get_brands.log"
        )
        logger.info("Starting generate method")
        session_key = super().service.__dict__.get("token")
        provided_username = getattr(self, "username", None)
        if provided_username:
            USERNAME = provided_username
            logger.info(f"Using provided username: {USERNAME}")
        else:
            USERNAME = Credentials.get_username(session_key, logger)
            logger.info(f"Retrieved username: {USERNAME}")
        API_KEY = Credentials.get_api_key(session_key, USERNAME, logger)
        logger.debug("API key retrieved")
        PROXY_ENABLED = Utils.read_conf("enable_proxy")
        logger.debug(f"Proxy enabled: {PROXY_ENABLED}")
        try:
            poller = DRPPoller(
                username=USERNAME,
                api_key=API_KEY,
                api_url="https://drp.group-ib.com/client_api/",
            )
            logger.debug("TIPoller initialized")
            poller.set_verify(True)
            poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
            if PROXY_ENABLED == "1":
                PROXY_ADDRESS = Utils.read_conf("proxy_address")
                PROXY_PORT = Utils.read_conf("proxy_port")
                PROXY_PROTOCOL = Utils.read_conf("proxy_protocol")
                poller.set_proxies(PROXY_PROTOCOL, PROXY_ADDRESS, PROXY_PORT)
                logger.debug("Proxy settings applied")
            else:
                logger.debug("Proxy not enabled")

            brands = poller.get_brands()
            yield {"Brands":brands}

        except Exception as e:
            logger.error(f"Error during generate: {str(e)}")
            yield {"error": str(e)}
        finally:
            poller.close_session()
            logger.info("Session closed")


dispatch(gibgetbrands, sys.argv, sys.stdin, sys.stdout, __name__)
