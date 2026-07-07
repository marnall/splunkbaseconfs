# encoding = utf-8

import json


from dragoslib import platform_input_utils as dragos_platform_input_utils


def submit_request_to_platform_api(session, page_number, preferred_batch_size):
    payload= {
        "pagination": {
            "pageNumber": page_number,
            "pageSize":preferred_batch_size
        }
    }

    return session.post("/assets/api/v4/getAssets", json=payload)


def write_splunk_item(dic_rest, helper, ew, dragos_input_utils):
    helper.logger.info("Writing {0} events to Splunk".format(len(dic_rest["content"])))

    # Create a splunk event
    for item in dic_rest["content"]:
        obj_data = dragos_input_utils.format_individual_data_item_for_splunk(item)

        # asset data can be strange in that there can be actual legitimate address information
        # nested inside the array of address objects, but the shortcuts such as attribute.host.ip
        # or attributes.host.mac are empty
        #
        # if at any point we fail, log the error but then just revert back to the original data
        try:
            obj = json.loads(obj_data)

            # setup on the extracted/normalized ip, dns, mac and nt_host fields
            # based off the (potential) values contained in the attributes object
            if "attributes" in obj:

                if "host.ip" in obj["attributes"] and len(obj["attributes"]["host.ip"]) > 0:
                    append_or_create(obj, "ip", obj["attributes"]["host.ip"])

                if "host.mac" in obj["attributes"] and len(obj["attributes"]["host.mac"]) > 0:
                    append_or_create(obj, "mac", obj["attributes"]["host.mac"])

                if "host.hostname" in obj["attributes"] and len(obj["attributes"]["host.hostname"]) > 0:
                    append_or_create(obj, "nt_host", obj["attributes"]["host.hostname"])
            
            # search through the addresses to see if there is any additional address related information
            # that we can extract
            if "addresses" in obj:
                for addr in obj["addresses"]:
                    if "type" in addr and "value" in addr:
                        if addr["type"] == "IP":
                            append_or_create(obj, "ip", addr["value"])
                        elif addr["type"] == "DOMAIN":
                            append_or_create(obj, "dns", addr["value"])
                        elif addr["type"] == "MAC":
                            append_or_create(obj, "mac", addr["value"])
                        elif addr["type"] == "HOSTNAME":
                            append_or_create(obj, "nt_host", addr["value"])

            obj_data = json.dumps(obj)
        except Exception as e:
            # log the error but then just revert back to the original data
            # don't let the error propagate up
            msg = "Error ocurred while processing additional event fields. {0}".format(repr(e))
            helper.logger.error(msg)

            obj_data = dragos_input_utils.format_individual_data_item_for_splunk(item)
        

        event = dragos_input_utils.new_event_for_slunk(helper, obj_data)
        ew.write_event(event)
    
    return dic_rest["totalPages"]

def append_or_create(obj, field, value):
    normalized_value = value
    if type(value) == str:
        normalized_value = [value]

    for v in normalized_value:
        if not field in obj:
            obj[field] = v
        elif type(obj[field]) == str:
            obj[field] = [obj[field], v]
        elif type(obj[field]) == list:
            obj[field].append(v)
        else:
            obj[field] = v

    if type(obj[field]) == list:
        obj[field] = list(set(obj[field]))
        if len(obj[field]) == 0:
            obj.pop(field, None) 
        if len(obj[field]) == 1:
            obj[field] = obj[field][0]


def validate_input(helper, definition):
    # We don't have access to the credentials the user has selected so there is minimal
    # validation that we can do. Just do some basics to make sure everything looks
    # broadly OK
    dragos_platform_input_utils.PlatformInputUtils().validate_certificate_filename_and_existence(
        definition.parameters,
        helper.logger
    )


def collect_events(helper, ew):
    dragos_platform_input_utils.PlatformInputUtils().collect_events_from_api(helper, ew, submit_request_to_platform_api, write_splunk_item)