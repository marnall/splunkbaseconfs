"""One poll: catalog, Watch notifications, Priority snapshot, optional Enterprise telemetry."""

import json
import os
from datetime import datetime, timedelta, timezone

from previdian_client import PrevidianClient, PrevidianError
from previdian_events import (
  attacker_event,
  infrastructure_event,
  kev_event,
  kev_lookup_row,
  notification_event,
  observation_event,
  priority_lookup_row
)

TRUTHY = {"1", "true", "yes", "on"}


def enabled(value, default=True):
  if value is None or value == "":
    return default
  return str(value).strip().lower() in TRUTHY


class Checkpoint:
  def __init__(self, path):
    self.path = path
    self.data = {}
    if path and os.path.exists(path):
      with open(path, "r", encoding="utf-8") as handle:
        self.data = json.load(handle)

  def get(self, key):
    return self.data.get(key)

  def set(self, key, value):
    if value:
      self.data[key] = value

  def save(self):
    if not self.path:
      return
    directory = os.path.dirname(self.path)
    if directory:
      os.makedirs(directory, exist_ok=True)
    temporary = self.path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
      json.dump(self.data, handle, sort_keys=True)
    os.replace(temporary, self.path)


def poll(config, checkpoint, client=None):
  """Return events, lookup rows, and messages. Advance checkpoint only for completed streams."""
  client = client or PrevidianClient(config["base_url"], config["api_token"], config["tier"])
  client.validate()
  events = []
  kev_rows = []
  priority_rows = []
  messages = []

  if enabled(config.get("collect_kevs"), True):
    if checkpoint.get("kevs_cisa_labels") != 1:
      for row in client.iter_kevs():
        kev_rows.append(kev_lookup_row(row))
      checkpoint.set("kevs_cisa_labels", 1)
    started = _now()
    cursor = checkpoint.get("kevs_modified_since")
    for row in client.iter_kevs(modified_since=cursor):
      events.append(kev_event(row))
      kev_rows.append(kev_lookup_row(row))
    checkpoint.set("kevs_modified_since", started)

  if enabled(config.get("collect_notifications"), True):
    cursor = checkpoint.get("notifications_since")
    newest = cursor
    for row in client.iter_notifications(since=cursor):
      event = notification_event(row)
      created = event["data"].get("created_at")
      if _already_seen(cursor, created):
        continue
      events.append(event)
      newest = _later(newest, created)
    if newest:
      checkpoint.set("notifications_since", newest)

  if enabled(config.get("collect_priority"), True):
    for row in client.iter_priority_items():
      priority_rows.append(priority_lookup_row(row))

  tier = config.get("tier")
  if enabled(config.get("collect_observations"), False):
    if tier != "enterprise":
      messages.append("Skipped observations. Enterprise token required.")
    else:
      cursor = checkpoint.get("observations_since") or _ago(7)
      try:
        found, newest = _collect_timed(client.iter_observations(observed_since=cursor), observation_event, "observed_at", cursor)
      except PrevidianError as error:
        messages.append(str(error))
      else:
        events.extend(found)
        if newest:
          checkpoint.set("observations_since", newest)

  if enabled(config.get("collect_infrastructure"), False):
    if tier != "enterprise":
      messages.append("Skipped attacker infrastructure. Enterprise token required.")
    else:
      cursor = checkpoint.get("infrastructure_seen_since") or _ago(30)
      try:
        found, newest = _collect_timed(client.iter_infrastructures(seen_since=cursor), infrastructure_event, "last_seen_at", cursor)
      except PrevidianError as error:
        messages.append(str(error))
      else:
        events.extend(found)
        if newest:
          checkpoint.set("infrastructure_seen_since", newest)

  if enabled(config.get("collect_attackers"), False):
    if tier != "enterprise":
      messages.append("Skipped attackers. Enterprise token required.")
    else:
      cursor = checkpoint.get("attackers_since")
      newest = cursor
      for row in client.iter_attackers():
        event = attacker_event(row)
        seen = event["data"].get("last_seen_at")
        if _already_seen(cursor, seen):
          continue
        events.append(event)
        newest = _later(newest, seen)
      checkpoint.set("attackers_since", newest or _now())

  return {
    "events": events,
    "kev_rows": kev_rows,
    "priority_rows": priority_rows,
    "messages": messages
  }


def _collect_timed(rows, event_fn, time_key, cursor):
  found = []
  newest = cursor
  for row in rows:
    event = event_fn(row)
    seen = event["data"].get(time_key)
    if _already_seen(cursor, seen):
      continue
    found.append(event)
    newest = _later(newest, seen)
  return found, newest


def _already_seen(cursor, seen):
  if not cursor:
    return False
  if not seen:
    return True
  return str(seen) <= str(cursor)


def _later(current, seen):
  if seen and (not current or str(seen) > str(current)):
    return str(seen)
  return current


def _now():
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ago(days):
  return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def config_from_params(params):
  required = ("api_token", "tier")
  missing = [name for name in required if not params.get(name)]
  if missing:
    raise PrevidianError("Missing input settings: %s" % ", ".join(missing))
  return {
    "api_token": params.get("api_token"),
    "base_url": params.get("base_url") or "https://previdian.com",
    "tier": params.get("tier"),
    "index": params.get("index") or "previdian",
    "collect_kevs": params.get("collect_kevs", "1"),
    "collect_notifications": params.get("collect_notifications", "1"),
    "collect_priority": params.get("collect_priority", "1"),
    "collect_observations": params.get("collect_observations", "0"),
    "collect_infrastructure": params.get("collect_infrastructure", "0"),
    "collect_attackers": params.get("collect_attackers", "0")
  }
