import datetime, json, os, sys, threading, logging
from typing import Union, List

# gives access to python libraries in the lib/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from lookout_mra_client.mra_client import MRAClient
from lookout_mra_client.lookout_logger import init_lookout_logger

import splunklib.client as SplunkClient
from splunk import setupSplunkLogger

from helpers import formatProxies, eventTypeDisplay, printEvent, killZombies, APP_VERSION


# TODO: python classes for routing/conn/history?
def event_fetcher(
    logger: logging.Logger,
    routing: dict,
    conn: dict,
    history: dict,
    historyCol: SplunkClient.Collection,
    secrets: SplunkClient.StoragePasswords,
) -> None:
    """
    Fetch events from Lookout's MRA using a given connection config

    Args:
        logger (logging.Logger): Internal application logger
        routing (dict): Routing info to reach Lookout
        conn (dict): Connection info for a single enterprise
        history (dict): History of this connection
        historyCol (splunklib.client.Collection): KV_Store collection updating historical data
        secrets (splunklib.client.StoragePasswords): Splunk secure storage client
    """
    entName = conn["entName"]
    threadName = threading.current_thread().name
    logger.info("{} - Beginning work".format(threadName))

    # Use current stream position if populated, else use starting position.
    # streamPosition is a str of a number or the word 'now'
    streamPosition: Union[str, int] = history.get("currentStreamPosition") or conn["streamPosition"]
    if not isinstance(streamPosition, int) and streamPosition.isdigit():
        streamPosition = int(streamPosition)

    proxies = formatProxies(routing, secrets)

    apiKey = secrets[":{}:".format(conn["_key"])]
    tokensKey = "{}_{}".format(conn["_key"], "tokens")

    eventTypes = eventTypeDisplay(conn)
    logger.info(
        "{} - Fetching {} events starting at position: {}".format(
            threadName, eventTypes, streamPosition
        )
    )

    # Initialize a new MRA client
    mra = MRAClient(
        routing["endpoint"],
        apiKey.clear_password,
        streamPosition,
        None,  # start_time
        eventTypes,
        proxies,
        user_agent=f"LookoutSplunk/{APP_VERSION}",
    )

    # Attempt to load MRA Oauth tokens from Splunk to save API calls
    tokens = {}
    try:
        tokens = json.loads(secrets[":{}:".format(tokensKey)].clear_password)
    except KeyError:
        pass
    mra.oauth.access_token = tokens.get("access")

    # Attempt to retrieve events from MRA
    events = []
    try:
        events = mra.get_events()
        history["exception"] = None
    except Exception as e:
        history["exception"] = str(e)
        logger.error("{} - Failed to retrieve events from MRA: {}".format(threadName, e))

    # Send events to splunk and update history
    eventCount = int(history.get("eventCount") or 0)
    if len(events) > 0:
        list(map(lambda e: printEvent(e, entName), events))
        logger.info("{} - Wrote '{}' events to Splunk".format(threadName, len(events)))
        eventCount += len(events)

        # Store MRA Oauth tokens in Splunk's encrypted store for the next run
        freshTokens = {
            "access": mra.oauth.access_token,
        }
        if not tokens:
            secrets.create(json.dumps(freshTokens), tokensKey)
        elif tokens and freshTokens != tokens:
            secrets[":{}:".format(tokensKey)].update(password=json.dumps(freshTokens))
    else:
        logger.info("{} - No events forwarded to Splunk".format(threadName))

    # Update history even if no events were fetched
    history["eventCount"] = eventCount
    history["lastEventDate"] = str(datetime.datetime.now())
    history["currentStreamPosition"] = mra.stream_position

    if history.get("_key"):
        historyCol.data.update(history["_key"], json.dumps(history))
    else:
        history["connectionKey"] = conn["_key"]
        historyCol.data.insert(json.dumps(history))


def main() -> None:
    """
    This script is run in a wrapper by Splunk and can't be run on its own.
    When Splunk starts the script an authenication token is supplied on the command line.
    This token allows for access to all of Splunk's APIs.
    """
    sessionKey: str = sys.stdin.readline().strip()
    # TODO: I think this actually is no longer necessary as I have fixed the method for
    #   connecting to splunk's KV store and no longer doing raw requests to localhost.
    # EMM-8558: force no proxy for localhost requests.
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    SPLUNK_HOME = os.environ["SPLUNK_HOME"]

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
    LOGGING_STANZA_NAME = "python"

    log_directory = os.path.join(SPLUNK_HOME, "var", "log", "splunk")
    logFile = os.path.join(log_directory, "lookout_mobile_edr_for_splunk.log")

    thisDir = os.path.dirname(__file__)
    logger = init_lookout_logger(logFile)
    setupSplunkLogger(
        logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME
    )
    logger.info("--- Lookout Mobile Risk API - Event Retrieval Loop ---")

    logger.info(f"Current Version: {APP_VERSION}")

    splunkService: SplunkClient.Service = SplunkClient.connect(
        owner="nobody",
        app="lookout_mobile_edr_for_splunk",
        sharing="app",
        token=sessionKey,
    )
    routingCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_routing"]
    connectionCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_connection"]
    historyCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_history"]
    secrets: SplunkClient.StoragePasswords = splunkService.storage_passwords

    # create symlink so that the UI can access and download the log file.
    instanceType = splunkService.info().get("instance_type")
    if instanceType != "cloud":
        linkPath = os.path.join(thisDir, "../appserver/static/javascript/app.log")
        if not os.path.exists(linkPath):
            os.symlink(logFile, linkPath)

    logger.info("Established connection to Splunk API")

    # Pull routing data from the kv_store
    #   if no routing data, log and kill the script
    try:
        routing: dict = routingCol.data.query()[0]
    except Exception as e:
        logger.info(
            "Could not load routing data, configuration may not be complete. Error: {}".format(e)
        )
        return

    # Pull connection and history data from the kv_store
    #   format historical data into a dict to easily tie back to a connection
    connections: List[dict] = connectionCol.data.query()
    historyList: List[dict] = historyCol.data.query()
    historyDict: dict = {h["connectionKey"]: h for h in historyList}

    # Start workers for each connection
    logger.info("Beginning work on '{}' mra connection(s)".format(len(connections)))
    threads = []
    for conn in connections:
        entKey = conn["_key"]
        entName = conn["entName"]
        threadName = "{}:{}".format(entKey, entName)
        if not conn["isActive"]:
            logger.info("'{}' is paused, skipping".format(threadName))
            continue
        opts = {
            "logger": logger,
            "routing": routing,
            "conn": conn,
            "history": historyDict.get(entKey) or {},
            "historyCol": historyCol,
            "secrets": secrets,
        }
        thread = threading.Thread(name=threadName, target=event_fetcher, kwargs=opts)
        thread.start()
        threads.append(thread)
    list(map(lambda t: t.join(), threads))
    logger.info("Joined worker threads")

    killZombies(logger, connections, historyList, historyCol, secrets)

    logger.info("--- End of Event Retrieval Loop ---")


if __name__ == "__main__":
    main()
