import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import k8s_search_lib as lib
_CACHE_KEYS = ('enabled', 'dir', 'discovery_ttl', 'list_default_ttl', 'get_default_ttl', 'max_size_bytes', 'max_entries')

class SettingsHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            return _dispatch(in_string)
        except lib._SplunkdError as exc:
            return lib.splunkd_error_response(exc)

def _dispatch(in_string):
    request = json.loads(in_string)
    method = request.get('method', 'GET').upper()
    session = request.get('session', {}) or {}
    session_key = session.get('authtoken', '')
    write_key = request.get('system_authtoken', '')
    if not write_key:
        lib.log('settings: passSystemAuth delivered no system token; falling back to the caller token for writes (which then requires k8s_search.conf write capability). Check passSystemAuth in restmap.conf.')
        write_key = session_key
    if method == 'GET':
        return _get(write_key)
    if method == 'PUT':
        return _put(session_key, write_key, request)
    return lib.json_response(405, {'error': 'method not allowed'})

def _get(read_key):
    cache_stanza = lib.conf_get(read_key, 'nobody', 'k8s_search', 'cache') or {}
    out = {k: cache_stanza[k] for k in _CACHE_KEYS if k in cache_stanza}
    return lib.json_response(200, {'cache': out, 'license': _license_status()})

def _license_status():
    ent = lib.entitlements()
    return {'valid': ent.get('valid', False), 'reason': ent.get('reason', ''), 'paid': ent.get('paid', False), 'license_id': ent.get('licenseId', ''), 'max_clusters': ent.get('maxClusters', 1), 'max_installations': ent.get('maxInstallations', 1), 'expiration': ent.get('expiration', 0), 'expired': ent.get('expired', False), 'in_grace': ent.get('inGrace', False), 'allow_per_user_tokens': ent.get('allowPerUserTokens', False)}

def _put(session_key, write_key, request):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to change settings'})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    if body is None:
        body = {}
    wrote = False
    cache_in = body.get('cache') or {}
    if cache_in:
        if not isinstance(cache_in, dict):
            return lib.json_response(400, {'error': "request body's `cache` field must be an object"})
        values = {k: cache_in[k] for k in _CACHE_KEYS if k in cache_in}
        if not values:
            return lib.json_response(400, {'error': 'no recognized [cache] keys in request body'})
        lib.conf_upsert(write_key, 'nobody', 'k8s_search', 'cache', values)
        wrote = True
    license_in = body.get('license')
    if license_in is not None:
        if not isinstance(license_in, dict) or 'key' not in license_in:
            return lib.json_response(400, {'error': "request body's `license` field must be an object with a `key`"})
        lib.conf_upsert(write_key, 'nobody', 'k8s_search', 'license', {'key': str(license_in['key']).strip()})
        wrote = True
    if not wrote:
        return lib.json_response(400, {'error': 'request body must contain a `cache` and/or `license` object'})
    return lib.json_response(200, {'status': 'ok', 'license': _license_status()})
