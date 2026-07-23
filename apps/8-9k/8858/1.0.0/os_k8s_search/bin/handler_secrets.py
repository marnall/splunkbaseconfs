import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import k8s_search_lib as lib

class SecretsHandler(PersistentServerConnectionApplication):

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
    user = session.get('user', '')
    if not user:
        return lib.json_response(401, {'error': 'no authenticated user in session'})
    if method != 'GET':
        return lib.json_response(405, {'error': 'method not allowed'})
    ent = lib.entitlements()
    if ent.get('runtimeReason'):
        return lib.json_response(403, {'error': ent['runtimeReason']})
    caller_key = session.get('authtoken', '')
    system_key = request.get('system_authtoken', '')
    if not system_key:
        lib.log('secrets: passSystemAuth delivered no system token; falling back to the caller token (the read then requires the caller to hold list_storage_passwords). Check passSystemAuth in restmap.conf.')
        system_key = caller_key
    ref = _query_get(request, 'ref')
    if not ref:
        return lib.json_response(400, {'error': 'missing required query parameter: ref'})
    owner, err = _entitled_owner(ref, user)
    if err:
        return lib.json_response(403, {'error': err})
    if ref.split(':')[1].startswith('userauth__') and (not ent.get('allowPerUserTokens')):
        return lib.json_response(403, {'error': 'per-user credentials require a license; contact sales@outcoldsolutions.com'})
    gate_err = _impersonation_bearer_gate(ref, caller_key, system_key)
    if gate_err:
        return lib.json_response(403, {'error': gate_err})
    value = lib.secret_get(system_key, owner, ref)
    if value is None:
        return lib.json_response(404, {'error': 'secret not found'})
    return lib.json_response(200, {'value': value})
_IMPERSONATION_GATED_SUFFIXES = ('token', 'client_cert', 'client_key')

def _impersonation_bearer_gate(ref, caller_key, system_key):
    parts = ref.split(':')
    if len(parts) < 3 or parts[0] != lib.SECRET_REALM:
        return ''
    segments = parts[1].split('__')
    if len(segments) != 3 or segments[0] != 'cluster' or segments[2] not in _IMPERSONATION_GATED_SUFFIXES:
        return ''
    cluster_name = segments[1]
    content = lib.conf_get(system_key, 'nobody', 'kubeclusters', 'cluster.%s' % cluster_name)
    if not content or not lib.normalize_cluster_def(content).get('impersonate'):
        return ''
    if 'admin_all_objects' in lib.current_user_capabilities(caller_key):
        return ''
    return 'the default_auth credential of impersonation cluster %r is not directly readable; impersonation searches run server-side via /k8s_search/exec' % cluster_name

def _entitled_owner(ref, user):
    name = lib.secret_ref_to_name(ref)
    if name is None:
        return (None, 'malformed or foreign secret reference')
    kind = name.split('__')[0]
    if kind == 'userauth':
        parsed = lib.parse_userauth_name(name)
        if parsed is None:
            return (None, 'malformed per-user secret reference')
        _cluster, hexhash, _suffix = parsed
        if hexhash != lib.sha256_hex(user):
            return (None, 'not your secret')
        return ('nobody', None)
    if kind == 'cluster':
        return ('nobody', None)
    return (None, 'unrecognized secret reference')

def _query_get(request, key):
    q = request.get('query', [])
    if isinstance(q, dict):
        return q.get(key)
    if isinstance(q, list):
        for pair in q:
            if isinstance(pair, (list, tuple)) and len(pair) == 2 and (pair[0] == key):
                return pair[1]
    return None
