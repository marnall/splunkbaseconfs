"""Shared helpers for the HoneyLabs add-on: credential storage, HTTP, and the
one place that decides what to tell an analyst about their quota.

Kept dependency-free on purpose. Splunk Cloud rejects apps with static
third-party dependencies, and `requests` is not guaranteed present in the
Python that runs a search command, so everything here uses the standard
library.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import ipaddress
import json
import os
import ssl
import sys

try:                                     # py3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                      # pragma: no cover - py2 fallback
    from urllib2 import Request, urlopen, HTTPError, URLError

APP_NAME = "honeylabs"


def _version():
    """Read the version from app.conf rather than repeating it here.

    These two drifted: app.conf said 1.0.1 while this constant still said
    1.0.0, so every request the app made identified itself as the previous
    release and the two versions were indistinguishable in server-side
    telemetry. app.conf is the value Splunk and Splunkbase actually publish,
    so it is the one worth trusting.
    """
    conf = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "default", "app.conf")
    try:
        with open(conf) as fh:
            section = ""
            for line in fh:
                line = line.strip()
                if line.startswith("["):
                    section = line.strip("[]")
                elif section == "launcher" and line.startswith("version"):
                    return line.split("=", 1)[1].strip()
    except Exception:                    # never break a search over a version string
        pass
    return "0.0.0"


VERSION = _version()
API_BASE = os.environ.get("HONEYLABS_API_BASE", "https://honeylabs.net")
USER_AGENT = "Splunk-honeylabs/%s (+https://honeylabs.net/integrations/splunk-es)" % VERSION

# Sits in front of every network call. Splunk kills a search command that
# blocks too long, and a hung enrichment should degrade to "no annotation"
# rather than to a dead search.
TIMEOUT = 60

_REALM = "honeylabs_api"


def get_api_key(service):
    """Read the stored API key, or None.

    Stored through Splunk's storage/passwords endpoint so it is encrypted at
    rest and never appears in a .conf file, which is both the Splunk
    convention and an AppInspect requirement.

    Anonymous is a supported mode, not a failure: HoneyLabs answers without a
    key at a lower cap, so an analyst can install this and get results before
    deciding whether to sign up.
    """
    if service is None:
        return None
    try:
        for cred in service.storage_passwords:
            if cred.realm == _REALM or _REALM in (cred.name or ""):
                password = cred.clear_password
                # The setup page writes a JSON blob when it stores more than
                # one field; accept either shape.
                if password and password.startswith("{"):
                    try:
                        return json.loads(password).get("api_key") or None
                    except ValueError:
                        return password
                return password or None
    except Exception:                      # noqa: BLE001
        return None
    return None


def is_public_ipv4(value):
    """True for an address worth spending a credit on.

    Filters private, loopback, link-local and reserved space before it costs
    anything. A firewall log is full of RFC1918 addresses, and asking a
    honeypot network about someone's own LAN is both useless and billable.
    """
    if not value or len(value) > 15:
        return False
    try:
        addr = ipaddress.ip_address(str(value))
    except ValueError:
        return False
    return addr.version == 4 and addr.is_global


def http_post_sse(url, body, headers):
    """POST and yield ("row"|"summary", dict) as the SSE stream arrives.

    HoneyLabs answers /api/enrich with text/event-stream: one `data:` line per
    address, then an `event: summary` frame carrying the credit accounting.
    Yielding as it arrives keeps memory flat on a large batch.
    """
    req = Request(url, data=body, headers=headers)
    ctx = ssl.create_default_context()
    kind = "row"
    try:
        resp = urlopen(req, timeout=TIMEOUT, context=ctx)
    except HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8", "replace")).get("error", "")
        except Exception:                  # noqa: BLE001
            pass
        raise RuntimeError("HTTP %s %s" % (exc.code, detail or exc.reason))
    except URLError as exc:
        raise RuntimeError("cannot reach %s (%s)" % (url, exc.reason))

    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if not line:
                continue
            if line.startswith("event:"):
                kind = line.split(":", 1)[1].strip() or "row"
                continue
            if line.startswith("data:"):
                chunk = line.split(":", 1)[1].strip()
                if not chunk:
                    continue
                try:
                    payload = json.loads(chunk)
                except ValueError:
                    continue
                yield ("summary" if payload.get("_summary") else kind, payload)
                kind = "row"


def http_get(url, headers=None):
    """Plain GET returning bytes. Used by the feed input."""
    req = Request(url, headers=headers or {"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            return resp.read()
    except HTTPError as exc:
        raise RuntimeError("HTTP %s fetching %s" % (exc.code, url))
    except URLError as exc:
        raise RuntimeError("cannot reach %s (%s)" % (url, exc.reason))


def quota_message(summary):
    """What to tell the analyst about cost, or None to stay quiet.

    This is the only place the add-on mentions plans, and it earns the right
    to by being attached to a number the analyst just spent. It stays silent
    while there is plenty of headroom: an upgrade prompt on every search is
    noise, and noise gets an app uninstalled.
    """
    if not isinstance(summary, dict):
        return None
    used = summary.get("credits_used")
    remaining = summary.get("remaining_today")
    if used is None:
        return None

    # Anonymous: no account at all. Say what an account changes, once.
    if remaining is None:
        return ("HoneyLabs: enriched %s address(es) anonymously. A free account "
                "raises the per-search cap and unlocks saved feeds. "
                "https://honeylabs.net/dashboard?src=splunk-app" % used)

    try:
        remaining = int(remaining)
    except (TypeError, ValueError):
        return None

    if remaining <= 0:
        return ("HoneyLabs: daily credits exhausted, later events were not "
                "enriched. The budget resets at midnight UTC; a larger one and "
                "a 90-day window are part of Pro. "
                "https://honeylabs.net/upgrade?src=splunk-app")
    if remaining < used:
        return ("HoneyLabs: %s credits left today, less than this search just "
                "used. A bigger search will run short. "
                "https://honeylabs.net/upgrade?src=splunk-app" % remaining)
    return None
