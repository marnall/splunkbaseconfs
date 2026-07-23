import os
import sys
import json
import configparser
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import tarfile
import tempfile

import glob; _py_libs = glob.glob(os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "lib", "python3*", "site-packages")); [sys.path.insert(0, p) for p in _py_libs if p not in sys.path]
import splunk.rest

DEPLOYMENT_APPS_DIR = '/opt/splunk/etc/deployment-apps'
SPLUNKBASE_SEARCH_API  = 'https://splunkbase.splunk.com/api/v1/app/?product=splunk&limit=1&offset=0&appid={}'
SPLUNKBASE_RELEASE_API = 'https://splunkbase.splunk.com/api/v1/app/{}/release/?limit=1'
SPLUNKBASE_DOWNLOAD_URL = 'https://splunkbase.splunk.com/app/{}/release/{}/download/'
SPLUNKBASE_LOGIN_URL   = 'https://splunkbase.splunk.com/api/account:login/'
CRED_REALM = 'SA-deployment-manager'
CRED_NAME  = 'splunkbase'


# ── REST handlers ─────────────────────────────────────────────────────────────

class DeploymentManagerHandler(splunk.rest.BaseRestHandler):

    def handle_GET(self):
        apps = _scan_apps()
        self._json({'apps': apps})

    def handle_POST(self):
        uid     = self.args.get('uid', '').strip()
        version = self.args.get('version', '').strip()
        app_id  = self.args.get('app_id', '').strip()

        if not (uid and version and app_id):
            self._error(400, 'uid, version, and app_id are required')
            return

        try:
            username, password = _get_credentials(self.sessionKey)
        except Exception:
            self._error(401, 'Splunkbase credentials not set. Configure them in the Settings tab.')
            return

        try:
            _download_and_install(uid, version, app_id, username, password)
            self._json({'success': True, 'message': f'{app_id} {version} installed successfully'})
        except Exception as e:
            self._error(500, str(e))

    def _json(self, data):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))

    def _error(self, code, msg):
        self.response.setStatus(code)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps({'error': msg}))


class CredentialsHandler(splunk.rest.BaseRestHandler):

    def handle_GET(self):
        try:
            username, _ = _get_credentials(self.sessionKey)
            self._json({'configured': True, 'username': username})
        except Exception:
            self._json({'configured': False, 'username': ''})

    def handle_POST(self):
        username = self.args.get('username', '').strip()
        password = self.args.get('password', '').strip()
        if not username or not password:
            self._error(400, 'Username and password are required')
            return
        try:
            _store_credentials(self.sessionKey, username, password)
            self._json({'success': True})
        except Exception as e:
            self._error(500, str(e))

    def handle_DELETE(self):
        try:
            splunk.rest.simpleRequest(
                f'/services/storage/passwords/{CRED_REALM}:{CRED_NAME}:',
                sessionKey=self.sessionKey,
                method='DELETE',
                raiseAllErrors=True
            )
            self._json({'success': True})
        except Exception as e:
            self._error(500, str(e))

    def _json(self, data):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))

    def _error(self, code, msg):
        self.response.setStatus(code)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps({'error': msg}))


# ── app scanning ──────────────────────────────────────────────────────────────

def _scan_apps():
    try:
        entries = sorted(os.listdir(DEPLOYMENT_APPS_DIR))
    except FileNotFoundError:
        return []

    results = []
    for entry in entries:
        if not os.path.isdir(os.path.join(DEPLOYMENT_APPS_DIR, entry)):
            continue

        conf    = _read_app_conf(os.path.join(DEPLOYMENT_APPS_DIR, entry))
        label   = conf.get('label',   'N/A') if conf else 'N/A'
        version = conf.get('version', 'N/A') if conf else 'N/A'
        build   = conf.get('build',   'N/A') if conf else 'N/A'
        app_id  = conf.get('app_id')         if conf else None

        if app_id and version != 'N/A':
            latest, uid, dl_url = _get_splunkbase_info(app_id)
            is_valid = latest not in ('N/A', 'Error') and not str(latest).startswith('HTTP')
            update_available = _version_gt(latest, version) if is_valid else False
        else:
            latest, uid, dl_url, update_available = 'N/A', None, None, False

        results.append({
            'folder':           entry,
            'label':            label,
            'version':          version,
            'build':            build,
            'app_id':           app_id,
            'latest_version':   latest,
            'uid':              uid,
            'download_url':     dl_url,
            'update_available': update_available,
            'has_conf':         conf is not None,
        })

    return results


def _read_app_conf(app_dir):
    conf_path = os.path.join(app_dir, 'default', 'app.conf')
    if not os.path.exists(conf_path):
        return None
    config = configparser.RawConfigParser()
    config.read(conf_path)
    def get(section, key):
        try:
            return config.get(section, key).strip()
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
    return {
        'label':   get('ui', 'label')        or 'N/A',
        'version': get('launcher', 'version') or 'N/A',
        'build':   get('package', 'build')    or 'N/A',
        'app_id':  get('package', 'id'),
    }


def _fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Splunk/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _get_splunkbase_info(app_id):
    try:
        data    = _fetch_json(SPLUNKBASE_SEARCH_API.format(app_id))
        results = data.get('results', [])
        if not results:
            return 'N/A', None, None
        uid = results[0].get('uid')
        if not uid:
            return 'N/A', None, None
        releases = _fetch_json(SPLUNKBASE_RELEASE_API.format(uid))
        if releases and isinstance(releases, list):
            ver = releases[0].get('name')
            if ver:
                return ver, uid, SPLUNKBASE_DOWNLOAD_URL.format(uid, ver)
        return 'N/A', None, None
    except Exception:
        return 'Error', None, None


def _version_gt(latest, current):
    try:
        def parse(v):
            return tuple(int(x) for x in v.strip().split('.'))
        return parse(latest) > parse(current)
    except Exception:
        return False


# ── credential store ──────────────────────────────────────────────────────────

def _store_credentials(session_key, username, password):
    try:
        splunk.rest.simpleRequest(
            f'/services/storage/passwords/{CRED_REALM}:{CRED_NAME}:',
            sessionKey=session_key, method='DELETE'
        )
    except Exception:
        pass
    splunk.rest.simpleRequest(
        '/services/storage/passwords',
        sessionKey=session_key,
        postargs={'name': CRED_NAME, 'realm': CRED_REALM,
                  'username': username, 'password': password},
        method='POST',
        raiseAllErrors=True
    )


def _get_credentials(session_key):
    _, content = splunk.rest.simpleRequest(
        f'/services/storage/passwords/{CRED_REALM}:{CRED_NAME}:',
        sessionKey=session_key,
        getargs={'output_mode': 'json'},
        raiseAllErrors=True
    )
    data  = json.loads(content)
    entry = data['entry'][0]['content']
    return entry['username'], entry['clear_password']


# ── download & install ────────────────────────────────────────────────────────

def _download_and_install(uid, version, app_id, username, password):
    cj     = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_data = urllib.parse.urlencode(
        {'username': username, 'password': password}
    ).encode()
    login_req = urllib.request.Request(
        SPLUNKBASE_LOGIN_URL, data=login_data,
        headers={'User-Agent': 'Splunk/1.0', 'Content-Type': 'application/x-www-form-urlencoded'}
    )
    resp         = opener.open(login_req, timeout=30)
    login_result = json.loads(resp.read())
    if not login_result.get('username'):
        raise Exception('Splunkbase login failed — check your Splunk.com credentials')

    dl_url = SPLUNKBASE_DOWNLOAD_URL.format(uid, version)
    dl_req = urllib.request.Request(dl_url, headers={'User-Agent': 'Splunk/1.0'})
    resp   = opener.open(dl_req, timeout=120)

    with tempfile.NamedTemporaryFile(suffix='.tgz', delete=False) as tmp:
        tmp.write(resp.read())
        tmp_path = tmp.name

    try:
        if not tarfile.is_tarfile(tmp_path):
            raise Exception('Downloaded file is not a valid tar archive')
        with tarfile.open(tmp_path, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.name.startswith('/') or '..' in member.name:
                    raise Exception(f'Unsafe path in archive: {member.name}')
            tar.extractall(DEPLOYMENT_APPS_DIR)
    finally:
        os.unlink(tmp_path)
