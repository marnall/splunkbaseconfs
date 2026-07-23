"""
lookup_ax_editor_handler.py
CSV read/write + header validation. Saves via tmp -> eai:data.
GET: read CSV (returns allowed columns only)
POST action=save: save inline edits
POST action=upload: save uploaded CSV
"""
import csv
import json
import os
import tempfile
import urllib.parse
import base64
import logging

import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path

logger = logging.getLogger(__name__)

APP = 'lookup-editor-ax'
KV_BASE = f'/servicesNS/nobody/{APP}/storage/collections/data'
COLL = 'lookup_ax_schemas'

csv.field_size_limit(10485760)


def _kv_path(key=None):
    path = f'{KV_BASE}/{COLL}'
    if key:
        path += '/' + urllib.parse.quote(str(key), safe='')
    return path + '?output_mode=json'


def _kv_req(path, method='GET', data=None, session_key=''):
    kwargs = dict(sessionKey=session_key, method=method, raiseAllErrors=True)
    if data is not None:
        # ensure_ascii=True (default) — \uXXXX escaping keeps it ASCII-safe (avoids Latin-1 encoding errors)
        kwargs['jsonargs'] = json.dumps(data)
    _, content = splunk.rest.simpleRequest(path, **kwargs)
    raw = content.decode('utf-8') if isinstance(content, bytes) else content
    return json.loads(raw) if raw.strip() else {}


def _user_has_capability(session_key, capability):
    """Check whether the capability is held, using the user's own session_key."""
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


def _get_schema(app, filename, session_key):
    key = f'{app}__{filename}'
    try:
        rec = _kv_req(_kv_path(key), method='GET', session_key=session_key)
        if isinstance(rec, dict) and '_key' in rec:
            cols = json.loads(rec.get('columns', '[]'))
            max_bk = int(rec.get('max_backups', 10))
            try:
                ctypes = json.loads(rec.get('column_types', '{}')) or {}
            except Exception:
                ctypes = {}
            return cols, max_bk, ctypes
    except Exception:
        pass
    return None, 10, {}


def _col_type(column_types, name):
    """Return the simple type name ('string'|'number') for a column. Accepts both the
    object form {"name": {"type": "number"}} and the flat form {"name": "number"}."""
    spec = (column_types or {}).get(name)
    if isinstance(spec, dict):
        return spec.get('type', 'string')
    if isinstance(spec, str):
        return spec
    return 'string'


def _is_number(s):
    """True for blank (allowed in soft mode) or anything float() can parse."""
    s = '' if s is None else str(s).strip()
    if s == '':
        return True
    try:
        v = float(s)
        return v == v and v not in (float('inf'), float('-inf'))  # reject NaN/inf
    except (ValueError, TypeError):
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


def _is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _do_backup(app, filename, session_key, max_bk):
    import shutil
    lookup_path = _get_lookup_path(app, filename, session_key)
    if not lookup_path or not os.path.isfile(lookup_path):
        return

    safe_filename = filename.replace('/', '_').replace('\\', '_')
    backup_dir = os.path.join(
        os.path.dirname(lookup_path),
        'lookup_file_backups', app, safe_filename
    )
    os.makedirs(backup_dir, exist_ok=True)

    ts  = str(os.path.getmtime(lookup_path))
    dst = os.path.join(backup_dir, ts)
    if not os.path.exists(dst):
        shutil.copy2(lookup_path, dst)

    backups = sorted(
        [f for f in os.listdir(backup_dir) if os.path.isfile(os.path.join(backup_dir, f))],
        key=lambda f: float(f) if _is_float(f) else 0
    )
    while len(backups) > max_bk:
        os.unlink(os.path.join(backup_dir, backups.pop(0)))


class LookupAxEditorHandler(splunk.rest.BaseRestHandler):

    def _session_key(self):
        # For privilege-bypass operations like KV Store / lookup-table-files (systemAuth preferred)
        return (self.request.get('systemAuth') or self.request.get('session_key', ''))

    def _user_session_key(self):
        # For capability checks — the user's own token
        return getattr(self, 'sessionKey', '') or self.request.get('session_key', '')

    def _enforce_managed(self, app, filename, columns):
        """Allow access only to lookups registered in the managed list (schema).
        Users with lookup_ax_admin can freely access unregistered lookups too (preserves existing behavior).
        Users with only lookup_ax_edit can access registered ones only.
        Returns: True if blocked (response already sent), False if OK to proceed.
        """
        if columns is not None:
            return False  # registered schema → proceed
        if _user_has_capability(self._user_session_key(), 'lookup_ax_admin'):
            return False  # admin gets free-form access
        self.response.setStatus(403)
        self._send_json({
            'status':   'error',
            'code':     'not_managed',
            'app':      app,
            'filename': filename,
            'message':  f'Not managed: {app}/{filename}',  # English fallback (translated by frontend i18n)
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

        try:
            columns, _, column_types = _get_schema(app, filename, sk)
            if self._enforce_managed(app, filename, columns):
                return  # blocked (response already sent)
            lookup_path = _get_lookup_path(app, filename, sk)

            if not lookup_path or not os.path.isfile(lookup_path):
                self._send_json({'status': 'error', 'message': f'Lookup file not found: {filename}'})
                return

            with open(lookup_path, encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                file_headers = reader.fieldnames or []
                rows = list(reader)

            if columns:
                headers = [c for c in columns if c in file_headers]
                missing = [c for c in columns if c not in file_headers]
                filtered = [{h: r.get(h, '') for h in headers} for r in rows]
            else:
                headers  = file_headers
                missing  = []
                filtered = [{h: r.get(h, '') for h in headers} for r in rows]

            # Simple per-column type map ({name: 'number'}) for the columns being returned.
            # Columns default to string and are omitted to keep the payload small.
            types = {h: _col_type(column_types, h) for h in headers
                     if _col_type(column_types, h) != 'string'}

            self._send_json({
                'status':  'ok',
                'headers': headers,
                'rows':    filtered,
                'missing': missing,
                'types':   types,
                # Actual file headers (unfiltered by the allowed-columns whitelist) — the
                # Manager modal uses this to offer type assignment for every real column.
                'file_headers': file_headers,
                'path':    lookup_path,
            })
        except Exception as e:
            logger.exception('Editor GET error')
            self._send_json({'status': 'error', 'message': str(e)})

    def handle_POST(self):
        sk = self._session_key()
        raw = self.request.get('payload', '') or ''
        params = urllib.parse.parse_qs(raw)

        def g(k, d=''):
            vals = params.get(k, [d])
            return vals[0] if vals else d

        app      = g('app')
        filename = g('filename')
        action   = g('action', 'save')

        if not app or not filename:
            self._send_json({'status': 'error', 'message': 'app and filename required'})
            return

        try:
            columns, max_bk, column_types = _get_schema(app, filename, sk)
            if self._enforce_managed(app, filename, columns):
                return  # blocked

            if action == 'save':
                rows_json = g('rows', '[]')
                data_rows = json.loads(rows_json)

                if columns:
                    headers = columns
                elif data_rows:
                    headers = list(data_rows[0].keys())
                else:
                    self._send_json({'status': 'error', 'message': 'No columns defined'})
                    return

                _do_backup(app, filename, sk, max_bk)
                csv_rows = [headers] + [[r.get(h, '') for h in headers] for r in data_rows]
                _save_csv(csv_rows, app, filename, sk)
                self._send_json({'status': 'ok'})

            elif action == 'upload':
                csv_b64 = g('csv_b64', '')
                if not csv_b64:
                    self._send_json({'status': 'error', 'message': 'csv_b64 required'})
                    return

                csv_text = base64.b64decode(csv_b64).decode('utf-8-sig')  # auto-strip BOM
                reader   = csv.DictReader(csv_text.splitlines())
                up_headers = reader.fieldnames or []
                up_rows    = list(reader)

                warning = ''
                if columns:
                    invalid = [h for h in up_headers if h not in columns]
                    missing = [c for c in columns if c not in up_headers]
                    if invalid:
                        self._send_json({
                            'status': 'error',
                            'code':    'invalid_columns',
                            'invalid': invalid,
                            'allowed': list(columns),
                            'message': f'Invalid columns: {", ".join(invalid)}'
                        })
                        return
                    if missing:
                        warning = f'Columns in schema but missing from file: {", ".join(missing)}'
                    headers = columns
                else:
                    headers = up_headers

                # Soft type validation: count non-numeric cells in number columns.
                # Never blocks the upload — surfaced as a warning only.
                num_cols = [h for h in headers if _col_type(column_types, h) == 'number']
                if num_cols:
                    bad = sum(1 for r in up_rows for h in num_cols if not _is_number(r.get(h, '')))
                    if bad:
                        msg = f'{bad} cell(s) in number column(s) are not numeric'
                        warning = f'{warning}; {msg}' if warning else msg

                _do_backup(app, filename, sk, max_bk)
                csv_rows = [headers] + [[r.get(h, '') for h in headers] for r in up_rows]
                _save_csv(csv_rows, app, filename, sk)
                self._send_json({'status': 'ok', 'warning': warning})

            else:
                self._send_json({'status': 'error', 'message': f'Unknown action: {action}'})

        except Exception as e:
            logger.exception('Editor POST error')
            self._send_json({'status': 'error', 'message': str(e)})
