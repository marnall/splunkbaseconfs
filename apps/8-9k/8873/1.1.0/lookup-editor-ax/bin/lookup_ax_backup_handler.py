"""
lookup_ax_backup_handler.py
List backups / restore a specific backup / delete a backup
"""
import csv
import json
import os
import datetime
import urllib.parse
import tempfile
import logging

import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path

logger = logging.getLogger(__name__)

APP = 'lookup-editor-ax'
KV_BASE = f'/servicesNS/nobody/{APP}/storage/collections/data'
COLL = 'lookup_ax_schemas'

csv.field_size_limit(10485760)


def _is_schema_registered(app, filename, session_key):
    """Check whether the (app, filename) schema is registered in the KV Store."""
    key = f'{app}__{filename}'
    url = f'{KV_BASE}/{COLL}/{urllib.parse.quote(key, safe="")}?output_mode=json'
    try:
        _, content = splunk.rest.simpleRequest(url, sessionKey=session_key, method='GET', raiseAllErrors=True)
        raw = content.decode('utf-8') if isinstance(content, bytes) else content
        rec = json.loads(raw) if raw.strip() else {}
        return isinstance(rec, dict) and '_key' in rec
    except Exception:
        return False


def _user_has_capability(session_key, capability):
    """Check capability ownership using the user's own session_key."""
    try:
        _, content = splunk.rest.simpleRequest(
            '/services/authentication/current-context?output_mode=json',
            sessionKey=session_key, method='GET', raiseAllErrors=True
        )
        raw = content.decode('utf-8') if isinstance(content, bytes) else content
        data = json.loads(raw)
        entries = data.get('entry', [])
        if not entries:
            return False
        return capability in entries[0].get('content', {}).get('capabilities', [])
    except Exception:
        return False


def _get_lookup_path(app, filename, session_key):
    safe_app  = urllib.parse.quote(app, safe='')
    safe_file = urllib.parse.quote(filename, safe='')
    url = f'/servicesNS/nobody/{safe_app}/data/lookup-table-files/{safe_file}?output_mode=json'
    try:
        _, content = splunk.rest.simpleRequest(url, sessionKey=session_key, method='GET', raiseAllErrors=True)
        raw = content.decode('utf-8') if isinstance(content, bytes) else content
        data = json.loads(raw)
        return data['entry'][0]['content']['eai:data']
    except Exception:
        return None


def _backup_dir(lookup_path, app, filename):
    safe_filename = filename.replace('/', '_').replace('\\', '_')
    return os.path.join(
        os.path.dirname(lookup_path),
        'lookup_file_backups', app, safe_filename
    )


def _save_csv(rows, app, filename, session_key):
    lookup_tmp = make_splunkhome_path(['var', 'run', 'splunk', 'lookup_tmp'])
    os.makedirs(lookup_tmp, exist_ok=True)

    tmp = tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', dir=lookup_tmp,
        encoding='utf-8', delete=False, newline=''
    )
    writer = csv.writer(tmp)
    writer.writerows(rows)
    tmp.close()

    try:
        safe_app  = urllib.parse.quote(app, safe='')
        safe_file = urllib.parse.quote(filename, safe='')
        url = f'/servicesNS/nobody/{safe_app}/data/lookup-table-files/{safe_file}'
        splunk.rest.simpleRequest(
            url,
            sessionKey=session_key,
            method='POST',
            postargs={'eai:data': tmp.name, 'output_mode': 'json'},
            raiseAllErrors=True
        )
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


class LookupAxBackupHandler(splunk.rest.BaseRestHandler):

    def _session_key(self):
        return (self.request.get('systemAuth') or self.request.get('session_key', ''))

    def _user_session_key(self):
        return getattr(self, 'sessionKey', '') or self.request.get('session_key', '')

    def _enforce_managed(self, app, filename, sk):
        """Allow backup operations only for lookups registered in the managed list (KV).
        Users with lookup_ax_admin are allowed even for unregistered ones (free admin access).
        """
        if _is_schema_registered(app, filename, sk):
            return False
        if _user_has_capability(self._user_session_key(), 'lookup_ax_admin'):
            return False
        self.response.setStatus(403)
        self._send_json({
            'status':   'error',
            'code':     'not_managed',
            'app':      app,
            'filename': filename,
            'message':  f'Not managed: {app}/{filename}',
        })
        return True

    def _qp(self, key, default=''):
        query = self.request.get('query') or {}
        val = query.get(key, default)
        return val[0] if isinstance(val, list) else (val if val is not None else default)

    def _send_json(self, obj):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(obj))

    def handle_GET(self):
        sk = self._session_key()
        app      = self._qp('app')
        filename = self._qp('filename')

        if not app or not filename:
            self._send_json({'status': 'error', 'message': 'app and filename required'})
            return

        if self._enforce_managed(app, filename, sk):
            return

        try:
            lookup_path = _get_lookup_path(app, filename, sk)
            if not lookup_path:
                self._send_json({'status': 'ok', 'backups': []})
                return

            bdir = _backup_dir(lookup_path, app, filename)
            if not os.path.isdir(bdir):
                self._send_json({'status': 'ok', 'backups': []})
                return

            backups = []
            for f in os.listdir(bdir):
                full = os.path.join(bdir, f)
                if not os.path.isfile(full):
                    continue
                try:
                    ts = float(f)
                    backups.append({
                        'ts':          f,
                        'ts_readable': datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                        'size':        os.path.getsize(full),
                    })
                except ValueError:
                    continue

            backups.sort(key=lambda x: float(x['ts']), reverse=True)
            self._send_json({'status': 'ok', 'backups': backups})
        except Exception as e:
            logger.exception('Backup GET error')
            self._send_json({'status': 'error', 'message': str(e)})

    def handle_POST(self):
        sk = self._session_key()
        raw = self.request.get('payload', '') or ''
        params = urllib.parse.parse_qs(raw)

        def g(k, d=''):
            vals = params.get(k, [d])
            return vals[0] if vals else d

        app       = g('app')
        filename  = g('filename')
        action    = g('action', 'restore')
        backup_ts = g('backup_ts', '')

        if not app or not filename or not backup_ts:
            self._send_json({'status': 'error', 'message': 'app, filename, backup_ts required'})
            return

        if self._enforce_managed(app, filename, sk):
            return

        try:
            lookup_path = _get_lookup_path(app, filename, sk)
            if not lookup_path:
                self._send_json({'status': 'error', 'message': 'Lookup file not found'})
                return

            bdir     = _backup_dir(lookup_path, app, filename)
            bak_path = os.path.join(bdir, backup_ts)

            if not os.path.isfile(bak_path):
                self._send_json({'status': 'error', 'message': f'Backup not found: {backup_ts}'})
                return

            if action == 'delete':
                os.unlink(bak_path)
                self._send_json({'status': 'deleted'})

            elif action == 'restore':
                with open(bak_path, encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                _save_csv(rows, app, filename, sk)
                self._send_json({'status': 'restored'})

            else:
                self._send_json({'status': 'error', 'message': f'Unknown action: {action}'})

        except Exception as e:
            logger.exception('Backup POST error')
            self._send_json({'status': 'error', 'message': str(e)})
