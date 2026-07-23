"""
dashboard_client.py — Thin splunkd REST helper for Dashboard Studio views.

Uses splunklib.client (consistent with kanbanwrite's client.connect pattern).
No direct urllib calls — splunklib Service.request() handles the HTTP layer.

Public API:
    list_kanban_views(service)              -> list of view dicts
    get_view(service, app, owner, name)     -> dict or None
    save_view(service, app, owner, name, xml) -> None
    seconds_since_updated(entry_updated)    -> float
"""

import datetime
import time

from wiring import KANBAN_VIZ_TYPE

# ---------------------------------------------------------------------------
# ISO-8601 helper
# ---------------------------------------------------------------------------

def seconds_since_updated(entry_updated):
    """
    Parse an ISO-8601 datetime string (as returned by Splunk's eai:updated /
    updated fields) and return the number of seconds elapsed since that time.

    Handles the common Splunk format: '2024-01-15T12:34:56+00:00'
    Falls back to 0 on any parse error (treats as 'just updated').
    """
    if not entry_updated:
        return 0.0
    try:
        s = str(entry_updated).strip()
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return max(0.0, time.time() - dt.timestamp())
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# list_kanban_views
# ---------------------------------------------------------------------------

def list_kanban_views(service):
    """
    Return a list of dicts for Dashboard Studio views that contain the kanban
    board visualization type.

    Each dict has keys: name, app, owner, eai_data, updated (str ISO-8601).

    Strategy:
      1. Try a server-side search filter (eai:data=*kanban_board.kanban*).
         If the server rejects the filter or returns an error, fall back to
         listing all dashboard views and filtering client-side.
    """
    try:
        results = _fetch_views(service, search_filter='eai:data="*{}*"'.format(KANBAN_VIZ_TYPE))
        # Successful call: use server-filtered result even if empty (the server
        # already searched; an empty list means no kanban views exist right now).
        return _filter_kanban(results)
    except Exception:
        pass

    # Server filter raised an exception (unsupported param, network error, etc.) —
    # fall back to listing all views and filtering client-side.
    try:
        results = _fetch_views(service, search_filter=None)
        return _filter_kanban(results)
    except Exception:
        return []


def _fetch_views(service, search_filter=None):
    """
    Fetch dashboard views via splunklib, optionally filtered server-side.
    Returns a list of raw entry dicts (parsed from the response).
    """
    import json as _json

    # Build query params
    params = {'output_mode': 'json', 'count': '0'}
    if search_filter:
        params['search'] = search_filter

    # Use servicesNS with '-' owner and '-' app to search across all apps
    path = '/servicesNS/-/-/data/ui/views'
    response = service.get(path, **params)

    body = response.get('body', b'')
    if hasattr(body, 'read'):
        body = body.read()
    if isinstance(body, (bytes, bytearray)):
        body = body.decode('utf-8', errors='replace')

    parsed = _json.loads(body)
    return parsed.get('entry', [])


def _filter_kanban(entries):
    """
    Filter a list of raw entry dicts to those that contain KANBAN_VIZ_TYPE in
    their eai:data content. Return a list of normalised view dicts.
    """
    results = []
    for entry in entries:
        content = entry.get('content', {})
        eai_data = content.get('eai:data', '')
        if KANBAN_VIZ_TYPE not in (eai_data or ''):
            continue
        # Parse app and owner from the entry's acl block
        acl = entry.get('acl', {})
        results.append({
            'name':     entry.get('name', ''),
            'app':      acl.get('app', ''),
            'owner':    acl.get('owner', 'nobody'),
            'eai_data': eai_data,
            'updated':  entry.get('updated', ''),
        })
    return results


# ---------------------------------------------------------------------------
# get_view
# ---------------------------------------------------------------------------

def get_view(service, app, owner, name):
    """
    Fetch a single dashboard view by name and return a dict with keys
    {eai_data, updated}, or None if not found or on error.

    Uses the view's own app/owner for the servicesNS path.
    """
    import json as _json

    safe_owner = owner if owner else 'nobody'
    safe_app   = app   if app   else '-'

    try:
        path = '/servicesNS/{}/{}/data/ui/views/{}'.format(safe_owner, safe_app, name)
        response = service.get(path, output_mode='json')

        body = response.get('body', b'')
        if hasattr(body, 'read'):
            body = body.read()
        if isinstance(body, (bytes, bytearray)):
            body = body.decode('utf-8', errors='replace')

        parsed = _json.loads(body)
        entries = parsed.get('entry', [])
        if not entries:
            return None

        entry = entries[0]
        content = entry.get('content', {})
        return {
            'eai_data': content.get('eai:data', ''),
            'updated':  entry.get('updated', ''),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# save_view
# ---------------------------------------------------------------------------

def save_view(service, app, owner, name, xml):
    """
    POST updated eai:data XML back to Splunk for the named dashboard view.

    Uses the view's own app and owner for the servicesNS path so that
    permissions are respected. Raises on HTTP error.
    """
    # Normalise owner — 'nobody' is the standard shared-object owner
    safe_owner = owner if owner else 'nobody'
    safe_app   = app   if app   else '-'

    path = '/servicesNS/{}/{}/data/ui/views/{}'.format(safe_owner, safe_app, name)
    service.post(path, **{'eai:data': xml, 'output_mode': 'json'})
