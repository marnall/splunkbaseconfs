import ipaddress
import re
from urllib.parse import urlparse

INTEL_TYPES = {
    "certificate": {
        "lookup": "falconer_local_certificate_intel",
        "file": "falconer_local_certificate_intel.csv",
        "required": ["certificate_issuer", "certificate_subject", "certificate_issuer_organization", "certificate_subject_organization", "certificate_serial", "certificate_issuer_unit", "certificate_subject_unit", "description", "weight"],
        "observables": ["certificate_serial", "certificate_subject", "certificate_issuer"],
    },
    "email": {
        "lookup": "falconer_local_email_intel",
        "file": "falconer_local_email_intel.csv",
        "required": ["description", "src_user", "subject", "weight"],
        "observables": ["src_user", "subject"],
    },
    "file": {
        "lookup": "falconer_local_file_intel",
        "file": "falconer_local_file_intel.csv",
        "required": ["description", "file_hash", "file_name", "weight"],
        "observables": ["file_hash", "file_name"],
    },
    "http": {
        "lookup": "falconer_local_http_intel",
        "file": "falconer_local_http_intel.csv",
        "required": ["description", "http_referrer", "http_user_agent", "url", "weight"],
        "observables": ["url", "http_user_agent", "http_referrer"],
    },
    "ip": {
        "lookup": "falconer_local_ip_intel",
        "file": "falconer_local_ip_intel.csv",
        "required": ["description", "ip", "weight"],
        "observables": ["ip"],
    },
    "domain": {
        "lookup": "falconer_local_domain_intel",
        "file": "falconer_local_domain_intel.csv",
        "required": ["description", "domain", "weight"],
        "observables": ["domain"],
    },
    "process": {
        "lookup": "falconer_local_process_intel",
        "file": "falconer_local_process_intel.csv",
        "required": ["description", "process", "process_file_name", "weight"],
        "observables": ["process", "process_file_name"],
    },
    "registry": {
        "lookup": "falconer_local_registry_intel",
        "file": "falconer_local_registry_intel.csv",
        "required": ["description", "registry_path", "registry_value_name", "registry_value_text", "weight"],
        "observables": ["registry_path", "registry_value_name", "registry_value_text"],
    },
    "service": {
        "lookup": "falconer_local_service_intel",
        "file": "falconer_local_service_intel.csv",
        "required": ["description", "service", "service_file_hash", "service_dll_file_hash", "weight"],
        "observables": ["service", "service_file_hash", "service_dll_file_hash"],
    },
    "user": {
        "lookup": "falconer_local_user_intel",
        "file": "falconer_local_user_intel.csv",
        "required": ["description", "user", "weight"],
        "observables": ["user"],
    },
}

TYPE_ALIASES = {
    "hash": "file",
    "url": "http",
    "domains": "domain",
}

MANAGED_HEADERS = [
    "source",
    "threat_collection",
    "threat_group",
    "confidence",
    "expiration",
    "notes",
    "falconer_managed",
    "falconer_key",
    "falconer_entry_id",
    "updated_time",
    "threat_description",
]


def canonical_type(value):
    value = str(value or "").strip().lower()
    value = TYPE_ALIASES.get(value, value)
    if value not in INTEL_TYPES:
        raise ValueError("indicator_type must be one of " + ", ".join(INTEL_TYPES.keys()))
    return value


def normalize_value(indicator_type, field, value):
    value = str(value or "").strip()
    if field in ("domain", "src_user", "user", "file_hash", "url"):
        return value.lower()
    return value


def primary_observable(doc, indicator_type):
    for field in INTEL_TYPES[indicator_type]["observables"]:
        value = normalize_value(indicator_type, field, doc.get(field))
        if value:
            return field, value
    value = normalize_value(indicator_type, "indicator", doc.get("indicator"))
    return "indicator", value


def validate_weight(value):
    try:
        weight = int(value if value not in (None, "") else 60)
    except Exception:
        return None, "weight must be an integer"
    if weight < 1 or weight > 100:
        return None, "weight must be between 1 and 100"
    return weight, ""


def validate_observable(indicator_type, field, value):
    value = str(value or "").strip()
    if not value:
        return ""
    if field == "ip":
        try:
            ipaddress.ip_address(value)
            return ""
        except Exception:
            return "ip must be a valid IP address"
    if field in ("file_hash", "service_file_hash", "service_dll_file_hash"):
        if not re.fullmatch(r"[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}", value):
            return f"{field} must be MD5, SHA1, or SHA256"
    if field == "url":
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "url must start with http:// or https:// and include a host"
    if field in ("src_user", "user") and indicator_type == "email":
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            return f"{field} must be an email address"
    if field == "domain":
        if len(value) > 253 or "." not in value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]", value):
            return "domain must be a valid domain"
    return ""


def validate_doc(doc, require_all_headers=True):
    indicator_type = canonical_type(doc.get("indicator_type"))
    spec = INTEL_TYPES[indicator_type]
    errors = []
    row = dict(doc)
    row["indicator_type"] = indicator_type
    weight, weight_error = validate_weight(row.get("weight"))
    if weight_error:
        errors.append(weight_error)
    else:
        row["weight"] = weight

    for field in spec["required"]:
        if field == "weight":
            continue
        if require_all_headers and str(row.get(field) or "").strip() == "":
            errors.append(f"{field} is required for {indicator_type} intel")

    observable_found = False
    for field in spec["observables"]:
        row[field] = normalize_value(indicator_type, field, row.get(field))
        if row[field]:
            observable_found = True
            error = validate_observable(indicator_type, field, row[field])
            if error:
                errors.append(error)

    if not observable_found:
        errors.append(f"at least one observable field is required for {indicator_type}: " + ", ".join(spec["observables"]))

    if not str(row.get("description") or "").strip():
        row["description"] = "Falconer-authored intelligence"
    return row, errors
