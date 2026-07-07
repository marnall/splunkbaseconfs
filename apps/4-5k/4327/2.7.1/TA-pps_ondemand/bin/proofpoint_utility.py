import websocket
import ssl
import os
import json
import datetime
import signal
import time
from six.moves.urllib.parse import quote
from solnlib import conf_manager
import ta_pps_ondemand_declare

import splunk.rest as rest

app_name = __file__.split(os.sep)[-3]

TA_NAME = ta_pps_ondemand_declare.ta_name


def validate_input(helper, definition, input_type):
    """
    Validate the input parameters and provides error to user on UI.

    :param helper: object of BaseModInput class
    :param definition: object containing input parameters
    :param type: type of log data (message OR sendmail)
    """
    interval = int(definition.parameters.get("interval", None))
    if interval < 60 or interval > 300:
        msg = "Retry Interval must be in range 60 seconds to 300 seconds."
        helper.log_error("Error: " + msg)
        raise Exception(msg)


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        TA_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(TA_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all(only_current_app=True)


def check_kvstore_status(session_key):
    """
    Check status of kvstore.

    :param session_key: session key of current session
    """
    kvservice_status = False
    kvstore_status = False
    _, content = rest.simpleRequest(
        "/services/kvstore/status",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    c = json.loads(content)['entry'][0]['content']
    # kvservice
    if c.get('externalKVStore'):
        kvservice_status = c['externalKVStore']['status'] == 'ready'
    # kvstore
    kvstore_status = c['current']['status'] == 'ready'

    if not kvservice_status and not kvstore_status:
        raise Exception("Please enable it to start the data collection.")


def parse_checkpoint_time(stored_time, helper):
    """Parse checkpoint time in new and old format.

    :param stored_time : str
    : return stored checkpoint time
    """
    new_pattern = "%Y-%m-%dT%H:%M:%S.%f%z"
    old_pattern = "%Y-%m-%dT%H:%M:%S%z"

    try:
        stored_time = datetime.datetime.strptime(stored_time, new_pattern).astimezone(tz=None)
        stored_time = stored_time.replace(tzinfo=None)
        return stored_time
    except ValueError as ve:
        helper.log_error("Error while parsing checkpoint time in new format. Checkpoint time = {0} "
                         "Error = {1}".format(stored_time, ve))

    try:
        stored_time = datetime.datetime.strptime(stored_time, old_pattern).astimezone(tz=None)
        stored_time = stored_time.replace(tzinfo=None)
        helper.log_info("Parsed checkpoint time in old format.")
        return stored_time
    except ValueError as ve:
        helper.log_error("Error while parsing checkpoint time in older format. Checkpoint time = {0} "
                         "Error = {1}".format(stored_time, ve))
    raise ValueError("Unable to parse checkpoint time.")


def process_result(result):
    """
    Extract fields used in dashboards.

    :param result: data received
    :return result with additional fields
    """
    result = json.loads(result)
    filter = result.get("filter")
    actions = filter.get("actions")
    action_dkimv = []
    action_spf = []
    action_dmarc = []
    for action in actions:
        isFinal = action.get("isFinal")
        module = action.get("module")
        if module == "dkimv":
            action_dkimv.append(action)
        elif module == "spf":
            action_spf.append(action)
        elif module == "dmarc":
            action_dmarc.append(action)
        if isFinal:
            result["final_action"] = action.get("action")
            result["final_module"] = action.get("module")
            result["final_rule"] = action.get("rule")
    result["action_dkimv"] = action_dkimv
    result["action_spf"] = action_spf
    result["action_dmarc"] = action_dmarc
    return json.dumps(result)


def collect_events(helper, ew, input_type):
    """
    Create websocket connection and fetch logs.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param type: type of log data (message OR sendmail)
    """
    # Check KV Store Status
    session_key = helper.context_meta["session_key"]
    try:
        check_kvstore_status(session_key)
    except Exception as e:
        err_msg = "Error: KV Store is disabled. " + str(e)
        helper.log_error(err_msg)
        # Display notification in Splunk messages
        postargs = {"severity": "error", "name": app_name, "value": app_name + err_msg}
        try:
            rest.simpleRequest("/services/messages", session_key, postargs=postargs)
        except Exception:
            helper.log_error("Error: Failed to give notification message")
        exit(1)
    # Getting parameters
    global_account = helper.get_arg("global_account")
    proxy_settings = helper.get_proxy()
    http_proxy_host = proxy_settings.get("proxy_url")
    http_proxy_port = proxy_settings.get("proxy_port")
    if http_proxy_port:
        http_proxy_port = int(http_proxy_port)
    http_proxy_username = proxy_settings.get("proxy_username")
    http_proxy_password = proxy_settings.get("proxy_password")
    http_proxy_auth = None
    if http_proxy_username or http_proxy_password:
        http_proxy_auth = (http_proxy_username, http_proxy_password)

    websocket_ping_interval = int(helper.get_arg("websocket_ping_interval"))
    cluster_id = global_account.get("username")
    api_key = global_account.get("password")

    input_name = str(helper.get_input_stanza_names())
    helper.log_info("Starting input : {} .".format(input_name))
    delta = datetime.datetime.now() - datetime.datetime.utcnow()
    timezone_hour, timezone_minute = divmod(
        (delta.days * 24 * 60 * 60 + delta.seconds + 30) // 60, 60
    )
    checkpoint = helper.get_check_point(input_name)
    sinceTime = None
    data_count = 0
    enforce_sincetime = helper.get_arg("enforce_sincetime")

    if checkpoint and checkpoint.get(input_type):
        helper.log_info("Checkpoint found with sinceTime: " + str(checkpoint.get(input_type)))
        stored_time = parse_checkpoint_time(checkpoint.get(input_type), helper)
        current_time = datetime.datetime.now()

        # If difference between current time and stored time is more than 60 minutes
        # then we will set sinceTime to last saved checkpoint time.
        if (enforce_sincetime in ("1", "TRUE", "T", "Y", "YES")):
            helper.log_info(
                "Enforcing sinceTime to last stored checkpoint time as checkbox of enforce sinceTime is enabled."
            )
            sinceTime = checkpoint.get(input_type)
        elif (current_time - stored_time).total_seconds() > 3600:
            helper.log_info("Difference between current time and stored checkpoint time is more than 60 minutes."
                            " Setting sinceTime to last stored checkpoint time.")
            sinceTime = checkpoint.get(input_type)
        else:
            helper.log_info("Difference between current time and stored checkpoint time is less than 60 minutes."
                            " Setting sinceTime to None")

    # preparing url and header to create connection
    url = (
        "wss://logstream.proofpoint.com:443/v1/stream?cid=" + quote(str(cluster_id))
        + "&type=" + input_type
        + ("&sinceTime=" + quote(str(sinceTime)) if sinceTime else "")
    )
    helper.log_debug("Request URL: " + url)
    header = {"Authorization": "Bearer %s" % (api_key,)}
    sslopt = {"cert_reqs": ssl.CERT_NONE}

    sourcetype = None
    if input_type == "sendmail":
        sourcetype = "pps_maillog"
    elif input_type == "message":
        sourcetype = "pps_messagelog"
    elif input_type == "audit":
        sourcetype = "pps_auditlog"

    def save_checkpoint():
        """Save the checkpoint, handling failures and retries."""
        attempt = 0
        nonlocal checkpoint  # noqa
        sleep_time = 10
        while True:
            attempt += 1
            helper.log_info(
                'Saving checkpoint in wrapper (name:{}, attempt:{}, checkpoint:{})'
                .format(input_name, attempt, checkpoint)
            )
            try:
                checkpoint = {
                    input_type: "%s%+03d%02d"
                    % (
                        datetime.datetime.now().isoformat(),
                        timezone_hour,
                        timezone_minute
                    )
                }
                helper.save_check_point(input_name, checkpoint)
                helper.log_info('Checkpoint saved successfully on attempt {}'.format(attempt))
                return
            except Exception as save_checkpoint_exc:
                helper.log_error('Failed to save checkpoint: {}'.format(save_checkpoint_exc))
                if attempt >= 5:
                    raise Exception from save_checkpoint_exc
                helper.log_info('Retrying after {} seconds'.format(sleep_time))
                time.sleep(sleep_time)

    def on_open(wsapp):
        helper.log_info("Connection successful.")
        # Save checkpoint to use it in case a retrieval from archive operation took longer than 60 minutes
        if sinceTime is not None:
            save_checkpoint()

    def on_message(wsapp, message):
        nonlocal data_count
        if message:
            if sourcetype == "pps_messagelog":
                message = process_result(message)
            else:
                if not isinstance(message, str):
                    message = message.decode()

            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=sourcetype,
                data=str(message)
            )
            ew.write_event(event)
            data_count += 1
        else:
            # Storing current time when results are not obtained
            helper.log_info("No events found for cluster id: {}".format(cluster_id))
            save_checkpoint()

    def on_error(wsapp, error):
        helper.log_error(error)
        # Moving this save checkpoint to stream events to handle all scenarios
        '''
        # Save checkpoint only if the data was coming from a "real-time" stream
        if sinceTime is None:
            save_checkpoint()
        '''

    def on_close(wsapp, close_status_code, close_msg):
        helper.log_info("Connection closed with code={}, msg={}".format(close_status_code, close_msg))
        # Moving this save checkpoint to stream events to handle all scenarios
        '''
        # Save checkpoint only if the data was coming from a "real-time" stream
        if sinceTime is None:
            save_checkpoint()
        '''

    def signal_handler(sig, frame):
        """Close the connection and threads in case of exception or timeout."""
        try:
            helper.log_info("Successfully handled the SIGTERM signal.")
            if sinceTime is None:
                save_checkpoint()
        except Exception:
            pass

    try:
        wsapp = websocket.WebSocketApp(
            url,
            header=header,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, signal_handler)
        # for unix machine
        else:
            signal.signal(signal.SIGTERM, signal_handler)

        wsapp.run_forever(
            sslopt=sslopt,
            ping_interval=websocket_ping_interval,
            http_proxy_host=http_proxy_host,
            http_proxy_port=http_proxy_port,
            http_proxy_auth=http_proxy_auth
        )
    except Exception as e:
        helper.log_error("Error while creating connection: " + str(e))
        exit(1)

    if sinceTime is None:
        helper.log_info("Connection closed.")
        save_checkpoint()
    helper.log_info("Total events ingested: {}".format(data_count))
    helper.log_info("Exiting input : {} .".format(input_name))
