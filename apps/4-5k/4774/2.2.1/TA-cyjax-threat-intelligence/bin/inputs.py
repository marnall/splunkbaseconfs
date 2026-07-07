# encoding = utf-8

from six.moves.urllib import parse as urllib_parse
from datetime import datetime, timedelta, timezone
import json
from tzlocal import get_localzone
import pytz
from services import ResponseErrorException
from proxy import get_proxies


def collect_entries_from_endpoint(helper, ew, endpoint_klass, *args, **kwargs):
    opt_api_key = helper.get_arg('api_key')
    if not opt_api_key:
        helper.log_error("Invalid API key")
        return

    opt_interval = helper.get_arg('interval')
    helper.log_info("Using %s as interval" % opt_interval)
    since_store_key = f"since_{endpoint_klass.__name__}"
    helper.log_info(f"using key: {since_store_key}")

    if helper.get_check_point(since_store_key):
        since_string = helper.get_check_point(since_store_key)
        # Convert ISO format string to datetime object
        since_object = datetime.fromisoformat(since_string)
        since = since_object.isoformat()

        helper.log_info("Fetching data from %s" % since)
    else:
        utc_now = datetime.now(timezone.utc) - timedelta(seconds=int(86400))
        since = utc_now.astimezone(get_localzone()).replace(
            microsecond=0).isoformat()
        helper.log_info(
            "Fetching data for the first time. Starting from %s" % since)
    utc_now = datetime.now(timezone.utc)
    until = utc_now.astimezone(get_localzone()).replace(
        microsecond=0).isoformat()

    helper.save_check_point(since_store_key, until)
    helper.log_info("Saving check point %s" % until)

    endpoint = endpoint_klass(api_key=opt_api_key, proxies=get_proxies(helper))
    try:
        helper.log_info("Fetching %s..." % endpoint.get_name())
        page = 1
        has_next = True
        while has_next:
            helper.log_info("URL=%s since=%s, until=%s" %
                            (endpoint.BASE_URI, since, until))
            helper.log_info("Processing page %d..." % page)
            response = endpoint.get_entries(
                since=since, until=until, page=page, per_page=50, *args, **kwargs)
            helper.log_info("Found %d results..." % len(response.json()))
            for entry in response.json():
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                         sourcetype=helper.get_sourcetype(), data=json.dumps(entry))
                ew.write_event(event)

            if page < 20 and 'next' in response.links:
                parsed = urllib_parse.urlparse(response.links['next']['url'])
                page = int(urllib_parse.parse_qs(parsed.query)['page'][0])
            else:
                has_next = False
    except ResponseErrorException as e:
        helper.log_error("Error fetching data for endpoint %s: %s" %
                         (endpoint.get_name(), e))
    helper.log_info("Terminated")
