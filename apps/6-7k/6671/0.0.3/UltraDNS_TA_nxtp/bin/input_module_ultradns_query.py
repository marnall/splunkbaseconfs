# encoding = utf-8

import datetime as dt
import json
from ultradns_ta_nxtp.ultradns import Request, ManagementConnection

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # lookbackdays = definition.parameters.get('lookbackdays', None)


def collect_events(helper, ew):
    # For troubleshooting uncomment the following line
    # helper.save_check_point("ultraDNSTimestamp", dt.datetime.now().timestamp() - 86500)

    lastTimeExecuted = helper.get_check_point("ultraDNSTimestamp")
    mgmtConnection = ManagementConnection(helper)
    now = dt.datetime.now()
    tokenExpirayDate = dt.datetime.now().timestamp()
    # Wird beim ersten Mal ausführen ausgeführt
    if lastTimeExecuted is None:
        for i in range(1, int(helper.get_arg("lookbackdays")) + 1):
            if dt.datetime.now().timestamp() - 3500 > tokenExpirayDate:
                helper.log_debug(
                    f"Token will expire within 100 Seconds, requesting new Token from the API"
                )
                mgmtConnection = ManagementConnection(helper)
                tokenExpirayDate = dt.datetime.now().timestamp()
            queryTime = now - dt.timedelta(days=i)
            formattedQueryTime = queryTime.strftime("%Y-%m-%d")
            data = Request(mgmtConnection, "/reports/dns_resolution/query_volume/zone?advance=true", formattedQueryTime,
                           formattedQueryTime).execute()
            for event in data:
                if data is None:
                    continue
                event["startDate"] = formattedQueryTime
                event["endDate"] = formattedQueryTime
                ew.write_event(
                    helper.new_event(
                        json.dumps(event),
                    )
                )
        # This line looks really weird, but it's to have the timestamp always be the exact time and just with different date
        helper.save_check_point("ultraDNSTimestamp", dt.datetime.strptime(now.strftime("%Y-%m-%d"), "%Y-%m-%d").timestamp() + 14400)
    # Wenn der letzte Timestamp schon über einen Tag her ist
    elif now.timestamp() - 86400 > lastTimeExecuted:
        queryTime = dt.datetime.fromtimestamp(lastTimeExecuted)
        formattedQueryTime = queryTime.strftime("%Y-%m-%d")
        data = Request(mgmtConnection, "/reports/dns_resolution/query_volume/zone?advance=true", formattedQueryTime,
                       formattedQueryTime).execute()
        for event in data:
            if data is None:
                continue
            event["startDate"] = formattedQueryTime
            event["endDate"] = formattedQueryTime
            ew.write_event(
                helper.new_event(
                    json.dumps(event),
                )
            )
        # This line looks really weird, but it's to have the timestamp always be the exact time and just with different date
        helper.save_check_point("ultraDNSTimestamp", dt.datetime.strptime(now.strftime("%Y-%m-%d"), "%Y-%m-%d").timestamp() + 14400)
