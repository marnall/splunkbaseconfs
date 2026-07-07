# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utility functions for Group-IB Threat Intelligence Connector."""


def config_to_int_flag(config_value):
    """Convert config value to integer flag (0 or 1)."""
    if isinstance(config_value, bool):
        return 1 if config_value else 0
    if isinstance(config_value, str):
        return 1 if config_value.lower() in ("true", "1", "yes") else 0
    if isinstance(config_value, int | float):
        return 1 if config_value else 0
    return 0


def get_nested_value(data, path, default=None):
    """Get value from nested dict using dot notation path.

    Example: get_nested_value({"a": {"b": 1}}, "a.b") returns 1
    """
    if not data or not isinstance(data, dict):
        return default

    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default

    return value if value is not None else default


def get_first_value(data_source, key):
    """Extract first value from a list in data_source."""
    if not data_source or not isinstance(data_source, dict):
        return None

    value_list = data_source.get(key.lower(), [])
    if value_list and isinstance(value_list, list) and len(value_list) > 0:
        return value_list[0]
    return None


def get_joined_values(data_source, key, separator=", "):
    """Join all values from a list in data_source."""
    if not data_source or not isinstance(data_source, dict):
        return None

    value_list = data_source.get(key.lower(), [])
    if value_list and isinstance(value_list, list) and len(value_list) > 0:
        return separator.join(str(v) for v in value_list if v)
    return None


def safe_get_list(data, key):
    """Get a list from dictionary, ensuring result is always a list."""
    if not data or not isinstance(data, dict):
        return []

    value = data.get(key, [])
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def join_list_values(values, separator=", "):
    """Join a list of values into a string."""
    if not values or not isinstance(values, list):
        return None

    filtered = [str(v) for v in values if v]
    return separator.join(filtered) if filtered else None


def mask_password(password, mask_chars=3, mask_symbol="*"):
    """Mask password by replacing last N characters."""
    if not password or not isinstance(password, str) or len(password) == 0:
        return None

    if len(password) > mask_chars:
        return password[:-mask_chars] + (mask_symbol * mask_chars)
    return mask_symbol * mask_chars


def determine_hash_type(hash_value):
    """Determine hash type based on length. Returns (cef_field_name, hash_type_label)."""
    if not hash_value:
        return None, None

    hash_len = len(hash_value)

    if hash_len == 32:
        return "fileHashMd5", "MD5"
    if hash_len == 40:
        return "fileHashSha1", "SHA1"
    if hash_len == 64:
        return "fileHashSha256", "SHA256"
    return "fileHash", "Unknown"


def normalize_to_list(value):
    """Ensure value is always a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_names_from_array(items, name_key="name"):
    """Extract names from array of dicts or strings, return joined string."""
    if not items or not isinstance(items, list):
        return None
    names = []
    for item in items:
        if isinstance(item, dict) and item.get(name_key):
            names.append(item.get(name_key))
        elif isinstance(item, str) and item:
            names.append(item)
    return ", ".join(names) if names else None


def create_artifact(name, cef, artifact_type="*other", label="gib_info", start_time=None, end_time=None, severity=None, **kwargs):
    """Factory function for creating artifact dictionaries."""
    artifact = {"name": name, "type": artifact_type, "label": label, "cef": cef}
    if start_time:
        artifact["start_time"] = start_time
    if end_time:
        artifact["end_time"] = end_time
    if severity:
        artifact["severity"] = severity
    artifact.update(kwargs)
    return artifact


def extract_ipv4_fields(ipv4_data, cef, prefix=""):
    """Extract common IPv4 fields to CEF dict."""
    if not ipv4_data or not isinstance(ipv4_data, dict):
        return cef

    field_map = {
        "ip": f"{prefix}IP" if prefix else "destinationAddress",
        "countryName": f"{prefix}Country" if prefix else "Country",
        "city": f"{prefix}City" if prefix else "City",
        "provider": f"{prefix}Provider" if prefix else "Provider",
        "region": f"{prefix}Region" if prefix else "Region",
        "asn": f"{prefix}ASN" if prefix else "ASN",
    }

    for src_key, dest_key in field_map.items():
        value = ipv4_data.get(src_key)
        if value:
            cef[dest_key] = str(value) if src_key == "asn" else value
    return cef


def extract_cnc_fields(cnc_data, cef):
    """Extract CNC fields to CEF dict."""
    if not cnc_data or not isinstance(cnc_data, dict):
        return cef

    if cnc_data.get("domain"):
        cef["CNC Domain"] = cnc_data.get("domain")
    if cnc_data.get("url"):
        cef["CNC URL"] = cnc_data.get("url")

    cnc_ipv4 = cnc_data.get("ipv4")
    if cnc_ipv4 and isinstance(cnc_ipv4, dict):
        if cnc_ipv4.get("ip"):
            cef["CNC IP"] = cnc_ipv4.get("ip")
        if cnc_ipv4.get("countryName"):
            cef["CNC Country"] = cnc_ipv4.get("countryName")
        if cnc_ipv4.get("city"):
            cef["CNC City"] = cnc_ipv4.get("city")
        if cnc_ipv4.get("provider"):
            cef["CNC Provider"] = cnc_ipv4.get("provider")
        if cnc_ipv4.get("asn"):
            cef["CNC ASN"] = str(cnc_ipv4.get("asn"))
    return cef


def get_items_from_chunk(chunk):
    """Extract items list from chunk safely."""
    if not chunk or not chunk.raw_dict:
        return []
    return chunk.raw_dict.get("items", [])
