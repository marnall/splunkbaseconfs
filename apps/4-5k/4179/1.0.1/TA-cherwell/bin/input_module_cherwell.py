
# encoding = utf-8

# Python imports
import datetime
import json

# Local imports
from rest_api import RestApiService


def validate_input(helper, definition):
    """ This method validates the input parameters provided by the user while creating the input and provides
    appropriate error in case the validation fails.

    :param helper: Object of BaseModInput class
    :param definition: Object containing input parameters
    """

    # Validate interval provided by user
    # interval = definition.parameters.get('interval')

    # try:
    #    interval = int(interval)
    #    if interval < 0:
    #        raise Exception
    # except:
    #   raise Exception("Please provide positive integer value for interval")

    # Validate the date provided by the user
    since_value = definition.parameters.get("since_value")
    try:
        if since_value:
            datetime.datetime.strptime(since_value, r"%m/%d/%Y %I:%M:%S %p")
    except Exception as e:
        raise Exception("Please provide a valid date and in appropriate format, %s" %str(e))


def is_true(val):
    """ This method is used to derive the boolean value of the input provided by the user for cert validation.

    :param val: Input provided by the user
    :return:
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False
    

def collect_events(helper, ew):
    """ This method implements the core logic to collect records from Cherwell instance and index them in Splunk.

    :param helper: Object of BaseModInput class
    :param ew: Object of EventWriter class
    """

    current_utc_time = datetime.datetime.utcnow()
    # Get input stanza, it will be a list of dictionary ex: [{"stanza_name": {<dict containing stanza attributes>}}]
    stanza = helper.get_input_stanza()
    # Get stanza name
    stanza_name = stanza.keys()[0]
    # Get stanza attributes
    stanza = stanza.values()[0]
    # Get the account configured in the input
    cherwell_account = stanza.get('cherwell_account')

    # Get value for proxy based on whether the proxy is configured or not
    proxy = True if helper.get_proxy() else False
    # Get value of ssl_verify based on the value selected by the user
    ssl_verify = is_true(cherwell_account.get("ssl_verify"))

    # Create REST connection using the account details
    rest_api = RestApiService(cherwell_account.get("url_scheme") + "://" + cherwell_account.get("ipaddress"),
                              cherwell_account.get("username"), cherwell_account.get("password"),
                              cherwell_account.get("clientid"), helper, proxy, ssl_verify)

    # Get checkpoint if present
    checkpoint = helper.get_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"])) or dict()

    # Get UTC Offset
    last_time_offset = checkpoint.get('last_time_offset')
    if not last_time_offset:
        service_info = rest_api.get_service_info()
        last_time_offset = service_info.get("timeZone", {}).get("BaseUtcOffset","00:00:00")
        checkpoint['last_time_offset'] = last_time_offset
        helper.save_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"]), checkpoint)

    last_time_offset = [each_param for each_param in last_time_offset.split(':')]
    current_time = current_utc_time + datetime.timedelta(hours=int(last_time_offset[0]),
                                                         minutes=int(last_time_offset[1]),
                                                         seconds=int(last_time_offset[2]))

    # Get start time from checkpoint, if not found consider a default value
    start_time = checkpoint.get("last_time")
    if not start_time:
        start_time = stanza.get('since_value') or "01/01/2017 12:00:00 AM"
    
    # Get business object id
    object_id = checkpoint.get("object_id")
    # Get business object name
    object_name = checkpoint.get("object_name")
    # Fetch business object id and name if not found
    if not object_id or not object_name:
        bus_object = rest_api.get_object_name_id(stanza.get('business_object'))
        object_id = bus_object.get("busObId")
        object_name = bus_object.get("name")
        checkpoint["object_name"] = bus_object.get("name")
        checkpoint["object_id"] = bus_object.get("busObId")
        # Save business object id and name in checkpoint
        helper.save_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"]), checkpoint)

    # Get field id
    field_id = checkpoint.get("field_id")
    # Fetch field id if not found
    if not field_id:
        # For Change Request and Customer business objects the field name that contains last modified time of
        # record is "LastModDateTime" and for others it is "LastModifiedDateTime"
        for field_name in ("LastModifiedDateTime", "LastModDateTime"):
            try:
                field_id = rest_api.get_field_id(object_id, field_name) 
                break
            except ValueError:
                pass
        else:
            field_id = None
        # Save field id in checkpoint
        checkpoint["field_id"] = field_id
        helper.save_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"]), checkpoint)

    # Parameter to get values in ascending order and include all fields
    parameters = {
            "busObId": object_id,
            "sorting": [rest_api.sort_scheme(field_id, descending=False)],
            "includeAllFields": True,
            "filters": [rest_api.filter_scheme(field_id, 'gt', start_time)]
    }

    page_number = 1
    last_time = None
    count = 0

    # Pagination logic
    try:
        while True: 
            helper.log_debug("[Cherwell][%s] get object list page=%d, start_time=%s" %
                             (stanza_name, page_number, start_time))

            # Get list of objects from rest api
            object_list = rest_api.get_results(pageNumber=page_number, **parameters)
            # Break if no objects are found in the given PageNumber
            if not object_list:
                break

            for each_object in object_list:
                # Parse the object
                each_object.update({each_field["name"]: each_field["value"] for each_field in each_object["fields"]})
                if each_object.get("LastModifiedDateTime"):
                    each_object["LastModifiedDateTime"] = str(each_object["LastModifiedDateTime"]) + " " + \
                                                          str(last_time_offset[0]) + str(last_time_offset[1])
                # For Change Request and Customer business objects the field name that contains last modified time of
                # record is "LastModDateTime"
                elif each_object.get("LastModDateTime"):
                    each_object["LastModDateTime"] = str(each_object["LastModDateTime"]) + " " + \
                                                         str(last_time_offset[0]) + str(last_time_offset[1])
                del each_object["fields"]
                if "links" in each_object:
                    del each_object["links"]
                each_object["cherwell_instance"] = cherwell_account.get("ipaddress").strip('/')
                each_object["busObName"] = object_name
                # Index the event
                event = helper.new_event(json.dumps(each_object), index=stanza.get('index'),
                                         source="cherwell:%s" % stanza_name,
                                         sourcetype="cherwell:bo:%s" % object_name)
                ew.write_event(event)
  
            # Get last modified date for checkpoint
            if "LastModifiedDateTime" in object_list[-1]:
                last_time = object_list[-1]["LastModifiedDateTime"]
            # For Change Request and Customer business objects the field name that contains last modified time of
            # record is "LastModDateTime"
            elif "LastModDateTime" in object_list[-1]:
                last_time = object_list[-1]["LastModDateTime"]
            helper.log_debug("[Cherwell][%s] Number of object found=%d, Last_time = %s"
                             % (stanza_name, len(object_list), last_time))
            page_number += 1
            count += len(object_list)
    except:
        # Store latest time of object to the checkpoint
        if last_time:
            last_time = " ".join(last_time.split()[:-1])
            checkpoint["last_time"] = last_time
            helper.save_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"]), checkpoint)
            helper.log_debug("[Cherwell][%s] stored checkpoint:date: %s" % (stanza_name, last_time))
        helper.log_error("[Cherwell][%s] Error: Got only %d Objects from api." % (stanza_name, count))
        raise
    else:
        # If last_time is present convert into datetime object, compare it with current_time and store the larger of
        # the two. Reason being if the clock is one hour ahead due to daylight, applying the offset will give current
        # time that is one hour behind the actual time. So to avoid duplicates as much as possible store the larger
        # value by comparing latest modified time found in record with the current time.
        if last_time:
            last_time = " ".join(last_time.split()[:-1])
            last_time_dt_obj = datetime.datetime.strptime(last_time, "%m/%d/%Y %I:%M:%S %p")
            # Adding 1 second as the Cherwell REST API returns records with greater than or equal to the
            # specified datetime.
            last_time_dt_obj_one_sec_ahead = last_time_dt_obj + datetime.timedelta(seconds=1)

            if last_time_dt_obj_one_sec_ahead > current_time:
                latest_time = last_time_dt_obj_one_sec_ahead.strftime(r"%m/%d/%Y %I:%M:%S %p")
            else:
                # Store current time with timezone to the checkpoint
                latest_time = current_time.strftime(r"%m/%d/%Y %I:%M:%S %p")
        # If last_time is not found convert start_time into datetime object, compare it with current_time and store
        # the larger of the two.
        else:
            start_time_dt_obj = datetime.datetime.strptime(start_time, "%m/%d/%Y %I:%M:%S %p")

            if start_time_dt_obj > current_time:
                latest_time = start_time
            else:
                # Store current time with timezone to the checkpoint
                latest_time = current_time.strftime(r"%m/%d/%Y %I:%M:%S %p")

        checkpoint["last_time"] = latest_time
        helper.save_check_point(stanza_name + "-" + stanza.get('business_object') + "-" + str(cherwell_account["name"]), checkpoint)
        helper.log_debug("[Cherwell][%s] stored checkpoing:date: %s" % (stanza_name, latest_time))
        helper.log_info("[Cherwell][%s] Got %d Objects from api." % (stanza_name, count))