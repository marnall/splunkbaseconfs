import json
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import k8s_search_lib as lib
import _launcher
_EXEC_TIMEOUT_SECONDS = 300
_COMMANDS = ('get', 'logs', 'events', 'describe')

class ExecHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            return _dispatch(in_string)
        except lib._SplunkdError as exc:
            return lib.splunkd_error_response(exc)

def _dispatch(in_string):
    request = json.loads(in_string)
    method = request.get('method', 'POST').upper()
    session = request.get('session', {}) or {}
    user = session.get('user', '')
    system_key = request.get('system_authtoken', '')
    if not user:
        return lib.json_response(401, {'error': 'no authenticated user in session'})
    if not system_key:
        return lib.json_response(500, {'error': 'system auth token unavailable (passSystemAuth not effective)'})
    if method != 'POST':
        return lib.json_response(405, {'error': 'method not allowed'})
    body, err = lib.parse_json_body(request)
    if err:
        return lib.json_response(400, {'error': err})
    command = body.get('command', '')
    if command not in _COMMANDS:
        return lib.json_response(400, {'error': 'unknown or missing command (expected one of %s)' % ', '.join(_COMMANDS)})
    ent = lib.entitlements()
    if ent.get('runtimeReason'):
        return lib.json_response(403, {'error': ent['runtimeReason']})
    try:
        binary = _launcher.binary_path('k8s_search')
    except _launcher.BinaryNotFoundError as exc:
        return lib.json_response(500, {'error': 'k8s_search binary not found: %s' % exc})
    except _launcher.UnsupportedPlatformError as exc:
        return lib.json_response(500, {'error': 'unsupported platform: %s' % exc})
    cluster = body.get('context', '')
    cluster_def = lib.conf_get(system_key, 'nobody', 'kubeclusters', 'cluster.%s' % cluster)
    if cluster_def is None:
        return lib.json_response(404, {'error': 'cluster %r is not configured' % cluster})
    if not lib.normalize_cluster_def(cluster_def).get('impersonate'):
        return lib.json_response(403, {'error': 'the exec endpoint serves impersonation clusters only; cluster %r is not impersonate=true' % cluster})
    if not ent.get('allowImpersonation'):
        return lib.json_response(403, {'error': 'impersonation requires a license; contact sales@outcoldsolutions.com'})
    params = body.get('params') or {}
    if params.get('server'):
        return lib.json_response(400, {'error': 'server= is not an accepted parameter (it could redirect the impersonation bearer)'})
    if str(params.get('insecure', '')).strip().lower() == 'true':
        return lib.json_response(400, {'error': 'insecure= is not an accepted parameter for impersonation clusters'})
    try:
        secrets = _resolve_secrets(system_key, cluster, cluster_def)
    except lib._SplunkdError as exc:
        return lib.splunkd_error_response(exc)
    payload = {'command': command, 'params': body.get('params') or {}, 'context': cluster, 'dispatch_dir': body.get('dispatch_dir', ''), 'earliest_time': body.get('earliest_time', 0), 'impersonate_user': user, 'secrets': secrets}
    try:
        result = subprocess.run([binary, 'exec'], input=json.dumps(payload), capture_output=True, text=True, timeout=_EXEC_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return lib.json_response(504, {'error': 'server-side exec timed out after %ds' % _EXEC_TIMEOUT_SECONDS})
    except (OSError, subprocess.SubprocessError) as exc:
        return lib.json_response(502, {'error': 'server-side exec did not run: %s' % exc})
    if result.returncode != 0:
        detail = result.stderr.strip() or 'exit %d' % result.returncode
        return lib.json_response(502, {'error': 'server-side exec failed: %s' % detail})
    return {'payload': result.stdout, 'status': 200}

def _resolve_secrets(system_key, cluster, cluster_def):
    out = {}
    da = lib.conf_get(system_key, 'nobody', 'kubeclusters', 'default_auth.%s' % cluster) or {}
    refs = []
    if cluster_def.get('ca_data_ref'):
        refs.append(cluster_def['ca_data_ref'])
    for key in ('token_ref', 'client_cert_ref', 'client_key_ref'):
        if da.get(key):
            refs.append(da[key])
    for ref in refs:
        value = lib.secret_get(system_key, 'nobody', ref)
        if value is not None:
            out[ref] = value
    return out
