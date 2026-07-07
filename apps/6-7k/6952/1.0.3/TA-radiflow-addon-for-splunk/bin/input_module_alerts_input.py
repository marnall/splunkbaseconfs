
# encoding = utf-8

import os
import sys
import time
from datetime import datetime,timedelta
from radiflow_rest_client import get_all_alerts, set_last_polled_timestamp,get_last_polled_timestamp
import json
from dateutil.parser import isoparse
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


_APP_NAME = 'RadiFlowAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # radiflow_account = definition.parameters.get('radiflow_account', None)
    pass

def collect_events(helper, ew):
    try:
        source = helper.get_arg('name')
        site_id = helper.get_arg("site_id")
        opt_historical_polling_days = int(helper.get_arg("historical_polling_days"))
        earliest = get_last_polled_timestamp(log_location, source)
        calculatedAfter = earliest[:-3] + 'Z' if earliest else False
        now = datetime.utcnow()
        sourcetype = "Radiflow:Alerts"
        total_alerts = 0
        if calculatedAfter:
            calculatedAfter = isoparse(calculatedAfter).timestamp()
            helper.log_info(f'This is calculated after for incremental polling {calculatedAfter}')
        else:
            earliest = (now - timedelta(days=opt_historical_polling_days)).isoformat()
            calculatedAfter = earliest[:-3] + 'Z' if earliest else False
            calculatedAfter = isoparse(calculatedAfter).timestamp()
        all_opened_alerts = get_all_alerts(helper,calculatedAfter)
        helper.log_info("Total alerts recevice : ")
        helper.log_info(all_opened_alerts)
        for alert in all_opened_alerts:
            alert.update({"site_id":site_id})
            alert_new = json.dumps(alert)
            event = helper.new_event(source=source, index=helper.get_output_index(), sourcetype=sourcetype, data=alert_new)
            ew.write_event(event)
            total_alerts += 1
        helper.log_info(f'The total number of alerts parsed {total_alerts}')
        if total_alerts > 0:
            set_last_polled_timestamp(log_location, source, datetime.isoformat(now))
    except Exception as e:
        sourcetype = "RadiFlowAddonForSplunk:error"
        data = str(e)
        input_type = helper.get_arg('name')
        event = helper.new_event(source=input_type, index=helper.get_output_index(), sourcetype=sourcetype, data=data)
        ew.write_event(event)
