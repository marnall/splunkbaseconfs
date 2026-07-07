import datetime as dt
import re
from datetime import datetime


def get_event_time(data, event_type):
    """Get event_time from data.

    :param data: dict Sample event
    :param event_type: str Event type (indicator/reports/cve/mentions)
    :return: timestamp: float epoch timestamp
    """
    if 'timestamp' in list(data.keys()) and event_type == "indicators":
        try:
            timestamp = float(data.get('timestamp'))
            return timestamp
        except Exception:
            return None
    elif event_type == "cve":
        return get_cve_time(data)
    elif event_type == "mentions":
        return get_mention_time(data)
    elif event_type == "compromised_credentials":
        return get_compromised_credentials_time(data)
    elif event_type == "alerts":
        return get_alerts_time(data)
    elif event_type == "ransomware":
        return get_ransomware_time(data)
    elif 'version_posted_at' in list(data.keys()) and event_type == "reports":
        try:
            version_posted_at = data['version_posted_at']
            timestamp = get_report_time(version_posted_at)
            return timestamp
        except Exception:
            return None
    else:
        return None


def get_mention_time(data):
    """Function to return index time for Mentions."""
    try:
        datetime_obj = datetime.strptime(data.get("date"), "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = datetime_obj.timestamp()
        return float(timestamp)
    except Exception:
        return None


def get_compromised_credentials_time(data):
    """Function to return index time for Compromised Credentials."""
    if data.get("_source", {}).get("header_", {}).get("indexed_at"):
        timestamp = data.get("_source", {}).get("header_", {}).get("indexed_at")
        if timestamp:
            return float(timestamp)
        else:
            return None
    return None


def get_alerts_time(data):
    """Function to return index time for Alerts."""
    try:
        datetime_obj = datetime.strptime(data.get("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = datetime_obj.timestamp()
        return float(timestamp)
    except Exception:
        return None


def get_ransomware_time(data):
    """Function to return index time for Ransomware."""
    try:
        datetime_obj = datetime.strptime(data.get("date"), "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = datetime_obj.timestamp()
        return float(timestamp)
    except Exception:
        return None


def get_cve_time(data):
    """Function to return index time for CVE."""
    try:
        if data.get("timelines").get("last_modified_at"):
            datetime_obj = datetime.strptime(data.get("timelines").get("last_modified_at"), "%Y-%m-%dT%H:%M:%S.%fZ")
        elif data.get("timelines").get("published_at"):
            datetime.strptime(data.get("timelines").get("published_at"), "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            return None
        timestamp = datetime_obj.timestamp()
        return float(timestamp)
    except Exception:
        return None


def get_report_time(version_posted_at):
    """Get Time for reports.

    :param version_posted_at: Date string iso 8601 format
    :return total_time: total seconds since epoch
    """
    pat_with_float = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}"
    pat_without_float = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}"
    if re.match(pat_with_float, version_posted_at):
        date_format = "%Y-%m-%dT%H:%M:%S.%f"
    elif re.match(pat_without_float, version_posted_at):
        date_format = "%Y-%m-%dT%H:%M:%S"
    else:
        return None
    hour, minute = version_posted_at[-5:].split(':')
    total_time = (datetime.strptime(version_posted_at[:-6], date_format) - datetime(1970, 1, 1)).total_seconds()
    if hour and minute:
        time_zone_sec = int(dt.timedelta(hours=int(hour), minutes=int(minute)).total_seconds())
        if version_posted_at[-6] == '+':
            total_time = total_time - time_zone_sec
        elif version_posted_at[-6] == '-':
            total_time = total_time + time_zone_sec
    return total_time
