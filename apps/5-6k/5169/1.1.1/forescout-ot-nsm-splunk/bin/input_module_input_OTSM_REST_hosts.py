import base64
import json
import time
import sys
import splunklib.client as client
import splunklib.results as results


def validate_input(helper, definition):
    number_of_hosts_per_interval = int(definition.parameters.get("number_of_hosts_per_interval", 0))
    if number_of_hosts_per_interval < 1:
        raise Exception("Number of hosts per interval must be positive")
    if number_of_hosts_per_interval > 1000:
        raise Exception("Cannot fetch more than 1000 hosts per interval")


def collect_events(helper, ew):
    helper.log_info("START")

    cc_address = helper.get_arg("otsm_cc_server")

    checkpoint_host_id = "id_hosts|{}".format(cc_address)
    checkpoint_time_last_group = "host_group_time|{}".format(cc_address)

    last_time = 0
    if helper.get_check_point(checkpoint_time_last_group) is not None:
        last_time = helper.get_check_point(checkpoint_time_last_group)

    current_time = time.time()
    helper.log_info(f"current_time is {current_time}, last_time is {last_time}")

    if current_time < last_time + int(helper.get_arg("interval_between_host_updates")):
        helper.log_info("Not enough time passed since all the hosts were updated. "
                        "Skipping this iteration. Current time is {}.".format(current_time))
        return ""

    global_account = helper.get_arg("global_account")

    credentials = global_account["username"] + ":" + global_account["password"]
    credentials = str(base64.b64encode(credentials.encode("utf-8")))
    credentials = credentials.replace("b'", "").replace("='", "=")

    hdr = {"Authorization": "Basic " + credentials}

    id_min = "0"
    if helper.get_check_point(checkpoint_host_id) is not None:
        id_min = int(helper.get_check_point(checkpoint_host_id)) + 1

    number_hosts = int(helper.get_arg("number_of_hosts_per_interval"))

    helper.log_info(f"id_min is {id_min}, number of hosts is {number_hosts}")

    # Number of hosts to fetch

    url = "https://{}/api/v1/hosts?full=true&sort_ascending=true&id_min={}&limit={}".format(
        cc_address, id_min, number_hosts
    )

    try:
        # send request
        response = helper.send_http_request(
            url, "GET", headers=hdr, verify=False, use_proxy=False
        )
    except:
        helper.log_info("Could not send request:" + str(sys.exc_info()))

        # skip further processing
        return ""

    try:
        # load json data from response
        data = response.json()
    except:
        helper.log_info(
            "Server response cannot be converted to JSON." + str(sys.exc_info())
        )

        # skip further processing
        return ""

    try:
        # get total record count
        records = len(data["results"])

        helper.log_info("Server replied " + str(records) + " results.")
    except:
        helper.log_info("Server reply is malformed." + str(sys.exc_info()))

        # skip further processing
        return ""

    i = 0

    # loop through all records, store them in index
    while i != records:
        event_data = json.dumps(data["results"][i])

        event = helper.new_event(
            host=cc_address,
            time=time.time(),
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=event_data,
        )

        ew.write_event(event)

        i += 1

    # store checkpoint
    if records == number_hosts:
        id_last = data["results"][-1]["id"]

        helper.save_check_point(checkpoint_host_id, id_last)

        helper.log_info("Saved checkpoint with ID: " + str(id_last))

    else:
        helper.delete_check_point(checkpoint_host_id)

        helper.save_check_point(checkpoint_time_last_group, current_time)

        helper.log_info("Resetting checkpoint. Epoch when finishing updating the group is {}".format(current_time))

    helper.log_info("Completed successfully!")
