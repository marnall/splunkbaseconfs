import os, json, logging, sys
from typing import List

from furl import furl

from lookout_mra_client.lookout_logger import init_lookout_logger
from lookout_mra_client.event_forwarders.splunk_event_forwarder import SPLUNK_EVENT_DELIMITER

import splunklib.client as SplunkClient
from splunk import setupSplunkLogger

LOOKOUT_LOG_FILE = "lookout_mobile_edr_for_splunk.log"
CONTROL_LOOP_INTERVAL = 15  # seconds
CONTROL_LOOP_COUNT = 2  # number of times to run the main loop before exiting


def __get_version():
    this_dir = os.path.dirname(__file__)
    manifest_file = os.path.join(this_dir, "..", "app.manifest")
    with open(manifest_file) as manifest:
        return json.load(manifest)["info"]["id"]["version"]

    return None


APP_VERSION = __get_version()


def connectionsEqual(conn: dict, old_conn: dict) -> bool:
    """
    Helper to compare connection config dictionaries

    Args:
        conn (dict): current connection
        old_conn (dict): old connection

    Returns:
        bool: If the current connection matches the old connection
    """
    return all((old_conn.get(k) == v for k, v in conn.items()))


def setupLogger(instanceType: str) -> logging.Logger:
    """
    Helper to setup a log file within Splunk's logging framework.

    The main log file is stored in Splunk's log location, but a symlink
    is created back to the frontend application to give enterprise customers
    the ability to download the log file. This is not possible for cloud customers
    do to limitations of the cloud environment.

    Args:
        instanceType (str): Splunk instance type, i.e. "cloud", "enterprise"

    Returns:
        logging.Logger: Python logger object
    """
    SPLUNK_HOME = os.environ["SPLUNK_HOME"]
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
    LOGGING_STANZA_NAME = "python"

    logDir = os.path.join(SPLUNK_HOME, "var", "log", "splunk")
    thisDir = os.path.dirname(__file__)
    logFile = os.path.join(logDir, LOOKOUT_LOG_FILE)

    logger = init_lookout_logger(logFile, level=logging.INFO)
    setupSplunkLogger(
        logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME
    )

    # create symlink so that the UI can access and download the log file.
    if instanceType != "cloud":
        linkPath = os.path.join(thisDir, "../appserver/static/javascript/app.log")
        if not os.path.exists(linkPath):
            os.symlink(logFile, linkPath)

    return logger


def formatProxies(routing: dict, secrets: SplunkClient.StoragePasswords) -> dict:
    """
    Format proxy config info into a dict for python Requests library

    Args:
        routing (dict): Routing info from KV_Store
        secrets (SplunkClient.StoragePasswords): Splunk secure storage client

    Returns:
        dict: Proxies {'<scheme>': 'url'}
    """
    proxies = {}
    url = furl(routing.get("proxyEndpoint"))
    if routing.get("proxyUsername"):
        url.username = routing.get("proxyUsername")
        try:
            url.password = secrets[":proxyPassword:"].clear_password
        except KeyError:
            pass
    if url.scheme and url.host and url.port:
        proxies["https"] = url.tostr()
        proxies["http"] = url.tostr()

    return proxies


def eventTypeDisplay(conn: dict) -> str:
    """
    Helper function for formatting the eventType MRA parameter

    Args:
        conn (dict): MRA Connection data

    Returns:
        str: eventType parameter
    """
    types = []
    if conn is None:
        return ""
    if conn["threatEnabled"]:
        types.append("THREAT")
    if conn["deviceEnabled"]:
        types.append("DEVICE")
    if conn["smishingEnabled"]:
        types.append("SMISHING_ALERT")
    if conn["auditEnabled"]:
        types.append("AUDIT")
    return ",".join(types)


def printEvent(event: dict, entName: str) -> None:
    """
    Print MRA event in JSON format.

    TODO: Remove this once fully moved to MRA v2

    As this script is run within a Splunk wrapper, simply
    `print` the event and Splunk will pick it up.

    Args:
        event (dict): MRA event data
        entName (str): Enterprise name
    """
    event["entName"] = entName
    event["details"]["type"] = event["details"].get("type", "UNKNOWN")
    sys.stdout.write(json.dumps(event) + SPLUNK_EVENT_DELIMITER)


def killZombies(
    logger: logging.Logger,
    connections: List[dict],
    historyList: List[dict],
    historyCol: SplunkClient.Collection,
    secrets: SplunkClient.StoragePasswords,
) -> None:
    """
    Clean up zombied history records, as well as zombied oauth tokens

    Args:
        logger (logging.Logger): Internal application logger
        connections (List[dict]): List of connection data
        historyList (List[dict]): List of connection history data
        historyCol (SplunkClient.Collection): Splunk collection object for removing history data
        secrets (SplunkClient.StoragePasswords): Splunk password storage for removing connection tokens
    """
    connectionKeys = list(map(lambda c: c["_key"], connections))
    zombieHistory = list(filter(lambda h: h["connectionKey"] not in connectionKeys, historyList))

    list(map(lambda h: historyCol.data.delete_by_id(h["_key"]), zombieHistory))
    # NOTE: MRA v2 doesn't need to store access tokens as the stream is long living
    # and can hold onto the access token in memeory.
    try:
        list(
            map(
                lambda h: secrets.delete(f"{h['connectionKey']}_tokens"),
                zombieHistory,
            )
        )
    except Exception as e:
        logger.error(f"failed to delete access tokens: {e}")
        pass
    if len(zombieHistory) > 0:
        logger.info(f"Deleted {len(zombieHistory)} zombie historical entries")


def joinThread(
    entKey: str,
    stream_threads: dict,
) -> None:
    """
    Helper to shutdown stream threads

    Args:
        entKey (str): Which ent to shutdown
        stream_threads (dict): Dict of all current stream threads

    Returns:
        None: Null out local thread
    """
    thread = stream_threads.pop(entKey)
    thread.shutdown_flag.set()
    thread.join()
    return None
