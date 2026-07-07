import datetime, os, sys, json, logging
from time import sleep
from typing import List

# gives access to python libraries in the lib/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from lookout_mra_client.mra_v2_stream_thread import MRAv2StreamThread
from lookout_mra_client.event_forwarders.splunk_event_forwarder import SplunkEventForwarder

import splunklib.client as SplunkClient

from helpers import (
    connectionsEqual,
    setupLogger,
    formatProxies,
    eventTypeDisplay,
    joinThread,
    killZombies,
    CONTROL_LOOP_INTERVAL,
    CONTROL_LOOP_COUNT,
    APP_VERSION,
)


def updateEventCount(
    logger: logging.Logger,
    conn: dict,
    history: dict,
    historyCol: SplunkClient.Collection,
    threadName,
    events,
):
    # Update eventCount in history
    eventCount = int(history.get("eventCount") or 0)
    if len(events) > 0:
        logger.info(f"{threadName} - Wrote '{len(events)}' events to Splunk")
        eventCount += len(events)
        history["currentStreamPosition"] = events[-1]["id"]
    else:
        logger.info(f"{threadName} - No events forwarded to Splunk")

    # Update history even if no events were fetched
    history["eventCount"] = eventCount
    history["lastEventDate"] = str(datetime.datetime.now())
    # Reset any error messages
    history["exception"] = None

    logger.info(f"Updating eventCount in history: {history}")
    if history.get("_key"):
        historyCol.data.update(history["_key"], json.dumps(history))
    else:
        history["connectionKey"] = conn["_key"]
        historyCol.data.insert(json.dumps(history))


def initStreamThread(
    logger: logging.Logger,
    threadName: str,
    routing: dict,
    conn: dict,
    history: dict,
    historyCol: SplunkClient.Collection,
    secrets: SplunkClient.StoragePasswords,
) -> MRAv2StreamThread:
    """
    Initialize a MRA v2 stream thread

    Args:
        routing (dict): Routing info to reach Lookout
        conn (dict): Connection info for a single enterprise
        history (dict): History of this connection
        historyCol (splunklib.client.Collection): KV_Store collection updating historical data
        secrets (splunklib.client.StoragePasswords): Splunk secure storage client

    Returns:
        MRAv2StreamThread: MRA v2 stream ready to start
    """
    entName = conn["entName"]
    # Use current stream position if populated, else use starting position.
    lastEventId: str = history.get("currentStreamPosition") or conn["streamPosition"]

    proxies = formatProxies(routing, secrets)

    api_key = secrets[f":{conn['_key']}:"]
    eventTypes = eventTypeDisplay(conn)

    forwarder = SplunkEventForwarder(
        callback=lambda events: updateEventCount(
            logger, conn, history, historyCol, threadName, events
        )
    )
    stream_args = {
        "api_domain": routing["endpoint"],
        "api_key": api_key.clear_password,
        "last_event_id": lastEventId,
        "event_type": eventTypes,
        "proxies": proxies,
        "user_agent": f"LookoutSplunkMRAv2/{APP_VERSION}",
    }
    thread = MRAv2StreamThread(entName, forwarder, **stream_args)
    thread.name = threadName

    return thread


def main() -> None:
    """
    This script is run in a wrapper by Splunk and can't be run on its own.
    When Splunk starts the script an authenication token is supplied on the command line.
    This token allows for access to all of Splunk's APIs.
    """
    try:
        sessionKey: str = sys.stdin.readline().strip()

        splunkService: SplunkClient.Service = SplunkClient.connect(
            owner="nobody",
            app="lookout_mobile_edr_for_splunk",
            sharing="app",
            token=sessionKey,
        )
        instanceType = splunkService.info().get("instance_type")
        logger = setupLogger(instanceType)
        logger.info(f"Logged into splunk with key: {sessionKey}, on instance type: {instanceType}")

        logger.info(f"Current Version: {APP_VERSION}")

        try:
            routingCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_routing"]
            connectionCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_connection"]
            historyCol: SplunkClient.Collection = splunkService.kvstore["lookout_mra_history"]
            secrets: SplunkClient.StoragePasswords = splunkService.storage_passwords
        except Exception:
            logger.exception(f"Failed to connect to KV store.")
            sys.exit(1)

        logger.info("Established connection to Splunk API")

        streamThreads = {}
        oldConnections = {}
        loopCount = 0
        while loopCount < CONTROL_LOOP_COUNT:
            logger.info(f"{'-'*5} Lookout MRA v2 Control Loop #{loopCount} {'-'*7}")

            # Pull routing data from the kv_store
            #   if no routing data, log and kill the script
            try:
                routing: dict = routingCol.data.query()[0]
            except Exception as e:
                logger.info(
                    f"Could not load routing data, configuration may not be complete. Error: {e}"
                )
                sys.exit(0)

            # Pull connection and history data from the kv_store
            #   format historical data into a dict to easily tie back to a connection
            connections: List[dict] = connectionCol.data.query()
            historyList: List[dict] = historyCol.data.query()
            historyDict: dict = {h["connectionKey"]: h for h in historyList}

            logger.info(f"Begin processing '{len(connections)}' mra connection(s)")
            logger.info(f"  history records: {len(historyList)}")
            logger.info(f"  thread count: {len(streamThreads.keys())}")

            # Start/Manage workers for each connection
            for conn in connections:
                entKey = conn["_key"]
                entName = conn["entName"]
                threadName = f"{entKey}:{entName}"

                history: dict = historyDict.get(entKey, {})

                logger.info(f"Working on '{threadName}'")
                thread = streamThreads.get(entKey)
                # corner case for inital iteration
                if not oldConnections.get(entKey):
                    oldConnections[entKey] = conn

                if thread:
                    if not thread.is_alive():
                        logger.info("thread exists, thread is stopped -> join thread")
                        if thread.error:
                            logger.error(f"Thread error:", exc_info=thread.error)
                            history["exception"] = str(thread.error[1])
                        thread = joinThread(entKey, streamThreads)
                    elif not connectionsEqual(conn, oldConnections.get(entKey, {})):
                        logger.info("thread exists, config outdated -> join thread")
                        thread = joinThread(entKey, streamThreads)
                    else:
                        logger.info("thread exists, no change required -> next")
                        # reset error message
                        history["exception"] = None

                # re-check thread absence for quick restart
                if not thread:
                    if conn["isActive"]:
                        logger.info("thread doesn't exist, config is active -> init new thread")
                        thread = initStreamThread(
                            logger,
                            threadName,
                            routing,
                            conn,
                            history,
                            historyCol,
                            secrets,
                        )
                        thread.start()
                        streamThreads[entKey] = thread
                        history["exception"] = None
                    else:
                        logger.info("thread doesn't exist, config is paused -> next")
                        continue

                oldConnections[entKey] = conn

                history["currentStreamPosition"] = thread.stream.last_event_id

                logger.info(f"creating/updating history: {history}")
                if history.get("_key"):
                    historyCol.data.update(history["_key"], json.dumps(history))
                else:
                    history["connectionKey"] = conn["_key"]
                    historyCol.data.insert(json.dumps(history))

            threadKeys = streamThreads.keys()
            connKeys = list(map(lambda c: c["_key"], connections))
            zombieThreadKeys = list(filter(lambda key: key not in connKeys, threadKeys))

            if len(zombieThreadKeys) > 0:
                logger.info(f"Joining {len(zombieThreadKeys)} zombie threads")
                list(map(lambda t: joinThread(t, streamThreads), zombieThreadKeys))
            killZombies(logger, connections, historyList, historyCol, secrets)

            logger.info(f"{'-'*5} Control Loop End, Sleeping for {CONTROL_LOOP_INTERVAL}s {'-'*5}")
            sleep(CONTROL_LOOP_INTERVAL)
            loopCount += 1

        logger.info(f"{'-'*5} Exiting script to flush all events {'-'*5}")
        logger.info("Shutting down all threads")
        for entKey in list(streamThreads.keys()):
            logger.info(f"Joining thread for {entKey}")
            joinThread(entKey, streamThreads)

    except Exception:
        logger.exception("Exception in main:")


if __name__ == "__main__":
    main()
