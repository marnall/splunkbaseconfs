import logging
import json
import requests
from datetime import datetime, timezone, timedelta

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    """
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """
    data_input_name = helper.get_arg("name")
    data_input_index = helper.get_arg("index")
    project_id = helper.get_arg("project_id")
    authentication_account = helper.get_arg("authentication_account")
    api_token = authentication_account["password"]
    qualibooth_api_host = helper.get_arg("qualibooth_api_host")
    qualibooth_api_endpoint = helper.get_arg("qualibooth_api_endpoint")
    count = 10000

    
    checkpoint = helper.get_check_point(data_input_name) or {}
    last_executed = checkpoint.get("last_executed")
    logging.info(f"Last executed: {last_executed}")
    headers = {"Authorization": f"Bearer {api_token}"}
    today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    to_datetime = today_midnight.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    from_datetime = (today_midnight - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    if last_executed is not None:
        last_executed_unix = datetime.fromisoformat(last_executed.replace("Z", "+00:00")).timestamp()        
        
        if last_executed_unix == today_midnight.timestamp():
            logging.warning("Data already collected for today, skipping.")
            return
        elif last_executed_unix < today_midnight.timestamp():
            to_datetime = today_midnight.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            from_datetime = (today_midnight - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
    try:
        qualibooth_api_daily_report_url = f"{qualibooth_api_host}{qualibooth_api_endpoint}/{project_id}/list/period/{from_datetime}/{to_datetime}"
        response = requests.get(qualibooth_api_daily_report_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.InvalidSchema as schema_error:
        logging.error(f'Invalid url: {str(schema_error)}')
        return None
    except requests.HTTPError as http_error:
        if response.status_code == 401:
            logging.error("Unauthorized - check API token")
            return None
        elif response.status_code == 500:
            logging.error(f"Server error - {str(http_error)}")
            return None
        
    else:
        data = response.json()
        
    error_names = list(data["errors"].keys())
    
    if error_names is not None:
        for key in error_names:
                qualibooth_api_error_url=f"{qualibooth_api_host}{qualibooth_api_endpoint}/{project_id}/detail/period/{from_datetime}/{to_datetime}/{key}?count={count}"
                logging.info(qualibooth_api_error_url)
                response = requests.get(qualibooth_api_error_url, headers=headers)
                response_data = response.json()
                events = response_data["urls"]
                logging.info(f"Data fetched error={key} count={len(events)}")
                
                for event in events:
                    accessibility_error_event = {
                        "error_id": key,
                        "url": None,
                        "project_id": project_id,
                        "device": None,
                        "issue_count": None,
                        "view_count": None,
                        "timestamp": from_datetime
                    }
                    accessibility_error_event["url"] = event["url"]
                    accessibility_error_event["device"] = event["device"]
                    accessibility_error_event["issue_count"] = event["issueCount"]
                    accessibility_error_event["view_count"] = event["viewCount"]
                    dt = datetime.strptime(from_datetime, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

                    splunk_event = helper.new_event(
                        source=qualibooth_api_endpoint,
                        sourcetype="qualibooth:accessibility:error",
                        host=qualibooth_api_host,
                        index=data_input_index,
                        data=json.dumps(accessibility_error_event),
                        time=dt.timestamp()
                    )
                    ew.write_event(splunk_event)
    

    last_executed = today_midnight.strftime("%Y-%m-%dT%H:%M:%S.000Z")              
    helper.save_check_point(data_input_name, {"last_executed": last_executed})
    logging.info(f"Checkpoint saved: {last_executed}")                
                    

        
    
    
