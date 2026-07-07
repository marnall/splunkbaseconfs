# python imports
import datetime
import calendar
import traceback
from urllib.parse import urlparse
from urllib.parse import parse_qs

# custom imports
import splunk.rest as rest
from flashpoint import FlashPoint
from utils import get_checkpoint, format_proxy_uri, write_events
from config import POLL_OFFSET, POLL_OFFSET_FOR_CVE, POLL_OFFSET_INDICATORS

EVENT_TYPES = ["reports", "indicators", "cve", "mentions", "compromised_credentials", "ransomware", "alerts"]


def validate_input(helper, definition):
    """Validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here.

    :param helper: helper object
    :param ew: event writer object
    """
    event_type = helper.get_arg('type')
    input_name = helper.get_input_stanza_names()
    if get_checkpoint(helper, input_name) != helper.get_arg('start_date'):
        if event_type == "cve" and datetime.datetime.utcnow().hour != 20:
            helper.log_info(
                "Exiting input for type CVE as hour in UTC time is not 8 PM")
            exit(1)

    if event_type not in EVENT_TYPES:
        helper.log_error(
            "Invalid event type. Please select any type out of {}".format(", ".join(EVENT_TYPES)))
        exit(1)

    if event_type == "cve":
        # Adding a buffer window of 44 hours for cve.
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d") + "T20:00:00"
        now = calendar.timegm(datetime.datetime.strptime(now, "%Y-%m-%dT%H:%M:%S").timetuple()) - POLL_OFFSET_FOR_CVE  # noqa:E501
    elif event_type in ["compromised_credentials", "ransomware", "alerts"]:
        # No buffer window
        now = calendar.timegm(datetime.datetime.utcnow().timetuple())
    elif event_type == "indicators":
        # Adding a buffer window of 90 minutes
        now = calendar.timegm(datetime.datetime.utcnow().timetuple()) - POLL_OFFSET_INDICATORS
    else:
        # Adding a buffer window of 30 minutes
        now = calendar.timegm(datetime.datetime.utcnow().timetuple()) - POLL_OFFSET
    helper.log_info("Process started at {}".format(datetime.datetime.now()))

    ret_value = iterate_and_index(helper, ew, event_type, now)
    if ret_value == 1:
        exit(1)

    helper.log_info("Process finished at {}.".format(datetime.datetime.now()))


def data_colleciton_using_link(helper, fp, event_type, now, ew, checkpoint_name):
    """Function to collect and write data using next link."""
    next_link = True
    formatted_events_len = 0
    until = str(datetime.datetime.utcfromtimestamp(now)).replace(' ', 'T')

    while next_link:
        request_param = fp.get_request_param()
        request_param['created_before'] = until + 'Z'
        fp.set_request_param(request_param)
        try:
            fp.get_events()
            next_link, formatted_events = fp.get_formatted_events()
            formatted_events_len += len(formatted_events)
            write_events(helper, ew, formatted_events, event_type)
            if next_link:
                parsed_url = urlparse(next_link)
                request_param['cursor'] = parse_qs(parsed_url.query).get('cursor')[0]
                fp.set_request_param(request_param)
        except Exception as e:
            helper.log_error(
                "There was an error in fetching and writing events for {} in range {} to {}.\n Error: {}".format(
                    event_type, request_param['created_after'], request_param['created_before'], str(e)
                )
            )
            helper.log_info("Saving checkpoint to {}".format(str(request_param['created_after'])[:-1]))
            helper.save_check_point(checkpoint_name, str(request_param['created_after'])[:-1])
            return 1
    helper.log_info("Saving checkpoint to {}".format(until))
    helper.save_check_point(checkpoint_name, until)
    helper.log_info(
        "Fetching and writing events for {} completed. Total event collected: {}".format(
            event_type, formatted_events_len))


def indicator_data_collection(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time):
    """Function to collect and write data using generic method."""
    start_from = 0
    size = 1000
    formatted_events_len = 0
    request_param = fp.get_request_param()
    request_param['last_seen_before'] = str(datetime.datetime.utcfromtimestamp(now)).replace(' ', 'T')
    fp.set_request_param(request_param)

    while True:
        try:
            request_param['size'] = size
            request_param['from'] = start_from
            fp.set_request_param(request_param)
            fp.get_events()
            formatted_events = fp.get_formatted_events()
            formatted_events_len += len(formatted_events)
            write_events(helper, ew, formatted_events, event_type)
            helper.log_info("Collected {} events: {}".format(event_type, len(formatted_events)))
            if len(formatted_events) < size:
                break
            else:
                start_from += size
        except Exception as ex:
            res = getattr(getattr(ex, 'response', None), 'text', None)
            helper.log_error(
                (
                    "There was an error in fetching and writing events for {} from {} to {}."
                    "\n Response: {}\n Error: {}"
                ).format(
                    event_type,
                    request_param['last_seen_after'],
                    request_param['last_seen_before'],
                    res,
                    traceback.format_exc()
                )
            )
            return 1

    checkpoint = now
    checkpoint += 1     # Both API start & end time filter is inclusive
    checkpoint = str(datetime.datetime.utcfromtimestamp(checkpoint)).replace(' ', 'T')

    helper.log_info("Saving checkpoint: {}".format(checkpoint))
    helper.save_check_point(checkpoint_name, checkpoint)
    helper.log_info(
        "Fetching and writing events for {} completed. Total events collected: {}".format(
            event_type, formatted_events_len))


def data_collection_using_communities_search(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time):
    """Function to collect and write data using generic method."""
    events_count = 0
    until = str(datetime.datetime.utcfromtimestamp(now)).replace(' ', 'T')
    if event_type == "ransomware":
        request_body = {
            "include": {
                "type": ["ransomware"],
                "date": {"start": str(updated_since_time) + "Z", "end": until + "Z"},
            },
            "query": "",
            "size": 100,
        }
    else:
        request_body = {
            "include": {
                "enrichments": {"cve_ids": []},
                "date": {"start": str(updated_since_time) + "Z", "end": until + "Z"},
            },
            "query": "",
            "size": 100,
        }
    try:
        fp.set_json_param(request_body)
        first_page_data = fp.get_events(communities_call=True)
        events_count = events_count + len(first_page_data.get("items"))
        helper.log_info("Fetched {} events: {}".format(event_type, len(first_page_data.get("items"))))
        write_events(helper, ew, first_page_data.get("items"), event_type)

        number_of_results = first_page_data.get("total").get("value")
        size_per_page = first_page_data.get("size")
        number_of_pages = number_of_results // size_per_page if size_per_page else 0

        for page_num in range(1, number_of_pages + 1):
            request_body["page"] = page_num
            fp.set_json_param(request_body)
            page_data = fp.get_events(communities_call=True)
            events_count = events_count + len(page_data.get("items"))
            helper.log_info("Fetched {} events: {}".format(event_type, len(page_data.get("items"))))
            write_events(helper, ew, page_data.get("items"), event_type)

        checkpoint = now
        checkpoint += 1     # Both API start & end time filter is inclusive
        checkpoint = str(datetime.datetime.utcfromtimestamp(checkpoint)).replace(' ', 'T')

        helper.log_info("Saving checkpoint: {}".format(checkpoint))
        helper.save_check_point(checkpoint_name, checkpoint)
        helper.log_info(
            "Fetching and writing events for {} completed. Total events collected: {}".format(
                event_type, events_count))
    except Exception:
        helper.log_error(
            (
                "There was an error in fetching and writing events for {} from {} to {}.\nError: {}"
            ).format(
                event_type,
                updated_since_time,
                until,
                traceback.format_exc()
            )
        )
        return 1


def data_colleciton_using_search_scroll(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time):
    """Function to collect and write data using generic method."""
    scroll_id = True
    is_scroll = False
    formatted_events_len = 0
    last_scroll_id = None

    request_param = fp.get_request_param()
    request_param['updated_until'] = str(datetime.datetime.utcfromtimestamp(now)).replace(' ', 'T')
    fp.set_request_param(request_param)

    tmp_request_param = {'scroll': request_param.get('scroll')}
    tmp_json_param = {'scroll_id': None}

    while True:
        try:
            fp.get_events(is_scroll=is_scroll)
            scroll_id, formatted_events = fp.get_formatted_events()
            formatted_events_len += len(formatted_events)
            write_events(helper, ew, formatted_events, event_type)
            helper.log_info("Collected {} events: {}".format(event_type, len(formatted_events)))
            last_scroll_id = scroll_id or last_scroll_id
            if scroll_id and fp.fetched_event_count:
                # Valid scroll_id will be returned even if no events are returned
                is_scroll = True
                tmp_json_param['scroll_id'] = scroll_id
                fp.set_json_param(tmp_json_param)
                fp.set_request_param(tmp_request_param)
            else:
                break
        except Exception as ex:
            res = getattr(getattr(ex, 'response', None), 'text', None)
            helper.log_error(
                (
                    "There was an error in fetching and writing events for {} from {} to {}."
                    "\n Response: {}\n Error: {}"
                ).format(
                    event_type,
                    request_param['updated_since'],
                    request_param['updated_until'],
                    res,
                    traceback.format_exc()
                )
            )
            return 1

    if last_scroll_id:
        try:
            fp.delete_scroll_session(last_scroll_id)
            helper.log_debug('Scroll session deleted succesfully.')
        except Exception as ex:
            helper.log_warning(
                (
                    'Error occured while deleting the scroll session '
                    '(By default, it will be deleted in few minutes by server): error={}'
                ).format(ex))

    checkpoint = now
    checkpoint += 1     # Both API start & end time filter is inclusive
    checkpoint = str(datetime.datetime.utcfromtimestamp(checkpoint)).replace(' ', 'T')

    helper.log_info("Saving checkpoint: {}".format(checkpoint))
    helper.save_check_point(checkpoint_name, checkpoint)
    helper.log_info(
        "Fetching and writing events for {} completed. Total events collected: {}".format(
            event_type, formatted_events_len))


def cve_data_collection(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time):
    """Function to collect and write data using generic method."""
    try:
        events_count = 0
        while updated_since_time < now:
            request_param = fp.get_request_param()
            request_param["from"] = 0
            request_param['size'] = 100
            # Add next 10 days in updated since time
            next_10_days = updated_since_time + 864000
            if next_10_days > now:
                next_10_days = now
            request_param['updated_before'] = str(
                datetime.datetime.utcfromtimestamp(next_10_days)).replace(' ', 'T') + 'Z'
            fp.set_request_param(request_param)
            next_link = True
            from_value = 0
            size = 100
            while next_link:
                result = fp.get_events()
                events_count = events_count + len(result.get("results"))
                helper.log_info("Fetched {} events: {}".format(event_type, len(result.get("results"))))
                write_events(helper, ew, result.get("results"), event_type)
                next_link = result.get("next")
                from_value = from_value + size
                request_param["from"] = from_value
                fp.set_request_param(request_param)
            epoch_updated_before = request_param['updated_before'].rstrip(request_param['updated_before'][-1])
            epoch_updated_before = calendar.timegm(
                (datetime.datetime.strptime(epoch_updated_before, '%Y-%m-%dT%H:%M:%S')).timetuple())
            epoch_updated_before = epoch_updated_before + 1
            request_param['updated_after'] = str(
                datetime.datetime.utcfromtimestamp(epoch_updated_before)).replace(' ', 'T') + 'Z'
            fp.set_request_param(request_param)
            updated_since_time = epoch_updated_before
        checkpoint = now
        checkpoint = checkpoint + 1     # Both API start & end time filter is inclusive
        helper.save_check_point(checkpoint_name, str(
            datetime.datetime.utcfromtimestamp(checkpoint)).replace(' ', 'T'))
        helper.log_info(
            "Fetching and writing events for {} completed. Total events collected: {}"
            .format(event_type, events_count))

    except Exception as e:
        helper.log_error(
            "There was an error in fetching and writing events for {} in range {} to {}.\n Error: {}".format(
                event_type, request_param['updated_after'], request_param['updated_before'], str(e)
            )
        )
        helper.log_info("Saving checkpoint to {}".format(
            str(request_param['updated_after'])[:-1]))
        helper.save_check_point(checkpoint_name, str(
            request_param['updated_after'])[:-1])
        return 1


def data_colleciton_using_generic(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time):
    """Function to collect and write data using generic method."""
    while updated_since_time < now:
        request_param = fp.get_request_param()
        request_param['skip'] = 0

        # Add next 10 days in updated since time
        next_10_days = updated_since_time + 864000
        if next_10_days > now:
            next_10_days = now
        request_param['updated_until'] = str(
            datetime.datetime.utcfromtimestamp(next_10_days)).replace(' ', 'T')
        fp.set_request_param(request_param)
        formatted_events_len = 1
        while formatted_events_len != 0 and (request_param['skip'] + request_param['limit']) <= 10000:
            try:
                fp.get_events()
                formatted_events = fp.get_formatted_events()
                formatted_events_len = len(formatted_events)
                write_events(helper, ew, formatted_events, event_type)
                helper.log_info("Collected {} events: {}".format(event_type, formatted_events_len))
            except Exception as e:
                helper.log_error(
                    "There was an error in fetching and writing events for {} in range {} to {}.\n Error: {}".format(
                        event_type, request_param['updated_since'], request_param['updated_until'], str(e)
                    )
                )
                helper.log_info("Saving checkpoint to {}".format(
                    request_param['updated_since']))
                helper.save_check_point(checkpoint_name, str(
                    request_param['updated_since']))
                return 1

            request_param['skip'] += request_param['limit']
            fp.set_request_param(request_param)
        request_param['updated_since'] = request_param['updated_until']
        fp.set_request_param(request_param)
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(request_param['updated_since'], '%Y-%m-%dT%H:%M:%S')).timetuple())
    # Update updated_since value in check point
    helper.save_check_point(checkpoint_name, str(
        datetime.datetime.utcfromtimestamp(now)).replace(' ', 'T'))
    helper.log_info(
        "Fetching and writing events for {} completed.".format(event_type))


def iterate_and_index(helper, ew, event_type, now):
    """Function to iterate over event_types and index data.

    Returns 1 if any error occurs in data fetching or indexing
    :param helper: helper object
    :param ew: event writer object
    :param event_type: str, type of event to fetch and index
    :param now: Time when process started
    """
    input_name = helper.get_input_stanza_names()
    helper.log_info("Input {} started".format(input_name))
    checkpoint_name = input_name
    updated_since = get_checkpoint(helper, checkpoint_name)

    try:
        opt_global_account = helper.get_arg('global_account')
        api_key = opt_global_account.get("api_key").replace('Bearer ', '')
    except AttributeError:
        session_key = helper.context_meta['session_key']
        message = 'Found an unsupported input "{}" from the older version of Flashpoint. '\
            'Please recreate this input with the new configurations to continue fetching data.'.format(input_name)
        data = {'name': 'Error in Flashpoint input ' + input_name, 'value': message, 'severity': 'error'}
        rest.simpleRequest("/services/messages", sessionKey=session_key, method='POST', postargs=data)
        helper.log_error(message)
        exit(1)

    proxy_dict = helper.get_proxy()
    proxy_uri = None
    if proxy_dict:
        proxy_uri = format_proxy_uri(proxy_dict)

    helper.log_info("Writing events for type: {}".format(event_type))

    if event_type in ["alerts"]:
        helper.log_info("Checkpoint time: {}".format(updated_since))
        updated_since += 'Z'
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        data_colleciton_using_link(helper, fp, event_type, now, ew, checkpoint_name)

    elif event_type in ["ransomware", "mentions"]:
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())
        helper.log_info("Updated since is {}".format(updated_since))
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        data_collection_using_communities_search(helper, fp, event_type, now, ew, checkpoint_name, updated_since)

    elif event_type in ["compromised_credentials"]:
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())
        helper.log_info("Updated since is {}".format(updated_since))
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        data_colleciton_using_search_scroll(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time)

    elif event_type in ["indicators"]:
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())
        helper.log_info("Updated since is {}".format(updated_since))
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        # data_colleciton_using_indicator_scroll(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time)
        indicator_data_collection(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time)

    elif event_type in ["cve"]:
        if updated_since[-1] == 'Z':
            updated_since = updated_since[:-1]
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        cve_data_collection(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time)

    else:
        # Generic data collection
        updated_since_time = calendar.timegm(
            (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())
        helper.log_info("Updated since is {}".format(updated_since))
        fp = FlashPoint(api_key=api_key, proxy_uri=proxy_uri,
                        event_type=event_type, helper=helper, updated_since=updated_since)
        data_colleciton_using_generic(helper, fp, event_type, now, ew, checkpoint_name, updated_since_time)
