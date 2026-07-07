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

    return session.post("/vulnerabilities/api/v1/vulnerability/detection", json=payload)


def write_splunk_item(dic_rest, helper, ew, dragos_input_utils):
    helper.logger.info("Writing {0} events to Splunk".format(len(dic_rest["content"])))
    
    # Create a splunk event
    for item in dic_rest["content"]:
        obj_data = dragos_input_utils.format_individual_data_item_for_splunk(item)

        # try our best to identify the dest which according to Splunk CIM
        # is the host with the vulnberablity
        #
        # if at any point we fail, log the error but then just revert back to the original data
        try:
            obj = json.loads(obj_data)

            if "host" in obj:
                if "mac" in obj["host"] and len(obj["host"]["mac"]) > 0:
                    obj["dest"] = obj["host"]["mac"][0]
                elif "ip" in obj["host"] and len(obj["host"]["ip"]) > 0:
                    obj["dest"] = obj["host"]["ip"][0]
                elif "hostname" in obj["host"] and len(obj["host"]["hostname"]) > 0:
                    obj["dest"] = obj["host"]["hostname"][0]
                elif "name" in obj["host"]:
                    obj["dest"] = obj["host"]["name"]
                else:
                    obj["dest"] = "unknown"
            
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

    
def validate_input(helper, definition):
    # We don't have access to the credentials the user has selected so there is minimal
    # validation that we can do. Just do some basics to make sure everything looks
    # broadly OK
    dragos_platform_input_utils.PlatformInputUtils().validate_input_parameters(
        helper, definition.parameters
    )



def collect_events(helper, ew):
    dragos_platform_input_utils.PlatformInputUtils().collect_events_from_api(helper, ew, submit_request_to_platform_api, write_splunk_item)