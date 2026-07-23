import base64
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import k8s_search_lib as lib
_MATCH_PREFIX = '/k8s_search/clusters'
_CLUSTER_KEYS = ('server', 'ca_data_ref', 'ca_path', 'insecure', 'tls_server_name', 'namespace', 'impersonate')
_AUTH_KEYS = ('type', 'token_ref', 'client_cert_ref', 'client_key_ref')

class ClustersHandler(PersistentServerConnectionApplication):

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
        lib.log('clusters: passSystemAuth delivered no system token; falling back to the caller token for writes (which then requires storage/passwords + kubeclusters.conf write capabilities). Check passSystemAuth in restmap.conf.')
        write_key = session_key
    tail = lib.path_tail(request, _MATCH_PREFIX)
    parts = [p for p in tail.split('/') if p]
    if len(parts) > 2 or (len(parts) == 2 and parts[1] != 'auth'):
        return lib.json_response(404, {'error': 'not found'})
    name = parts[0] if parts else ''
    subresource = parts[1] if len(parts) == 2 else ''
    if subresource == 'auth':
        return _dispatch_auth(method, session_key, write_key, name, request)
    return _dispatch_cluster(method, session_key, write_key, name, request)

def _dispatch_cluster(method, session_key, write_key, name, request):
    if not name:
        if method == 'GET':
            return _list_clusters(session_key)
        if method == 'POST':
            return _create_cluster(session_key, write_key, request)
        return lib.json_response(405, {'error': 'method not allowed'})
    if method == 'GET':
        return _get_cluster(session_key, name)
    if method == 'PUT':
        return _update_cluster(session_key, write_key, name, request)
    if method == 'DELETE':
        return _delete_cluster(session_key, write_key, name)
    return lib.json_response(405, {'error': 'method not allowed'})

def _list_clusters(session_key):
    stanzas = lib.conf_list(session_key, 'nobody', 'kubeclusters')
    out = []
    for entry in stanzas:
        name, kind = _parse_stanza_name(entry['name'])
        if kind != 'cluster':
            continue
        out.append({'name': name, **_filtered(entry['content'], _CLUSTER_KEYS)})
    return lib.json_response(200, {'clusters': out})

def _get_cluster(session_key, name):
    content = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % name)
    if content is None:
        return lib.json_response(404, {'error': 'cluster %r not found' % name})
    return lib.json_response(200, {'name': name, **_filtered(content, _CLUSTER_KEYS)})

def _create_cluster(session_key, write_key, request):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to create clusters'})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    name = (body.get('name') or '').strip()
    if not name:
        return lib.json_response(400, {'error': 'missing required field: name'})
    existing = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % name)
    if existing is not None:
        return lib.json_response(409, {'error': 'cluster %r already exists; use PUT to update' % name})
    ent = lib.entitlements()
    current = lib.count_clusters(write_key)
    if current >= ent['maxClusters']:
        return lib.json_response(403, {'error': 'your license allows %d cluster(s) and %d are already registered; contact sales@outcoldsolutions.com to add more' % (ent['maxClusters'], current)})
    return _save_cluster(session_key, write_key, name, body, ent=ent)

def _update_cluster(session_key, write_key, name, request):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to update clusters'})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    return _save_cluster(session_key, write_key, name, body)

def _save_cluster(session_key, write_key, name, body, ent=None):
    cluster = _filtered(body, _CLUSTER_KEYS)
    ca_data = body.get('ca_data', '')
    if ca_data:
        cluster['ca_path'] = ''
    existing = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % name) or {}
    effective = _filtered(existing, _CLUSTER_KEYS)
    effective.update(cluster)
    if ent is None:
        ent = lib.entitlements()
    if not ent['allowImpersonation'] and lib.normalize_cluster_def(effective).get('impersonate'):
        return lib.json_response(403, {'error': 'impersonation clusters require a license; contact sales@outcoldsolutions.com'})
    if ca_data:
        effective['ca_data_ref'] = 'pending'
    ok, message, _ = lib.validate_cluster(name, effective)
    if not ok:
        return lib.json_response(400, {'error': message})
    if ca_data:
        ref_name = lib.secret_name(['cluster', name, 'ca'])
        encoded = base64.b64encode(ca_data.encode('utf-8')).decode('ascii')
        cluster['ca_data_ref'] = lib.secret_put(write_key, 'nobody', ref_name, encoded)
    lib.conf_upsert(write_key, 'nobody', 'kubeclusters', 'cluster.%s' % name, cluster)
    lib.mark_app_configured(write_key)
    return lib.json_response(200, {'name': name, **cluster})

def _ref_to_secret_name(ref):
    return ref.split(':')[1] if ':' in ref else ref

def _delete_auth_secrets(write_key, name, auth_stanza):
    targets = set()
    for key in ('token_ref', 'client_cert_ref', 'client_key_ref'):
        ref = (auth_stanza or {}).get(key)
        if ref:
            targets.add(_ref_to_secret_name(ref))
    for suffix in ('token', 'client_cert', 'client_key'):
        targets.add(lib.secret_name(['cluster', name, suffix]))
    for secret in targets:
        lib.secret_delete(write_key, 'nobody', secret)

def _delete_cluster(session_key, write_key, name):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to delete clusters'})
    auth_stanza = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name)
    _delete_auth_secrets(write_key, name, auth_stanza)
    cluster_stanza = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % name) or {}
    ca_targets = {lib.secret_name(['cluster', name, 'ca'])}
    ca_ref = cluster_stanza.get('ca_data_ref')
    if ca_ref:
        ca_targets.add(_ref_to_secret_name(ca_ref))
    for secret in ca_targets:
        lib.secret_delete(write_key, 'nobody', secret)
    lib.conf_delete(write_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name)
    existed = lib.conf_delete(write_key, 'nobody', 'kubeclusters', 'cluster.%s' % name)
    if not existed:
        return lib.json_response(404, {'error': 'cluster %r not found' % name})
    return lib.json_response(200, {'deleted': name})

def _dispatch_auth(method, session_key, write_key, name, request):
    if not name:
        return lib.json_response(404, {'error': 'not found'})
    if method == 'GET':
        return _get_default_auth(session_key, name)
    if method == 'PUT':
        return _put_default_auth(session_key, write_key, name, request)
    if method == 'DELETE':
        return _delete_default_auth(session_key, write_key, name)
    return lib.json_response(405, {'error': 'method not allowed'})

def _get_default_auth(session_key, name):
    content = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name)
    if content is None:
        return lib.json_response(404, {'error': 'no default_auth for cluster %r' % name})
    return lib.json_response(200, {'cluster': name, **_filtered(content, _AUTH_KEYS)})

def _put_default_auth(session_key, write_key, name, request):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to set default_auth'})
    cluster_exists = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'cluster.%s' % name)
    if cluster_exists is None:
        return lib.json_response(404, {'error': 'cluster %r not found' % name})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    auth = _stash_auth_secrets(write_key, 'nobody', ['cluster', name], body)
    ok, message, unsupported = lib.validate_cluster(name, _filtered(cluster_exists, _CLUSTER_KEYS), auth)
    if not ok:
        return lib.json_response(400, {'error': message, 'unsupported': unsupported})
    lib.conf_upsert(write_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name, auth)
    return lib.json_response(200, {'cluster': name, **auth})

def _delete_default_auth(session_key, write_key, name):
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to delete default_auth'})
    stanza = lib.conf_get(session_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name)
    _delete_auth_secrets(write_key, name, stanza)
    existed = lib.conf_delete(write_key, 'nobody', 'kubeclusters', 'default_auth.%s' % name)
    if not existed:
        return lib.json_response(404, {'error': 'no default_auth for cluster %r' % name})
    return lib.json_response(200, {'deleted_default_auth_for': name})

def _stash_auth_secrets(write_key, owner, name_prefix, body):
    auth = _filtered(body, _AUTH_KEYS)
    if body.get('token'):
        ref_name = lib.secret_name(name_prefix + ['token'])
        auth['token_ref'] = lib.secret_put(write_key, owner, ref_name, body['token'])
    if body.get('client_cert'):
        ref_name = lib.secret_name(name_prefix + ['client_cert'])
        encoded = base64.b64encode(body['client_cert'].encode('utf-8')).decode('ascii')
        auth['client_cert_ref'] = lib.secret_put(write_key, owner, ref_name, encoded)
    if body.get('client_key'):
        ref_name = lib.secret_name(name_prefix + ['client_key'])
        encoded = base64.b64encode(body['client_key'].encode('utf-8')).decode('ascii')
        auth['client_key_ref'] = lib.secret_put(write_key, owner, ref_name, encoded)
    return auth

def _filtered(d, allowed):
    out = {k: d[k] for k in allowed if k in d}
    return lib.normalize_cluster_def(out)

def _parse_stanza_name(raw):
    if '.' not in raw:
        return ('', '')
    kind, _, name = raw.partition('.')
    return (name, kind)
