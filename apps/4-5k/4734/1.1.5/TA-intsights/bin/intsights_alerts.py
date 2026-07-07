"""IntSights scheduled input script to gather alerts and ingest if requested."""
import intsights_client
import logging
import os
import re
import splunk.version as ver
import splunk_client
import sys
import time
from logging.handlers import RotatingFileHandler

# App name and configurations
APP_NAME = "TA-intsights"
STANZA_NAME = "thread-command"
CONF_NAME = "intsights"

# setup lock file
current_path = os.path.dirname(os.path.realpath(__file__))
LOCK_FILE = os.path.join(current_path, "intsights_alerts.lock")

# IntSights API
MAX_SESSION_TIME_IN_SECONDS = 30 * 60
FOUND_DATE_IN_MS = int(round((time.time() - 60 * 60) * 1000))
ALERT_PARAMS_SET = [
    {
        'foundDateFrom': FOUND_DATE_IN_MS
    },
    {
        'foundDateFrom': FOUND_DATE_IN_MS,
        'isClosed': 'true'
    }
]

# Splunk variables
SOURCE_TO_PUSH_TO = "intsights_alerts"
SEARCH_QUERY = "search source={}".format(SOURCE_TO_PUSH_TO)
SESSION_KEY = sys.stdin.readline().strip()

try:
    if "authString" in SESSION_KEY:
        auth_token_match = re.search('<authToken>(?P<authtoken>[^<]+)', SESSION_KEY)
        SESSION_KEY = auth_token_match.group('authtoken')
        LOGGER.debug("Script called via command instead of from inputs.conf.")
except Exception:
    LOGGER.exception("Failed to extract a session key from splunk. Make sure to enable passauth=true in inputs.conf and commands.conf.")

VERSION = float(re.search(r"(\d+.\d+)", ver.__version__).group(1))
MAXBYTES = 2000000

PROXY = None

# attempt to build backwards compatible paths
try:
    if VERSION >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError as e:
    raise ImportError("Import splunk sub libraries failed\n")

# setup log
log_path = make_splunkhome_path(["var", "log", "intsights"])

# handle missing logs by making new log
if not os.path.isdir(log_path):
    os.makedirs(log_path)

# associate handler to logger and setup logging prefs
handler = RotatingFileHandler(
    os.path.join(
        log_path + '/intsights.log'
    ),
    maxBytes=MAXBYTES,
    backupCount=20
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
LOGGER = logging.getLogger("intsights_alerts")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(handler)


def get_alert_by_id(intsights_service, alert_id):
    """Use intsights class to get alert id."""
    try:
        LOGGER.debug("Trying to pull down complete alerts")

        complete_alert = intsights_service.get_complete_alert_by_id(
            params={},
            alert_id=alert_id
        )

        return complete_alert

    except Exception as e:
        LOGGER.debug('Could not get_alert_by_id to IntSights. Exception - {} '.format(e))
        raise e


def ingest_alerts():
    """Use splunk client class and Intsights API to push alerts."""
    # attempt to create splunk client and post alerts
    try:
        splunk_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, STANZA_NAME, LOGGER)
        ingestion_enabled = splunk_service.alerts_ingestion_enabled()

        if(ingestion_enabled is None):
            LOGGER.debug('App setup has not been run, no alert ingestion possible. Exiting...')
            return False

        if ingestion_enabled == 0:
            LOGGER.debug('Selected not to ingest Thread Command alerts. Exiting...')
            return False

        if ingestion_enabled == 1:
            LOGGER.debug('Selected to ingest Thread Command alerts.')
            LOGGER.info('Initiating contact with IntSights')

            account_id, api_key = splunk_service.get_intsights_creds('tenant')
            intsights_service = intsights_client.IntSightsClient(account_id, api_key, LOGGER, PROXY)

            intsights_alert_ids = []

            for params in ALERT_PARAMS_SET:
                intsights_alert_ids.extend(intsights_service.get_alerts(params=params))

            LOGGER.debug('intsights_alert_ids: {}'.format(intsights_alert_ids))

            if not intsights_alert_ids:
                LOGGER.warning('No alerts were found. Exiting...')
                return False

            # Connect to Splunk
            LOGGER.info('Initiating contact with Splunk')

            # Get IntSights data from Splunk
            splunk_alert_ids = splunk_service.get_alerts()

            LOGGER.debug('splunk_alert_ids: {}'.format(splunk_alert_ids))
            LOGGER.debug('len of splunk_alert_ids: {}'.format(len(splunk_alert_ids)))

            # Difference IntSights vs Splunk
            alerts_to_add = list(set(intsights_alert_ids) - splunk_alert_ids)

            LOGGER.debug('alerts_to_add: {}'.format(alerts_to_add))

            if not alerts_to_add:
                LOGGER.warning('No alerts to add. Exiting...')
                return False

            LOGGER.debug('Getting complete alerts from IntSights')
            complete_alerts = [get_alert_by_id(intsights_service, alert_id) for alert_id in alerts_to_add]

            LOGGER.debug('Pushing alerts to Splunk')
            splunk_service.push_alerts(complete_alerts)

            return True

    except Exception as e:
        LOGGER.exception("Fatal error ingest_alerts in IntSights")
        raise e


def is_proxy_used():
    """Function to check if we should be including a proxy object with requests."""
    global PROXY
    try:
        splunk_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, STANZA_NAME, LOGGER)

        proxy_user, proxy_authentication = splunk_service.get_proxy_creds()

        proxy_address = None

        LOGGER.debug("Pulling proxy server")
        splunk_proxy_service = splunk_client.SplunkClient(SESSION_KEY, APP_NAME, CONF_NAME, "intsights-config", LOGGER)
        proxy_address = splunk_proxy_service.get_proxy_address()

        if(proxy_address is None):
            LOGGER.debug("No proxy in requests")
            PROXY = None
            return False
        else:
            LOGGER.debug("Updating requests to include proxy: " + str(proxy_address))
            keyval = ""

            if("https:" in proxy_address):
                keyval = "https"
                proxy_with_auth = ""
                if(proxy_user is not None and proxy_authentication is not None):
                    proxy_with_auth = "https://" + proxy_user + ":" + proxy_authentication + "@" + proxy_address.split("https://")[1]
                else:
                    proxy_with_auth = proxy_address

                PROXY = {keyval: proxy_with_auth}
                LOGGER.debug("Created proxy object.")
                return True
            else:
                keyval = "http"
                LOGGER.warning("Please use a secure proxy server with https support")
                raise Exception("Using HTTP instead of HTTPS")
                return False
    except Exception as ex:
        LOGGER.warning("Exception attempting to gather proxy details.")
        LOGGER.error(ex)
        raise Exception(ex)
        return False

if __name__ == "__main__":
    # run only if lock file is not presetn
    if not os.path.exists(LOCK_FILE):

        with open(LOCK_FILE, 'a') as l:
            LOGGER.debug("Creating lock file.")
            l.write("Script is running...\n")

        # attempt to ingest alerts
        try:

            use_proxy = is_proxy_used()

            ingested = ingest_alerts()

            if(ingested is False):
                LOGGER.error("Script was not able to ingest alerts - check setup.")
            else:
                LOGGER.info("Script completed successfully.")

        except Exception as e:
            LOGGER.exception(
                'Fatal error in main loop. '
                'Error: {0}'.format(e)
            )

        # remove lock file
        os.remove(LOCK_FILE)
        LOGGER.debug("Lock file removed.")

    else:
        LOGGER.error("Lock detected by another instance of script. "
                     "Exiting current iteration of script without getting new alerts.")
