# bp_utils
import ssl
from future.moves.urllib import request
from future.moves.urllib.parse import urlparse, urlunparse, urlencode
from ta_bigpanda.logging_helper import get_logger

logger = get_logger("bigpanda_action_manager")


# Helper function to disable proxy usage
def disable_proxy():
    # Disable proxy usage
    logger.info("Disabling global proxy.")
    noproxy = request.ProxyHandler({})
    opener = request.build_opener(noproxy)
    request.install_opener(opener)


# Helper function to disable SSL verification
def disable_ssl_verification():
    # Create an SSL context to disable certificate verification
    logger.info("Disabling SSL verification.")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def normalize_url(url, actions):
    try:
        parsed_url = urlparse(url)
        port = parsed_url.port
        return urlunparse(parsed_url._replace(
            scheme="https",
            netloc=f"localhost:{port if port else 8089}",
            query=urlencode({'actions': actions})
        ))
    except Exception as e:
        logger.error(f"Failed to normalize URL: {e}")
        return None
