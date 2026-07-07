# encoding = utf-8


from datetime import datetime
import pytz
import iso8601
from collections import OrderedDict

UNIX_EPOCH_ISO_8601 = "1970-01-01T00:00:00Z"

TIMESTAMP_BOOKMARK_NAME = "timestamp"

from dragoslib import platform_input_utils as dragos_platform_input_utils
from dragoslib import app_config as dragos_app_config

def submit_request_to_platform_api(session, page_number, preferred_batch_size, **kwargs):

    earliest = datetime.fromtimestamp(kwargs['unix_timestamp_checkpoint'] - kwargs['backward_shift_seconds'], pytz.utc).isoformat()
    now      = datetime.fromtimestamp(kwargs['unix_timestamp_now']        - kwargs['backward_shift_seconds'], pytz.utc).isoformat()

    query_createdFilter  = "createdAt=gt='{0}';createdAt=le='{1}'".format(earliest, now)

    params = {
        "pageNumber": page_number,
        "pageSize": preferred_batch_size,
        "sorts": "createdAt:a",
        "filter": "type!='Baseline';({0});type!='System'".format(query_createdFilter)
    }

    return session.get("/notifications/api/v2/notification", params=params)
    

def write_splunk_item(dic_rest, helper, ew, dragos_input_utils):
    helper.logger.info("Writing {0} events to Splunk".format(len(dic_rest["content"])))
    
    # Create a splunk event
    for item in dic_rest["content"]:
        # The source and dest ips are hard to parse out of the default notification
        # data. As such we add additional fields to make these key fields easier to use
        # Since these are additional fields, if we hit any parsing errors then simply continue
        # on. The error should not be fatal
        source_ips = []
        source_macs = []
        dest_ips = []
        dest_macs = []
        source_hostnames = []
        dest_hostnames = []
        source_domains = []
        dest_domains = []
        try:
            for asset in item["assets"]:
                ips  = [addr["value"] for addr in asset["addresses"] if addr["type"] == "IP"]
                macs = [addr["value"] for addr in asset["addresses"] if addr["type"] == "MAC"]
                hostnames = [addr["value"] for addr in asset["addresses"] if addr["type"] == "HOSTNAME"]
                domains = [addr["value"] for addr in asset["addresses"] if addr["type"] == "DOMAIN"]
                if asset["directionalities"] == ["source"]:
                    source_ips += ips
                    source_macs += macs
                    source_hostnames += hostnames
                    source_domains += domains
                elif asset["directionalities"] == ["destination"]:
                    dest_ips += ips
                    dest_macs += macs
                    dest_hostnames += hostnames
                    dest_domains += domains
        except Exception:
            pass

        item["source_ips"] = source_ips
        item["destination_ips"] = dest_ips
        item["source_macs"] = source_macs
        item["destination_macs"] = dest_macs
        item["source_hostnames"] = source_hostnames
        item["destination_hostnames"] = dest_hostnames
        item["source_domains"] = source_domains
        item["destination_domains"] = dest_domains

        # We need to verify that each item has a createdAt
        # field that is a valid, parsable ISO 8601 formattedtimestamp
        # If there are any issues fallback to the current time
        if "createdAt" not in item:
            item["createdAt"] = datetime.now(iso8601.iso8601.UTC).isoformat()
        else:
            try:
                iso8601.parse_date(item["createdAt"])
            except iso8601.iso8601.ParseError:
                item["createdAt"] = datetime.now(iso8601.iso8601.UTC).isoformat()

        # Dragos notifications have a source field that collides with Splunk's
        # internal source field. To avoid any issues we rename the source field
        if "source" in item:
            item["dragos_source"] = item.pop("source")
        
        # At this point we have a data item that has a valid iso8601 timestamp
        # in the createdAt field.
        #
        # Now I want to modify the dict ordering to ensure the createdAd field
        # is at the beginning. This is for two reasons:
        # 1) There are multiple copies of the createdAt timestamp all over the
        #    notification. For example assets referred in the notification also
        #    contain a createdAt field which can potentially cause splunk to pull
        #    the incorrect instance of the createdAt field
        # 2) Its expensive for splunk to search the event for the timestamp in
        #    the createdAt field and its possible it will give up for performance
        #    reasons before it can find the createdAt field
        #
        # Also need to be careful here as the OrderedDict methods have changed between Python2
        # and Python3, so while this isn't be prettiest looking it does work in both versions
        # of python
        top_field_names = ['createdAt', 'type', 'severity', 'summary', 'name']
        top_fields = OrderedDict()
        ordered_item = OrderedDict(item)
        for field in top_field_names:
            if field in ordered_item:
                top_fields[field] = ordered_item.pop(field)

        ordered_item = OrderedDict(list(top_fields.items()) + list(ordered_item.items()))
        obj_data = dragos_input_utils.format_individual_data_item_for_splunk(ordered_item)

        event = dragos_input_utils.new_event_for_slunk(helper, obj_data)
        ew.write_event(event)

    # After each page of notifications is output to Splunk, the data checkpoint timestamp
    # should be set to one second before the created time of last notification in the page.
    if len(dic_rest["content"]) > 0:
        latest_createdat_datetime = dragos_platform_input_utils.PlatformInputUtils.datetime_to_unix_timestamp(iso8601.parse_date(dic_rest["content"][-1]["createdAt"]))
        latest_createdat_datetime -= 1

        token_name = get_bookmark_name(helper, TIMESTAMP_BOOKMARK_NAME)
        helper.logger.info("Saving notifications timestamp bookmark after writing page to splunk")
        helper.save_check_point(token_name, latest_createdat_datetime)

    return dic_rest["totalPages"]

def get_bookmark_name(helper, bookmark_name):
    return "{0}-{1}-{2}".format(helper.get_input_type(), list(helper.get_input_stanza().keys())[0], bookmark_name)

def validate_input(helper, definition):
    # We don't have access to the credentials the user has selected so there is minimal
    # validation that we can do. Just do some basics to make sure everything looks
    # broadly OK
    dragos_platform_input_utils.PlatformInputUtils().validate_input_parameters(
        helper, definition.parameters
    )

    # Additional validation for the optional timestamp_bookmark field if specified
    timestamp_bookmark = definition.parameters.get('timestamp_bookmark', None)
    if timestamp_bookmark:
        try:
            input_date = iso8601.parse_date(timestamp_bookmark)
            helper.logger.info("Timestamp bookmark date raw={0}    parsed={1}".format(timestamp_bookmark, input_date))

            unix_epoch = iso8601.parse_date(UNIX_EPOCH_ISO_8601)
            if input_date < unix_epoch:
                message = "Date string {0} resulted in timestamp of {1}. Please verify its a valid ISO 8601 date string and is after 1970-01-01T00:00:00Z".format(timestamp_bookmark, input_date)
                helper.logger.error(message)
                raise ValueError(message)
        except iso8601.iso8601.ParseError as e:
            message = "Unable to parse date string '{0}'. Please verify it is ISO 8601 compliant or leave blank.".format(timestamp_bookmark)
            helper.logger.error(message)
            raise ValueError(message)
    else:
        helper.logger.info("timetamp_bookmark field not specified")

    helper.logger.info("Notifications specific parameters validated")   


def collect_events(helper, ew):
    # Setup a session with the platform and do standard initialization for inputs
    input_utils = dragos_platform_input_utils.PlatformInputUtils()
    session = input_utils.collect_events_initialization(helper)

    # Additional processing to determine timestamp if first run or retrieve the checkpoint
    # if its the nth run
    helper.logger.info("Processing notifications timestamp bookmark")
    user_supplied_timestamp = helper.get_arg("timestamp_bookmark")
    token_name = get_bookmark_name(helper, TIMESTAMP_BOOKMARK_NAME)
    helper.logger.debug(f'Looking up timestamp with key "{token_name}"')
    unix_timestamp_checkpoint = helper.get_check_point(token_name)
    if unix_timestamp_checkpoint:
        helper.logger.info("Got existing timestamp checkpoint")
    else:
        unix_timestamp_checkpoint = input_utils.datetime_to_unix_timestamp(user_supplied_timestamp)  #use default value specified when input was created
        helper.logger.info("No existing timestamp checkpoint")
    helper.logger.info("Timestamp checkpoint {0} ({1})".format(unix_timestamp_checkpoint, datetime.fromtimestamp(unix_timestamp_checkpoint, pytz.utc).isoformat()))

    unix_timestamp_now = input_utils.datetime_to_unix_timestamp(datetime.now(pytz.utc))

    api_context = {
        "unix_timestamp_checkpoint": unix_timestamp_checkpoint,
        "unix_timestamp_now": unix_timestamp_now,
        # A the recommendation of the API owner we should adjust our query to allow for some processing to avoid
        # missing notifications on the boundary that simply haven't been processed yet
        "backward_shift_seconds": int(dragos_app_config.AppConfig().dragos_worldview_notification_query_backward_shift_seconds())
    }
    input_utils.collect_events_from_api(helper, ew, submit_request_to_platform_api, write_splunk_item, session=session, api_context=api_context)
            
    #save timestamp so that on the next run we only pickup new notifications
    helper.logger.info("Saving notifications timestamp bookmark")
    helper.save_check_point(token_name, unix_timestamp_now)

