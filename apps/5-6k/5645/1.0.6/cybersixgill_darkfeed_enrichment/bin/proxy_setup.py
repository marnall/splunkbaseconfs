"""Configure proxy values from the user and setup the connection syntax."""
from typing import Optional, Union

from splunk.clilib import cli_common as cli
from utils import setup_logging

logger = setup_logging(__name__)


def getproxy() -> Union[dict[str, Optional[str]], Exception]:
    """Retrieve and configure proxy settings from Splunk configuration.

    This function reads proxy configuration from the 'sixgillproxy' stanza in Splunk's
    configuration and formats it into a dictionary suitable for use with requests.

    Returns:
        Union[dict[str, Optional[str]], Exception]:
            - A dictionary with 'http' and 'https' keys and string values when proxy is configured
            - An empty dictionary when no proxy is configured
            - An Exception object if an error occurs

    Raises:
        Exception: If there's an error reading the configuration or processing the proxy settings

    """
    try:
        cfg = cli.getConfStanza("sixgillproxy", "sixgillproxy")
        host = cfg.get("host")

        if host:
            port = int(cfg.get("port"))
            if not port:
                port = 80
            username = cfg.get("proxy_uname")
            password = cfg.get("proxy_pswd")

            if username and password:
                netloc = "%s:%s@%s:%d" % (username, password, host, port)
            else:
                netloc = "%s:%d" % (host, port)

            proxy = {
                "http": netloc,
                "https": netloc,
            }
        else:
            proxy = {}

        return proxy

    except Exception as err:
        logger.exception(err)
        return err
