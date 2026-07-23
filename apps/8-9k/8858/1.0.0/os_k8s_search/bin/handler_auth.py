import base64
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import k8s_search_lib as lib
_MATCH_PREFIX = '/k8s_search/auth'
_AUTH_KEYS = ('type', 'token_ref', 'client_cert_ref', 'client_key_ref')

class AuthHandler(PersistentServerConnectionApplication):

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
    user = session.get('user', '')
    if not user:
        return lib.json_response(401, {'error': 'no authenticated user in session'})
    write_key = request.get('system_authtoken', '')
    if not write_key:
        lib.log('auth: passSystemAuth delivered no system token; falling back to the caller token for writes (which then requires a storage/passwords edit capability). Check passSystemAuth in restmap.conf.')
        write_key = session_key
    tail = lib.path_tail(request, _MATCH_PREFIX)
    parts = [p for p in tail.split('/') if p]
    if len(parts) > 1:
        return lib.json_response(404, {'error': 'not found'})
    cluster = parts[0] if parts else ''
    if not cluster:
        if method == 'GET':
            return _list_user_auth(session_key, user)
        return lib.json_response(405, {'error': 'method not allowed'})
    if method == 'GET':
        return _get_user_auth(session_key, user, cluster)
    if method == 'PUT':
        return _put_user_auth(session_key, write_key, user, cluster, request)
    if method == 'DELETE':
        return _delete_user_auth(write_key, user, cluster)
    return lib.json_response(405, {'error': 'method not allowed'})

def _list_user_auth(session_key, user):
    stanzas = lib.conf_list(session_key, user, 'kubeauth')
    out = []
    for entry in stanzas:
        name = entry['name']
        if not name.startswith('auth.'):
            continue
        cluster = name[len('auth.'):]
        out.append({'cluster': cluster, **_filtered(entry['content'], _AUTH_KEYS)})
    return lib.json_response(200, {'auth': out})

def _get_user_auth(session_key, user, cluster):
    content = lib.conf_get(session_key, user, 'kubeauth', 'auth.%s' % cluster)
    if content is None:
        return lib.json_response(404, {'error': 'no override for cluster %r' % cluster})
    return lib.json_response(200, {'cluster': cluster, **_filtered(content, _AUTH_KEYS)})

def _put_user_auth(session_key, write_key, user, cluster, request):
    if not lib.entitlements()['allowPerUserTokens']:
        return lib.json_response(403, {'error': 'per-user credentials require a license; contact sales@outcoldsolutions.com'})
    cluster_def = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % cluster)
    if cluster_def is None:
        return lib.json_response(404, {'error': 'cluster %r is not in the system registry' % cluster})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    cluster_for_validate = lib.normalize_cluster_def({k: cluster_def[k] for k in ('server', 'ca_data_ref', 'ca_path', 'insecure', 'tls_server_name', 'namespace') if k in cluster_def})
    auth_for_validate = _filtered(body, _AUTH_KEYS)
    for raw, ref in (('token', 'token_ref'), ('client_cert', 'client_cert_ref'), ('client_key', 'client_key_ref')):
        if body.get(raw):
            auth_for_validate[ref] = 'pending'
    ok, message, unsupported = lib.validate_cluster(cluster, cluster_for_validate, auth_for_validate)
    if not ok:
        return lib.json_response(400, {'error': message, 'unsupported': unsupported})
    auth = _stash_auth_secrets(write_key, user, cluster, body)
    lib.conf_upsert(write_key, user, 'kubeauth', 'auth.%s' % cluster, auth)
    return lib.json_response(200, {'cluster': cluster, **auth})

def _predictable_userauth_names(user, cluster):
    return [lib.userauth_secret_name(cluster, user, suffix) for suffix in ('token', 'client_cert', 'client_key')]

def _delete_user_auth(write_key, user, cluster):
    stanza = lib.conf_get(write_key, user, 'kubeauth', 'auth.%s' % cluster) or {}
    user_hash = lib.sha256_hex(user)
    candidates = set(_predictable_userauth_names(user, cluster))
    for key in ('token_ref', 'client_cert_ref', 'client_key_ref'):
        ref = stanza.get(key)
        if ref:
            name = lib.secret_ref_to_name(ref)
            if name is not None:
                candidates.add(name)
    for name in candidates:
        parsed = lib.parse_userauth_name(name)
        if parsed is None:
            continue
        parsed_cluster, parsed_hash, _suffix = parsed
        if parsed_hash != user_hash or parsed_cluster != cluster:
            continue
        lib.secret_delete(write_key, 'nobody', name)
    existed = lib.conf_delete(write_key, user, 'kubeauth', 'auth.%s' % cluster)
    if not existed:
        return lib.json_response(404, {'error': 'no override for cluster %r' % cluster})
    return lib.json_response(200, {'deleted_for_cluster': cluster})

def _stash_auth_secrets(write_key, user, cluster, body):
    auth = _filtered(body, _AUTH_KEYS)
    if body.get('token'):
        ref_name = lib.userauth_secret_name(cluster, user, 'token')
        auth['token_ref'] = lib.secret_put(write_key, 'nobody', ref_name, body['token'])
    if body.get('client_cert'):
        ref_name = lib.userauth_secret_name(cluster, user, 'client_cert')
        encoded = base64.b64encode(body['client_cert'].encode('utf-8')).decode('ascii')
        auth['client_cert_ref'] = lib.secret_put(write_key, 'nobody', ref_name, encoded)
    if body.get('client_key'):
        ref_name = lib.userauth_secret_name(cluster, user, 'client_key')
        encoded = base64.b64encode(body['client_key'].encode('utf-8')).decode('ascii')
        auth['client_key_ref'] = lib.secret_put(write_key, 'nobody', ref_name, encoded)
    return auth

def _filtered(d, allowed):
    return {k: d[k] for k in allowed if k in d}
