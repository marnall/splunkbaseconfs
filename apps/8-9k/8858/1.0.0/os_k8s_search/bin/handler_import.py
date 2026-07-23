import json as json_module
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import yaml
import k8s_search_lib as lib
_MATCH_PREFIX = '/k8s_search/import'

class ImportHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            return _dispatch(in_string)
        except lib._SplunkdError as exc:
            return lib.splunkd_error_response(exc)

def _dispatch(in_string):
    request = json_module.loads(in_string)
    method = request.get('method', 'GET').upper()
    session = request.get('session', {}) or {}
    session_key = session.get('authtoken', '')
    write_key = request.get('system_authtoken', '')
    if not write_key:
        lib.log('import: passSystemAuth delivered no system token; falling back to the caller token for writes (which then requires storage/passwords + kubeclusters.conf write capabilities). Check passSystemAuth in restmap.conf.')
        write_key = session_key
    if method != 'POST':
        return lib.json_response(405, {'error': 'method not allowed'})
    if not lib.can_edit_clusters(session_key):
        return lib.json_response(403, {'error': 'the edit_k8s_search_clusters capability is required to import kubeconfig'})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    kubeconfig = body.get('kubeconfig')
    if kubeconfig is None:
        return lib.json_response(400, {'error': 'missing required field: kubeconfig'})
    if isinstance(kubeconfig, str):
        try:
            kubeconfig = yaml.safe_load(kubeconfig)
        except yaml.YAMLError as exc:
            return lib.json_response(400, {'error': 'kubeconfig is not valid YAML or JSON: %s' % exc})
    if not isinstance(kubeconfig, dict):
        return lib.json_response(400, {'error': 'kubeconfig must be a mapping at the top level'})
    return _do_import(write_key, kubeconfig, body.get('context', ''), body.get('rename_to', ''))

def _do_import(write_key, kubeconfig, context_arg, rename_to):
    contexts = {c.get('name'): c.get('context', {}) for c in kubeconfig.get('contexts', []) or []}
    clusters = {c.get('name'): c.get('cluster', {}) for c in kubeconfig.get('clusters', []) or []}
    users = {u.get('name'): u.get('user', {}) for u in kubeconfig.get('users', []) or []}
    context_name = context_arg or kubeconfig.get('current-context', '')
    if not context_name:
        return lib.json_response(400, {'error': 'kubeconfig has no current-context and no `context` was provided'})
    ctx = contexts.get(context_name)
    if ctx is None:
        return lib.json_response(400, {'error': 'context %r is not in the kubeconfig' % context_name})
    cluster_kc_name = ctx.get('cluster', '')
    user_kc_name = ctx.get('user', '')
    cluster_kc = clusters.get(cluster_kc_name)
    user_kc = users.get(user_kc_name)
    if cluster_kc is None:
        return lib.json_response(400, {'error': 'context %r references unknown cluster %r' % (context_name, cluster_kc_name)})
    target_name = (rename_to or cluster_kc_name).lower()
    if not target_name:
        return lib.json_response(400, {'error': 'cluster has no name (use rename_to=)'})
    if lib.conf_get(write_key, 'nobody', 'kubeclusters', 'cluster.%s' % target_name) is None:
        ent = lib.entitlements()
        current = lib.count_clusters(write_key)
        if current >= ent['maxClusters']:
            return lib.json_response(403, {'error': 'your license allows %d cluster(s) and %d are already registered; contact sales@outcoldsolutions.com to add more' % (ent['maxClusters'], current)})
    cluster_def, ca_data = _build_cluster_def(cluster_kc)
    try:
        auth_def, secrets = _build_auth_def(user_kc) if user_kc else (None, {})
    except _ImportError as exc:
        return lib.json_response(400, {'error': str(exc)})
    cluster_validate = dict(cluster_def)
    auth_validate = dict(auth_def) if auth_def else None
    if ca_data:
        cluster_validate['ca_data_ref'] = 'pending'
    for kind in secrets:
        if auth_validate is not None:
            auth_validate[kind + '_ref'] = 'pending'
    ok, message, unsupported = lib.validate_cluster(target_name, cluster_validate, auth_validate)
    if not ok:
        return lib.json_response(400, {'error': message, 'unsupported': unsupported})
    if ca_data:
        ref_name = lib.secret_name(['cluster', target_name, 'ca'])
        cluster_def['ca_data_ref'] = lib.secret_put(write_key, 'nobody', ref_name, ca_data)
    for kind, value in secrets.items():
        ref_name = lib.secret_name(['cluster', target_name, kind])
        full = lib.secret_put(write_key, 'nobody', ref_name, value)
        auth_def[kind + '_ref'] = full
    lib.conf_upsert(write_key, 'nobody', 'kubeclusters', 'cluster.%s' % target_name, cluster_def)
    if auth_def is not None:
        lib.conf_upsert(write_key, 'nobody', 'kubeclusters', 'default_auth.%s' % target_name, auth_def)
    lib.mark_app_configured(write_key)
    return lib.json_response(200, {'imported': target_name, 'context': context_name, 'cluster': cluster_def, 'default_auth': auth_def or {}})

def _build_cluster_def(cluster_kc):
    out = {'server': cluster_kc.get('server', '')}
    if cluster_kc.get('insecure-skip-tls-verify'):
        out['insecure'] = True
    if cluster_kc.get('tls-server-name'):
        out['tls_server_name'] = cluster_kc['tls-server-name']
    ca_data = ''
    if cluster_kc.get('certificate-authority-data'):
        ca_data = cluster_kc['certificate-authority-data']
    elif cluster_kc.get('certificate-authority'):
        out['ca_path'] = cluster_kc['certificate-authority']
    return (out, ca_data)

def _build_auth_def(user_kc):
    if 'exec' in user_kc:
        raise _ImportError('kubeconfig uses an exec plugin (e.g. aws-iam-authenticator). Run the plugin manually and paste the bearer token it returns into the setup page instead.')
    auth = {}
    secrets = {}
    if user_kc.get('token'):
        auth['type'] = 'token'
        secrets['token'] = user_kc['token']
        return (auth, secrets)
    if user_kc.get('tokenFile'):
        raise _ImportError("user-auth uses `tokenFile` (an operator-supplied path the search head would read). For security, import does not open arbitrary paths — open the file yourself and paste the bearer token text into the kubeconfig's `token:` field, then re-import.")
    cert = user_kc.get('client-certificate-data')
    key = user_kc.get('client-key-data')
    if cert and key:
        auth['type'] = 'cert'
        secrets['client_cert'] = cert
        secrets['client_key'] = key
        return (auth, secrets)
    if user_kc.get('client-certificate') or user_kc.get('client-key'):
        raise _ImportError('user-auth uses `client-certificate`/`client-key` file paths (which the search head would read). For security, import does not open arbitrary paths — inline the PEMs as `client-certificate-data` / `client-key-data` (e.g. `base64 -w0 client.crt`) and re-import.')
    raise _ImportError('user has no recognized credentials (need a token, or client-certificate-data + client-key-data)')

class _ImportError(Exception):
    pass
