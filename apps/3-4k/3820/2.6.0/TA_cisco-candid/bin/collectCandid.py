# !/usr/bin/python
from __future__ import print_function
import sys
import os
import candid_logger_manager as log
import hashlib

import splunk.entity as entity
import time
from candidpyclient import RestClient
import json
import string
import xml.sax.saxutils as xss
from splunk.clilib.bundle_paths import make_splunkhome_path

from fabric import Fabric
from Epochs import Epoch
from events import Event

from threadpool import ThreadPool
from splunk.clilib import cli_common as cli

_LOGGER = log.setup_logging("candid_data_collection")
APP_NAME = __file__.split(os.sep)[-3]
upgrade_start_time = None
file_path = make_splunkhome_path(["etc", "apps", APP_NAME, "local", "last_pull_epoch_time.txt"])


def _getCredentials(sessionKey):
    try:
        # list all credentials
        entities = entity.getEntities(["admin", "passwords"], namespace=APP_NAME, owner="nobody", sessionKey=sessionKey)
    except Exception as e:
        _LOGGER.error("NAE Error: Could not get " + str(APP_NAME) + " credentials from splunk. Exception: " + str(e))

    # return set of credentials
    candid_credentials = dict()
    if entities:
        for i, c in entities.items():

            if (str(c["eai:acl"]["app"])) == APP_NAME:
                host = xss.unescape(str(i.split(":")[0]).strip())
                username = xss.unescape(c["username"])
                password = c["clear_password"]
                credential = []
                credential = [username, password]
                candid_credentials[host] = list(credential)
                # return c['username'],c['clear_password'],host

    return candid_credentials


def get_last_epoch_time_from_file(action, host_str=None, end_time=None):
    """Read checkpoint from last_pull_epoch_time."""
    global upgrade_start_time

    if action == "fetch":
        try:
            if os.path.isfile(file_path):
                fd = open(file_path, "r+")
                file_content = fd.read()
                last_epoch_pull_time = json.loads(file_content)
                fd.close()
                if str(last_epoch_pull_time).isdigit():
                    upgrade_start_time = int(last_epoch_pull_time)
                return last_epoch_pull_time
            else:
                return None
        except Exception:
            pass
    if action == "store":
        content = get_last_epoch_time_from_file("fetch")
        if content and not str(content).isdigit():
            content[host_str] = end_time
        else:
            content = {host_str: end_time}
        try:
            with open(file_path, "w+") as data:
                json.dump(content, data, indent=4)
            _LOGGER.debug("Data written in checkpoint file: {data} for host: {host}".format(
                data=content, host=host_str))
        except Exception:
            pass


def get_last_n(last_n=None):
    """Return default configured time by User."""
    try:
        look_back = int(last_n) if last_n.isdigit() else 4
    except Exception:
        look_back = 4
    return look_back


def get_epochs_with_time(ep, endTime, fabric_id=None, candid_host=None, last_n=None, host_str=None):
    """Get list of epochs between given time range."""
    global upgrade_start_time
    last_epoch_time = get_last_epoch_time_from_file("fetch")

    epoch_collection = []
    time_collection = []

    try:
        if not upgrade_start_time:
            if not (last_epoch_time and last_epoch_time.get(host_str)):
                look_back = get_last_n(last_n)
                startTime = endTime - look_back * 60 * 60 * 1000
            else:
                startTime = last_epoch_time.get(host_str) + 1000
        else:
            startTime = upgrade_start_time + 1000

        _LOGGER.info("Fetch epochs for fabric: {fabric} host: {host} between time: {start_time} and {end_time}".format(
            fabric=fabric_id, host=candid_host, start_time=startTime, end_time=endTime))
        resp = ep.get_epochs_by_time(start_time=startTime, end_time=endTime)

        if resp:
            for each in resp:
                time_collection.append(str(each.get("analysis_completion_time_rfc3339")))
                epoch_collection.append(str(each.get("epoch_id")))
        else:
            _LOGGER.warning("NAE Warning: No epochs found for fabric={}, NAE={}".format(fabric_id, candid_host))
            return [], [], []

        return epoch_collection, time_collection, resp
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Could not get epochs from host={} fabric={}. Exception={}".format(
                str(candid_host), str(fabric_id), str(e)
            )
        )
        return [], [], []


def display_epoch_data(epoch_data, fab_id, candid_host):
    """Print epoch event in Splunk."""
    for each in epoch_data:
        each.update({"component": "epoch", "fab_id": str(fab_id), "cnae_host": str(candid_host)})
        print("{}\n".format(json.dumps(each)))


def display_life_cycle(data, fab_id, candid_host, event_id, epoch_id, epoch_complete_time):
    """Print smart_event_lifecycle event in Splunk."""
    for each in data:
        each.update(
            {
                "component": "smart_event_lifecycle",
                "fab_id": str(fab_id),
                "cnae_host": str(candid_host),
                "event_uuid": str(event_id),
                "epoch_id": str(epoch_id),
                "analysis_completion_time_rfc3339": str(epoch_complete_time),
            }
        )
        print("{}\n".format(json.dumps(each)))


global response
response = []


def dict_parse(dictionary, keyset=None):
    """Parse the dictionary content."""
    dict_resp = []
    if isinstance(dictionary, dict):
        for key, val in dictionary.items():
            if isinstance(val, dict):
                for key2, val2 in val.items():
                    if keyset is not None and ("identifier" not in str(key2) or "ep_key" not in str(key2)):
                        dict_parse(val2, keyset=str(keyset) + "_" + str(key) + "_" + str(key2))
                    elif "identifier" not in str(key2) or "ep_key" not in str(key2):
                        dict_parse(val2, keyset=str(key) + "_" + str(key2))
            elif isinstance(val, list) and len(val) > 0:
                if keyset is not None:
                    list_parse(val, str(keyset) + "_" + str(key))
                else:
                    list_parse(val, str(key))
            elif isinstance(val, list) is False or isinstance(val, dict) is False:
                if keyset is None and (
                    "events_by_severity" not in str(keyset) or "identifier" not in str(key)
                ):  # and ('uuid' not in str(keyset) or 'ep_key' not in str(keyset)):
                    dict_resp.append(str(key) + "=" + str(val))
                elif str(val) != "[]" and ("identifier" not in str(key) and "ep_key" not in str(key)):
                    dict_resp.append(str(keyset) + "_" + str(key) + "=" + str(val))
    elif isinstance(dictionary, list) and len(dictionary) > 0:
        list_parse(dictionary, keyset)
    elif isinstance(dictionary, list) is False or isinstance(dictionary, dict) is False:
        if keyset is not None and "ep_key" not in str(keyset):
            dict_resp.append(str(keyset) + "=" + str(dictionary))
    response.append(dict_resp)
    return dict_resp


def list_parse(listed, keys=None):
    """Parse the list content."""
    for each in listed:
        dict_parse(each, keyset=keys)


def display_smart_events(each, epoch=None, complete_time=None, fab_id=None, candid_host=None, component=None):
    """Print smart_event_details event in Splunk."""
    uuid_var = ""
    final_resp = []
    semi_final_response = []
    final_resp.append("component=" + str(component))
    final_resp.append("analysis_completion_time_rfc3339=" + str(complete_time))
    try:
        if "aci_fabric_settings_dto" in each.keys():
            del each["aci_fabric_settings_dto"]
        if "links" in each.keys():
            del each["links"]
        if "primary_affected_object" in each.keys():
            if each["primary_affected_object"]["identifier"]:
                del each["primary_affected_object"]["identifier"]
            # if each['primary_affected_object']['name']:
            #    del(each['primary_affected_object']['name'])
            # if each['primary_affected_object']['type']:
            #    del(each['primary_affected_object']['type'])
        if "epoch_uuid" in each.keys():
            del each["epoch_uuid"]
        if "ep" in each.keys():
            if "ep_key" in each["ep"]:
                del each["ep"]["ep_key"]
            if "events_by_severity" in each["ep"]:
                del each["ep"]["events_by_severity"]
            if "details" in each["ep"]:
                del each["ep"]["details"]["ep_key"]
        if "identifier" in each.keys():
            uuid_var = each["identifier"]
            del each["identifier"]
        if isinstance(each, dict):
            dict_parse(each, None)
        if isinstance(each, list):
            list_parse(each, None)
        for resp in response:
            semi_final_response = semi_final_response + resp
        hash_list = "".join(sorted(semi_final_response))
        try:
            # py2
            hashnopunct = hash_list.translate(None, string.punctuation)
        except TypeError:
            # py3
            table = str.maketrans("", "", string.punctuation)
            hashnopunct = hash_list.translate(table)
        list_hash = hashlib.md5(str(hashnopunct).encode()).hexdigest()
        del response[:]
        each.update({"component": str(component), "analysis_completion_time_rfc3339": str(complete_time)})
        each.update({"hash_key": str(list_hash), "epoch_id": str(epoch)})
        each.update({"fab_id": str(fab_id), "cnae_host": str(candid_host)})
        each.update({"event_uuid": str(uuid_var)})
        print("{}\n".format(json.dumps(each)))
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Failed to parse events for fabric={} host={}. Exception={}".format(
                str(fab_id), str(candid_host), str(e)
            )
        )


# CNAE Redundancy
def _cnaeRedundancy(hosts, username, password, verify_ssl, domain_name, timeout):
    try:
        for host in hosts:
            try:
                host = host.strip()
                url = "https://" + str(host)
                rc = RestClient(url, username, password, verify_ssl, domain_name, timeout)
                return rc, host
            except Exception as e:
                _LOGGER.error(
                    "%% NAE Error: Could not find other NAEs to login:%s, Username:%s, Exception: %s"
                    % (host, username, str(e))
                )
                if len(hosts[1:]) > 0:
                    rc, host = _cnaeRedundancy(hosts[1:], username, password, verify_ssl, domain_name, timeout)
                    return rc, host
                else:
                    _LOGGER.error("Exiting due to no hosts, hosts")
                    return "", ""
    except Exception as e:
        _LOGGER.error(
            "%% NAE Error: Could not connect to any NAEs:%s, Username:%s, Exception: %s" % (hosts, username, str(e))
        )
        return "", ""


def threading_events(event_details, collect_lifecycle):
    """Pick entities from the queue to fetch and display smart events."""
    category = event_details["category"]
    event_uuid = event_details["identifier"]
    ev = event_details["ev"]
    epoch = event_details["epoch"]
    epoch_complete_time = event_details["epoch_complete_time"]
    fab_id = event_details["fabric_id"]
    host = event_details["nae_host"]

    if collect_lifecycle:
        try:
            event_lifecycle_resp = ev.get_event_lifecycle(event_uuid)
            if event_lifecycle_resp:
                _LOGGER.debug(
                    "Smart Event Lifecycle: for epoch: {epochs} for fabric: {fabric} "
                    "for identifier: {identifier} and host: {host}".format(
                        identifier=event_uuid, epochs=str(epoch), fabric=str(fab_id), host=str(host)
                    )
                )

                display_life_cycle(
                    event_lifecycle_resp,
                    fab_id=str(fab_id),
                    candid_host=str(host),
                    event_id=event_uuid,
                    epoch_id=str(epoch),
                    epoch_complete_time=epoch_complete_time,
                )
        except Exception as e:
            _LOGGER.error(
                "NAE Error: Failed to fetch event lifecycle response. host: {} fabric: {} "
                "event_id: {} Exception: {}".format(
                    str(host), str(fab_id), event_uuid, str(e)
                )
            )
            raise
    try:
        data = ev.get_event_details(category=category, uuid=event_uuid)
        if data:
            _LOGGER.debug(
                "Smart Event Details: for epoch: {epochs} for fabric:  {fabric} "
                "for identifier: {identifier} and host: {host}".format(
                    identifier=event_uuid, epochs=str(epoch), fabric=str(fab_id), host=str(host)
                )
            )

            for each in data:
                display_smart_events(
                    each,
                    epoch=str(epoch),
                    complete_time=epoch_complete_time,
                    fab_id=str(fab_id),
                    candid_host=str(host),
                    component="smart_event_details",
                )
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Failed to fetch event details response. host: {} fabric: {} "
            "event_id: {} Exception: {}".format(
                str(host), str(fab_id), event_uuid, str(e)
            )
        )
        raise


def create_job(pool, category, identifier, ev, epoch, epoch_complete_time, fab_id, host, collect_lifecycle):
    """Add tasks in the queue."""
    event_identifier_time = {}
    event_identifier_time["category"] = category
    event_identifier_time["identifier"] = identifier
    event_identifier_time["ev"] = ev
    event_identifier_time["epoch"] = str(epoch)
    event_identifier_time["epoch_complete_time"] = epoch_complete_time
    event_identifier_time["fabric_id"] = str(fab_id)
    event_identifier_time["nae_host"] = str(host)

    # the function which is to be called along with its args
    pool.add_task(threading_events, event_identifier_time, collect_lifecycle)


def main(argv):
    """Driver function and entry point of execution."""
    sessionKey = sys.stdin.readline().strip()
    if len(sessionKey) == 0:
        _LOGGER.error(
            "NAE Error: Did not receive a session key from splunkd. "
            "Please enable passAuth in inputs.conf for this "
            "script\n"
        )
        sys.exit()

    try:
        config = cli.getConfStanza("app_config", "app_setup") or {}
        no_of_threads = int(config.get("no_of_threads", 32))
        if no_of_threads not in range(1, 33):
            _LOGGER.error(
                "NAE Error: Number of threads should be greater than zero and less than or equal to 32. "
                "Please change the value first and then enable the script "
            )
            return
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Error occured while fetching number of threads from app_config.conf "
            "Exception: {}. Defaulting to 32".format(str(e))
        )
        no_of_threads = 32

    try:
        page_size = int(config.get("page_size", 200))
        if page_size <= 0:
            _LOGGER.error(
                "NAE Error: Page Size should be greater than zero. "
                "Please change the value first and then enable the script. "
            )
            return
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Error occured while fetching page size from app_config.conf "
            "Exception: {}. Defaulting to 200".format(str(e))
        )
        page_size = 200

    try:
        timeout = int(config.get("timeout", 120))
        if timeout <= 0:
            _LOGGER.error(
                "NAE Error: Timeout should be greater than zero. "
                "Please change the value first and then enable the script. "
            )
            return
    except Exception as e:
        _LOGGER.error(
            "NAE Error: Error occured while fetching timeout from app_config.conf "
            "Exception: {}. Defaulting to 120".format(str(e))
        )
        timeout = 120

    candid_credentials = _getCredentials(sessionKey)
    thread_pool = []

    for host_str in candid_credentials.keys():
        rc = None
        domain_name = None

        username = candid_credentials[host_str][0].split(",")[0]

        if "\\" in username:
            uname_domain = username.split("\\")
            domain_name = uname_domain[0]
            username = uname_domain[1]

        len_credential = len(candid_credentials[host_str][0].split(","))

        if len_credential == 3:
            collect_lifecycle = 1
            verify_ssl = (
                "False"
                if candid_credentials[host_str][0].split(",")[1].strip().lower() in ["f", "false", "n", "no", "0", ""]
                else "True"
            )
            last_n = candid_credentials[host_str][0].split(",")[2]

        if len_credential == 4:
            collect_lifecycle = candid_credentials[host_str][0].split(",")[1]
            try:
                if not (int(collect_lifecycle) == 0 or int(collect_lifecycle) == 1):
                    collect_lifecycle = "0"
                    _LOGGER.warning(
                        "NAE Warning: Disabling data collection for smart event "
                        "lifecycle for host/s: {host}. To collect lifecycle events set value "
                        "to 1 in passwords.conf. The format is [credential:<name_host>:,<1/0>,"
                        "True,<epoch_hour>".format(host=host_str)
                    )
            except Exception:
                collect_lifecycle = "0"
                _LOGGER.warning(
                    "NAE Warning: Disabling data collection for smart event "
                    "lifecycle for host/s: {host}. To collect lifecycle events set value "
                    "to 1 in passwords.conf. The format is [credential:<name_host>:,<1/0>,"
                    "True,<epoch_hour>".format(host=host_str)
                )
            verify_ssl = (
                "False"
                if candid_credentials[host_str][0].split(",")[2].strip().lower() in ["f", "false", "n", "no", "0", ""]
                else "True"
            )
            last_n = candid_credentials[host_str][0].split(",")[3]

        password = candid_credentials[host_str][1]
        host_list = host_str.split(",")
        host = host_list[0].strip()
        url = "https://" + str(host)  # + ":8443"
        if verify_ssl == "False":
            verify_ssl = False
        else:
            verify_ssl = True
        try:
            rc = RestClient(url, username, password, verify_ssl, domain_name, timeout)
            try:
                # Create a pool of no of threads configured in app_config.conf
                pool = ThreadPool(no_of_threads)
                thread_pool.append(pool)
            except Exception as e:
                _LOGGER.error("NAE Error: Error ocurred while creating threads for host:"
                              + str(host) + ", Exception:" + str(e))
        except Exception as e:
            _LOGGER.error("NAE Error: Could not login to host:" + str(host) + ", Exception:" + str(e))
            if len(host_list) > 1:
                rc, host = _cnaeRedundancy(host_list[1:], username, password, verify_ssl, domain_name, timeout)
        if not rc:
            continue

        try:
            fab = Fabric(rc)
            ids = fab.get_fabric_ids()
            _LOGGER.debug("Total Fabric: {fabric} and Fabrics: {list_ids} for host: {host}".format(
                fabric=len(ids), list_ids=ids, host=str(host)))
        except Exception as e:
            _LOGGER.error("NAE Error: Failed to fetch fabric for host={}. Exception: {}".format(str(host), str(e)))
            continue

        endTime = int(round(time.time()) * 1000)
        latest_collection_time = 0

        for fab_id in ids:
            _LOGGER.debug("Started data collection for fabric: {fabric} and host: {host}".format(
                fabric=str(fab_id), host=str(host)))
            try:
                ep = Epoch(rc, fab_id)
            except Exception as e:
                _LOGGER.error(
                    "NAE Error: Failed to fetch epochs for fabric={} host={}. Exception: {}".format(
                        str(fab_id), str(host), str(e)
                    )
                )
                continue
            try:
                ev = Event(rc, fab_id)
            except Exception as e:
                _LOGGER.error(
                    "NAE Error: Failed to fetch events for fabric={} host={}. Exception: {}".format(
                        str(fab_id), str(host), str(e)
                    )
                )
                continue
            list_of_epochs, epoch_time_list, resp = get_epochs_with_time(
                ep, endTime, fabric_id=str(fab_id), candid_host=str(host), last_n=str(last_n), host_str=host_str
            )

            if resp:
                latest_collection_time_current_fab = resp[0].get("collection_time_msecs")
                latest_collection_time = max(latest_collection_time, latest_collection_time_current_fab)

            if list_of_epochs and resp:
                _LOGGER.info(
                    "Total Epochs: {epochs} and Epochs: {list_epochs} for fabric: {fabric} "
                    "and host: {host}".format(
                        epochs=len(list_of_epochs), list_epochs=list_of_epochs, fabric=str(fab_id), host=str(host)
                    )
                )

                for epoch in list_of_epochs:
                    _LOGGER.debug(
                        "Working on Epochs: {epochs} for fabric: {fabric} "
                        "and host: {host}".format(
                            epochs=str(epoch), fabric=str(fab_id), host=str(host)
                        )
                    )

                    paramdict = {"$epoch_id": str(epoch), "$size": str(page_size)}

                    try:
                        identifiers_start_time = time.time()
                        _LOGGER.info(
                            "Collecting Identifiers for epoch={epochs} fabric={fabric} "
                            "host={host}".format(
                                epochs=epoch, fabric=fab_id, host=host
                            )
                        )
                        smart_events_identifier_category = ev.get_events(param_dict=paramdict)
                        list_index = list_of_epochs.index(epoch)
                        epoch_complete_time = epoch_time_list[list_index]
                        if smart_events_identifier_category:
                            _LOGGER.info(
                                "Collected Identifiers. Number of Identifiers={} for epoch={} fabric={} "
                                "host={}. Time Taken= {} minutes. ".format(
                                    len(smart_events_identifier_category), str(epoch), str(fab_id), str(
                                        host), ((time.time() - identifiers_start_time) / 60)
                                )
                            )
                            for values in smart_events_identifier_category:
                                create_job(pool, values["category"], values["identifier"], ev,
                                           epoch, epoch_complete_time, fab_id, host, int(collect_lifecycle))
                    except Exception as e:
                        _LOGGER.error(
                            "NAE Error: Failed to get smart events for epoch={} fabric={} host={} "
                            "Exception: {} ".format(str(epoch), str(fab_id), str(host), str(e))
                        )
                        continue
            if resp:
                display_epoch_data(resp, fab_id, host)

        if latest_collection_time != 0:
            get_last_epoch_time_from_file("store", host_str, latest_collection_time)

    # wait for all threads to complete
    for pools in thread_pool:
        pools.wait_completion()


if __name__ == "__main__":
    script_start_time = time.time()
    _LOGGER.info("Script Invoked")
    main(sys.argv[1])
    _LOGGER.info("Execution of the script is finished. Time taken: {} minutes.".format(
        (time.time() - script_start_time) / 60))
