import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import splunk
import splunk.rest
import splunklib.client as client
from splunklib.binding import HTTPError
import _launcher
APP_NAME = 'os_k8s_search'
SECRET_REALM = APP_NAME
_USERAUTH_PREFIX = 'userauth'
_USERAUTH_HASH_LEN = 64
_USERAUTH_SUFFIXES = frozenset(['token', 'client_cert', 'client_key'])
_splunkd_endpoint_cache = None

def _splunkd_endpoint():
    global _splunkd_endpoint_cache
    if _splunkd_endpoint_cache is None:
        parsed = urllib.parse.urlparse(splunk.rest.makeSplunkdUri().rstrip('/'))
        _splunkd_endpoint_cache = (parsed.scheme or 'https', parsed.hostname or '127.0.0.1', parsed.port or 8089)
    return _splunkd_endpoint_cache

def _service(session_key, owner='nobody'):
    scheme, host, port = _splunkd_endpoint()
    return client.Service(scheme=scheme, host=host, port=port, token=session_key, owner=owner, app=APP_NAME, verify=False)

def conf_list(session_key, owner, conf):
    try:
        svc = _service(session_key, owner)
        conf_file = svc.confs[conf]
        out = []
        for stanza in conf_file.list():
            if stanza.name == 'default':
                continue
            out.append({'name': stanza.name, 'content': dict(stanza.content)})
        return out
    except KeyError:
        return []
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def conf_get(session_key, owner, conf, stanza):
    try:
        svc = _service(session_key, owner)
        return dict(svc.confs[conf][stanza].content)
    except KeyError:
        return None
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def conf_upsert(session_key, owner, conf, stanza, values):
    cleaned = {k: _stringify(v) for k, v in values.items() if v is not None}
    try:
        svc = _service(session_key, owner)
        try:
            conf_file = svc.confs[conf]
        except KeyError:
            conf_file = svc.confs.create(conf)
        try:
            existing = conf_file[stanza]
        except KeyError:
            new_stanza = conf_file.create(stanza)
            if cleaned:
                new_stanza.submit(cleaned)
            return
        existing.submit(cleaned)
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def conf_delete(session_key, owner, conf, stanza):
    try:
        svc = _service(session_key, owner)
        svc.confs[conf].delete(stanza)
        return True
    except KeyError:
        return False
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def _stringify(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)

def secret_name(parts):
    return '__'.join(parts)

def secret_full_id(name):
    return '%s:%s:' % (SECRET_REALM, name)

def sha256_hex(user):
    return hashlib.sha256(user.encode('utf-8')).hexdigest()

def userauth_secret_name(cluster, user, suffix):
    return secret_name([_USERAUTH_PREFIX, cluster, sha256_hex(user), suffix])

def secret_ref_to_name(full_ref):
    if not isinstance(full_ref, str):
        return None
    parts = full_ref.split(':')
    if len(parts) != 3 or parts[0] != SECRET_REALM or parts[2] != '':
        return None
    return parts[1] or None

def _is_lower_hex(s, length):
    return len(s) == length and all((c in '0123456789abcdef' for c in s))

def parse_userauth_name(name):
    if not isinstance(name, str):
        return None
    segments = name.split('__')
    if len(segments) != 4:
        return None
    prefix, cluster, hexhash, suffix = segments
    if prefix != _USERAUTH_PREFIX:
        return None
    if not cluster:
        return None
    if not _is_lower_hex(hexhash, _USERAUTH_HASH_LEN):
        return None
    if suffix not in _USERAUTH_SUFFIXES:
        return None
    return (cluster, hexhash, suffix)

def parse_userauth_ref(full_ref):
    name = secret_ref_to_name(full_ref)
    if name is None:
        return None
    return parse_userauth_name(name)

def secret_put(session_key, owner, name, value):
    try:
        svc = _service(session_key, owner)
        sp = svc.storage_passwords
        try:
            sp.delete(username=name, realm=SECRET_REALM)
        except KeyError:
            pass
        sp.create(password=value, username=name, realm=SECRET_REALM)
        return secret_full_id(name)
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def secret_delete(session_key, owner, name):
    try:
        svc = _service(session_key, owner)
        svc.storage_passwords.delete(username=name, realm=SECRET_REALM)
    except KeyError:
        pass
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def secret_get(session_key, owner, full_id):
    try:
        svc = _service(session_key, owner)
        return svc.storage_passwords[full_id].clear_password
    except KeyError:
        return None
    except HTTPError as e:
        raise _wrap_http_error(e) from e

def mark_app_configured(session_key):
    try:
        svc = _service(session_key, owner='nobody')
        svc.apps[APP_NAME].update(configured='1')
    except (HTTPError, KeyError) as exc:
        log('mark_app_configured: %s' % exc)

def validate_cluster(name, cluster, auth=None):
    try:
        binary = _launcher.binary_path('k8s_search')
    except _launcher.BinaryNotFoundError as exc:
        log('validation skipped: %s' % exc)
        return (True, '', False)
    except _launcher.UnsupportedPlatformError as exc:
        return (False, 'schema validator unavailable: %s' % exc, False)
    payload = {'name': name, 'cluster': cluster}
    if auth is not None:
        payload['auth'] = auth
    try:
        result = subprocess.run([binary, 'validate_cluster'], input=json.dumps(payload), capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return (False, 'schema validator did not run: %s' % exc, False)
    if result.returncode != 0:
        return (False, 'schema validator exited %d: %s' % (result.returncode, result.stderr.strip()), False)
    try:
        parsed = json.loads(result.stdout)
    except ValueError:
        return (False, 'schema validator produced invalid JSON: %s' % result.stdout, False)
    return (bool(parsed.get('ok')), str(parsed.get('error', '')), bool(parsed.get('unsupported', False)))
_LICENSE_UNAVAILABLE = {'valid': False, 'reason': 'license status unavailable', 'paid': False, 'maxClusters': 1, 'maxInstallations': 1, 'expired': False, 'inGrace': False, 'allowShc': False, 'allowPerUserTokens': False, 'allowImpersonation': False, 'runtimeReason': 'Kubernetes Search license status is unavailable'}

def entitlements():
    try:
        binary = _launcher.binary_path('k8s_search')
    except (_launcher.BinaryNotFoundError, _launcher.UnsupportedPlatformError) as exc:
        log('license check skipped (%s); treating as unavailable' % exc)
        return dict(_LICENSE_UNAVAILABLE)
    try:
        result = subprocess.run([binary, 'license'], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        log('license check did not run (%s); treating as unavailable' % exc)
        return dict(_LICENSE_UNAVAILABLE)
    try:
        return json.loads(result.stdout)
    except ValueError:
        log('license check produced invalid JSON; treating as unavailable')
        return dict(_LICENSE_UNAVAILABLE)

def count_clusters(read_key):
    stanzas = conf_list(read_key, 'nobody', 'kubeclusters')
    return sum((1 for e in stanzas if e['name'].startswith('cluster.')))
CLUSTER_EDIT_CAPS = frozenset(['edit_k8s_search_clusters', 'admin_all_objects'])

def current_user_capabilities(session_key):
    if not session_key:
        return set()
    try:
        svc = _service(session_key)
        response = svc.get('/services/authentication/current-context', output_mode='json')
        body = response.body.read()
        parsed = json.loads(body) if body else {}
        for entry in parsed.get('entry', []):
            return set(entry.get('content', {}).get('capabilities', []))
    except Exception:
        pass
    return set()

def can_edit_clusters(session_key):
    return bool(current_user_capabilities(session_key) & CLUSTER_EDIT_CAPS)

def normalize_cluster_def(d):
    out = dict(d or {})
    for key in ('insecure', 'impersonate'):
        v = out.get(key)
        if isinstance(v, str):
            out[key] = v.strip().lower() in ('true', '1', 'yes')
    return out

def json_response(status, payload):
    return {'payload': json.dumps(payload), 'status': status}

def parse_json_body(request):
    payload = request.get('payload', '')
    if payload:
        try:
            return (json.loads(payload), None)
        except ValueError as exc:
            return (None, 'request body is not valid JSON: %s' % exc)
    form = request.get('form', {})
    if isinstance(form, list):
        form = {k: v for k, v in form}
    if form:
        return (form, None)
    return ({}, None)

def path_tail(request, prefix):
    path = request.get('path_info', '') or request.get('path', '')
    if path.startswith(prefix):
        path = path[len(prefix):]
    return path.lstrip('/')

class _SplunkdError(Exception):

    def __init__(self, status, body):
        super().__init__('splunkd returned %s: %s' % (status, str(body)[:512]))
        self.status = int(status)
        self.body = str(body)

def _wrap_http_error(err):
    raw = err.body
    body = None
    if isinstance(raw, (str, bytes)):
        body = raw
    elif hasattr(raw, 'read'):
        try:
            body = raw.read()
        except Exception:
            body = None
    if body is None:
        body = str(err)
    if isinstance(body, bytes):
        body = body.decode('utf-8', errors='replace')
    return _SplunkdError(err.status, body)

def splunkd_error_response(exc):
    if isinstance(exc, _SplunkdError):
        return json_response(int(exc.status), {'error': str(exc.body)})
    raise exc

def log(message):
    sys.stderr.write('k8s_search_lib: %s\n' % message)
