"""Turn Previdian API rows into sourcetyped events and lookup rows."""

import json
from datetime import datetime

CVE_URL = "https://previdian.com/%s"

LOOKUP_FIELDS = [
  "cve_id",
  "vulnerability_id",
  "title",
  "vendor",
  "product",
  "added_date",
  "cvss_score",
  "cvss_severity",
  "epss_score",
  "confidence_level",
  "in_cisa_kev",
  "sensor_observed",
  "first_observed",
  "last_observed",
  "unique_attacker_ips",
  "total_attempts",
  "previdian_url"
]


def kev_event(row):
  event = _kev_record(row)
  return {
    "sourcetype": "previdian:kev",
    "time": event.get("added_date"),
    "data": event
  }


def kev_lookup_row(row):
  event = _kev_record(row)
  return {field: _cell(event.get(field)) for field in LOOKUP_FIELDS}


def notification_event(row):
  payload = row.get("payload") or {}
  data_block = payload.get("data") or {}
  cve_id = row.get("cve_id") or data_block.get("cve_id") or ""
  event = {
    "id": row.get("id"),
    "event_type": row.get("event_type") or _event_name(payload.get("event")),
    "cve_id": cve_id,
    "vulnerability_id": row.get("vulnerability_id") or data_block.get("vulnerability_id"),
    "ghsa_id": row.get("ghsa_id") or data_block.get("ghsa_id"),
    "title": data_block.get("title"),
    "vendor": data_block.get("vendor"),
    "product": data_block.get("product"),
    "created_at": row.get("created_at") or payload.get("delivered_at"),
    "occurred_at": data_block.get("occurred_at"),
    "matched_via": data_block.get("matched_via"),
    "previdian_url": data_block.get("url") or _cve_url(cve_id),
    "watch_event": payload.get("event")
  }
  return {
    "sourcetype": "previdian:notification",
    "time": event.get("created_at"),
    "data": event
  }


def observation_event(row):
  cve_id = row.get("cve_id") or ""
  event = {
    "cve_id": cve_id,
    "vulnerability_id": row.get("vulnerability_id"),
    "ghsa_id": row.get("ghsa_id"),
    "observed_at": row.get("observed_at"),
    "attacker_ip": row.get("attacker_ip"),
    "request_path": row.get("request_path") or row.get("path") or row.get("uri"),
    "user_agent": row.get("user_agent"),
    "http_method": row.get("http_method") or row.get("method"),
    "response_status": row.get("response_status"),
    "payload_location": row.get("payload_location"),
    "payload_field": row.get("payload_field"),
    "payload_sample": row.get("payload_sample"),
    "previdian_url": _cve_url(cve_id)
  }
  return {
    "sourcetype": "previdian:observation",
    "time": event.get("observed_at"),
    "data": event
  }


def infrastructure_event(row):
  cve_id = row.get("cve_id") or ""
  event = {
    "id": row.get("id"),
    "host": row.get("host"),
    "port": row.get("port"),
    "kind": row.get("kind"),
    "cve_id": cve_id,
    "ghsa_id": row.get("ghsa_id"),
    "last_seen_at": row.get("last_seen_at") or row.get("last_seen"),
    "first_seen_at": row.get("first_seen_at") or row.get("first_seen"),
    "unique_attacker_ips": row.get("unique_attacker_ips"),
    "attacker_ips": row.get("attacker_ips") or [],
    "open_directory": row.get("open_directory"),
    "previdian_url": _cve_url(cve_id)
  }
  return {
    "sourcetype": "previdian:infrastructure",
    "time": event.get("last_seen_at"),
    "data": event
  }


def attacker_event(row):
  ip = row.get("ip") or row.get("attacker_ip")
  event = {
    "attacker_ip": ip,
    "country": row.get("country"),
    "tor_exit": row.get("tor_exit"),
    "unique_cves": row.get("unique_cves") or row.get("cve_count"),
    "last_seen_at": row.get("last_seen_at") or row.get("last_seen") or row.get("last_observed")
  }
  return {
    "sourcetype": "previdian:attacker",
    "time": event.get("last_seen_at"),
    "data": event
  }


def priority_lookup_row(row):
  cve = row.get("cve") or {}
  cve_id = row.get("cve_id") or ""
  return {
    "cve_id": cve_id,
    "vulnerability_id": row.get("vulnerability_id") or "",
    "title": cve.get("title") or "",
    "vendor": cve.get("affected_vendor") or "",
    "product": cve.get("affected_product") or "",
    "classification": row.get("classification") or "",
    "bucket": row.get("bucket") or "",
    "workflow_state": row.get("workflow_state") or "",
    "score": _cell(row.get("score")),
    "sensor_observed": _cell(row.get("sensor_observed")),
    "in_cisa_kev": _in_cisa_label(row),
    "confidence_level": row.get("confidence_level") or "",
    "watched_name": row.get("watched_name") or "",
    "previdian_url": _cve_url(cve_id)
  }


def epoch(value):
  """Splunk modular input <time> must be Unix seconds."""
  if not value:
    return None
  text = str(value).strip().replace("Z", "+00:00")
  try:
    parsed = datetime.fromisoformat(text)
  except ValueError:
    return None
  return "%.3f" % parsed.timestamp()


def dumps(data):
  return json.dumps(data, separators=(",", ":"), default=str, sort_keys=True)


def _kev_record(row):
  status = row.get("exploit_status") or {}
  sensor = row.get("sensor") or {}
  cve_id = row.get("cve_id") or row.get("vulnerability_id") or ""
  observed = sensor.get("observed")
  return {
    "cve_id": cve_id,
    "vulnerability_id": row.get("vulnerability_id") or cve_id,
    "ghsa_id": row.get("ghsa_id"),
    "title": row.get("title"),
    "vendor": row.get("affected_vendor"),
    "product": row.get("affected_product"),
    "added_date": _time_value(row.get("added_date")),
    "cvss_score": row.get("cvss_score"),
    "cvss_severity": row.get("cvss_severity"),
    "epss_score": row.get("epss_score"),
    "confidence_level": status.get("confidence_level"),
    "in_cisa_kev": _in_cisa_label(row),
    "sensor_observed": bool(observed) if observed is not None else False,
    "first_observed": _time_value(sensor.get("first_observed")),
    "last_observed": _time_value(sensor.get("last_observed")),
    "unique_attacker_ips": sensor.get("unique_attacker_ips"),
    "total_attempts": sensor.get("total_attempts"),
    "previdian_url": _cve_url(cve_id)
  }


def _event_name(value):
  text = value or ""
  if text.startswith("watchlist."):
    return text.split(".", 1)[1]
  return text


def _cve_url(cve_id):
  if not cve_id:
    return "https://previdian.com"
  return CVE_URL % cve_id


def _time_value(value):
  if value is None:
    return None
  return str(value)


def _in_cisa_label(row):
  """yes, no, or blank when the API did not say."""
  if row.get("in_cisa_kev") is not None:
    return _yes_no(row.get("in_cisa_kev"))
  if row.get("cisa_kev") is not None:
    return _yes_no(row.get("cisa_kev"))
  if row.get("not_yet_in_cisa_kev") is not None:
    return "no" if row.get("not_yet_in_cisa_kev") else "yes"
  return ""


def _yes_no(value):
  if isinstance(value, bool):
    return "yes" if value else "no"
  text = str(value).strip().lower()
  if text in ("true", "1", "yes"):
    return "yes"
  if text in ("false", "0", "no"):
    return "no"
  return ""


def _cell(value):
  if value is None:
    return ""
  if isinstance(value, bool):
    return "true" if value else "false"
  return str(value)
