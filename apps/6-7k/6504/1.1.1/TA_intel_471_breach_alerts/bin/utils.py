import configparser
import os
from typing import Union
import requests
import traceback
from datetime import datetime


def get_proxy_kwargs(proxy_settings: Union[dict, None]) -> dict:
    if not proxy_settings:
        return {}
    proxy_bits = [proxy_settings["proxy_type"],
                  "://",
                  proxy_settings["proxy_url"],
                  ":",
                  proxy_settings["proxy_port"]
                 ]
    username = proxy_settings.get("proxy_username")
    password = proxy_settings.get("proxy_password")
    if username and password:
        proxy_bits.insert(2, "@")
        proxy_bits.insert(2, password)
        proxy_bits.insert(2, ":")
        proxy_bits.insert(2, username)
    proxy = "".join(proxy_bits)
    return {"http": proxy, "https": proxy}


def get_version():
    here = os.path.dirname(os.path.realpath(__file__))
    config = configparser.ConfigParser()
    config.read(os.path.join(here, "..", "default", "app.conf"))
    try:
        return config["launcher"]["version"]
    except KeyError:
        return "UNSPECIFIED"


def raise_web_message(helper, msg: str):
    try:
        server_uri = helper.context_meta["server_uri"]
        session_key = helper.context_meta["session_key"]
        uri = f"{server_uri}/services/messages/new"
        headers = {"Authorization": f"Splunk {session_key}"}
        request_body = {
            "name": "Custom message from Intel 471 Add-on",
            "value": msg,
            "severity": "warn"
        }
        requests.post(uri, headers=headers, data=request_body)
    except Exception as e:
        helper.log_error(f"Raising of web message failed: {str(e)}")
        helper.log_error(traceback.format_exc())

def convert_ts(iso_timestamp) -> int:
    """
    Convert ISO timestamp string to Unix timestamp in milliseconds.

    Supports two formats:
    - "%Y-%m-%dT%H:%M:%SZ" (e.g., "2013-03-18T11:09:00Z")
    - "%Y-%m-%dT%H:%M:%S.%fZ" (e.g., "2023-01-23T14:49:30.886Z")
    """
    # Try format with milliseconds first
    try:
        dt = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        # Fall back to format without milliseconds
        dt = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ")

    unix_millis = int(dt.timestamp() * 1000)
    return unix_millis

def remove_none_values(data):
    """
    Recursively remove keys with None values from a nested dictionary.

    Args:
        data: A dictionary, list, or other data structure that may contain
              nested dictionaries with None values.

    Returns:
        A new data structure with all None value keys removed from dictionaries.
        Lists are preserved and processed recursively if they contain dictionaries.

    Example:
        >>> data = {"a": 1, "b": None, "c": {"d": 2, "e": None}}
        >>> remove_none_values(data)
        {"a": 1, "c": {"d": 2}}
    """
    if isinstance(data, dict):
        return {
            key: remove_none_values(value)
            for key, value in data.items()
            if value is not None
        }
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data]
    else:
        return data


def extract_path(d: dict, path: str, sentinel=None):
  if not all([d, path]):
    return sentinel
  path = path.split(".")
  for key in path:
    if isinstance(d, dict) and key in d:
      d = d[key]
    else:
      return sentinel
  # Return sentinel if final value is None and sentinel was provided
  if d is None and sentinel is not None:
    return sentinel
  return d
