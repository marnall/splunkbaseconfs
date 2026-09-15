"""
gazette_handler.py — Popup Gazette REST handlers.

  GazetteDisplayHandler  GET  /popup_gazette/display   (login only) — active notices for a dashboard
  GazetteAdminHandler    GET  /popup_gazette/notices    (gazette_edit) — list for management
                         POST /popup_gazette/notices    (gazette_edit; global/raw => gazette_admin) — upsert/delete

Notes
- KV Store reads/writes use the system token (passSystemAuth=true).
- Capability checks MUST use the user's own token (self.sessionKey); the system token would
  report the system user's capabilities and be mistaken for admin. (Same trap as lookup-editor-ax.)
- json.dumps default ensure_ascii=True — Splunk simpleRequest encodes the body as Latin-1, so
  non-ASCII (Korean) must stay \\uXXXX-escaped. The browser's JSON.parse restores it.
"""
import json
import re
import time
import urllib.parse
import logging

import splunk.rest

logger = logging.getLogger(__name__)

APP = 'popup_gazette'
COLL = 'gazette_notices'
KV_BASE = f'/servicesNS/nobody/{APP}/storage/collections/data'

CAP_ADMIN = 'gazette_admin'
CAP_EDIT = 'gazette_edit'


# ── KV helpers ──────────────────────────────────────────────────────────────
def _kv_path(key=None):
    path = f'{KV_BASE}/{COLL}'
    if key:
        path += '/' + urllib.parse.quote(str(key), safe='')
    return path + '?output_mode=json'


def _kv_req(path, method='GET', data=None, session_key=''):
    kwargs = dict(sessionKey=session_key, method=method, raiseAllErrors=True)
    if data is not None:
        kwargs['jsonargs'] = json.dumps(data)  # ensure_ascii=True keeps it Latin-1 safe
    _, content = splunk.rest.simpleRequest(path, **kwargs)
    raw = content.decode('utf-8') if isinstance(content, bytes) else content
    return json.loads(raw) if raw.strip() else {}


def _kv_list(session_key):
    recs = _kv_req(_kv_path(), method='GET', session_key=session_key)
    if isinstance(recs, dict):
        recs = [recs]
    return recs if isinstance(recs, list) else []


# ── Identity / capability ─────────────────────────────────────────────────────
def _context(session_key):
    """Return (username, roles[list], capabilities[list]) for the user's own token."""
    try:
        _, content = splunk.rest.simpleRequest(
            '/services/authentication/current-context?output_mode=json',
            sessionKey=session_key, method='GET', raiseAllErrors=True
        )
        raw = content.decode('utf-8') if isinstance(content, bytes) else content
        data = json.loads(raw)
        entry = (data.get('entry') or [{}])[0]
        c = entry.get('content', {}) or {}
        username = c.get('username') or entry.get('name') or 'unknown'
        roles = c.get('roles', [])
        if isinstance(roles, str):
            roles = [roles]
        caps = c.get('capabilities', []) or []
        return username, list(roles), list(caps)
    except Exception:
        logger.exception('current-context lookup failed')
        return 'unknown', [], []


# ── Raw HTML sanitizer (admin-only mode) ──────────────────────────────────────
_RE_BLOCK_TAG = re.compile(
    r'<\s*(script|style|iframe|object|embed|link|meta|base|form)\b[^>]*>.*?<\s*/\s*\1\s*>',
    re.IGNORECASE | re.DOTALL)
_RE_BLOCK_TAG_SELF = re.compile(
    r'<\s*(script|style|iframe|object|embed|link|meta|base|form)\b[^>]*/?>',
    re.IGNORECASE)
_RE_ON_ATTR = re.compile(r'\s+on[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', re.IGNORECASE)
_RE_JS_URI = re.compile(r'(href|src)\s*=\s*(["\']?)\s*javascript:[^"\'>\s]*\2', re.IGNORECASE)


def _sanitize_html(html):
    """Conservative sanitizer for admin Raw HTML mode: drop dangerous tags,
    inline event handlers and javascript: URIs. Not a full HTML parser — admin-only,
    defence in depth on top of the gazette_admin gate."""
    if not html:
        return ''
    out = _RE_BLOCK_TAG.sub('', html)
    out = _RE_BLOCK_TAG_SELF.sub('', out)
    out = _RE_ON_ATTR.sub('', out)
    out = _RE_JS_URI.sub(r'\1=""', out)
    return out


def _frequency(r):
    """Display frequency with backward-compat inference for notices saved before
    the frequency field existed: remember_days>0 => 'until_dismissed', else 'every'."""
    freq = r.get('frequency', '')
    if freq in ('every', 'daily', 'until_dismissed'):
        return freq
    rd = str(r.get('remember_days', '0') or '0')
    return 'until_dismissed' if rd not in ('', '0') else 'every'


class _Base(splunk.rest.BaseRestHandler):
    def _sys_key(self):
        # Elevated token for KV Store access.
        return (self.request.get('systemAuth') or self.request.get('session_key', ''))

    def _user_key(self):
        # User's own token — required for accurate capability/role checks.
        return getattr(self, 'sessionKey', '') or self.request.get('session_key', '')

    def _qp(self, key, default=''):
        query = self.request.get('query') or {}
        val = query.get(key, default)
        return val[0] if isinstance(val, list) else (val if val is not None else default)

    def _json(self, obj, status=200):
        self.response.setStatus(status)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(obj))


# ── Display: what a dashboard viewer sees ─────────────────────────────────────
class GazetteDisplayHandler(_Base):

    def handle_GET(self):
        sys_key = self._sys_key()
        app = self._qp('app')
        view = self._qp('view')
        _, roles, _ = _context(self._user_key())
        role_set = set(roles)
        now = time.time()

        try:
            records = _kv_list(sys_key)
        except Exception as e:
            logger.exception('display list failed')
            self._json({'status': 'error', 'message': str(e)})
            return

        out = []
        for r in records:
            if str(r.get('enabled', '1')) != '1':
                continue
            if not self._in_schedule(r, now):
                continue
            if not self._target_match(r, app, view):
                continue
            if not self._role_match(r, role_set):
                continue
            mode = r.get('content_mode', 'markdown')
            body = r.get('body_source', '') if mode == 'markdown' else r.get('body_html_safe', '')
            out.append({
                'key': r.get('_key', ''),
                'title': r.get('title', ''),
                'severity': r.get('severity', 'info'),
                'content_mode': mode,
                'body': body,
                'rev': str(r.get('updated_at', '') or ''),
                'frequency': _frequency(r),
                'dismissible': str(r.get('dismissible', '1')),
                'remember_days': str(r.get('remember_days', '0')),
                'cta_label': r.get('cta_label', ''),
                'cta_url': r.get('cta_url', ''),
                'priority': int(str(r.get('priority', '0')) or '0'),
            })

        out.sort(key=lambda x: x['priority'], reverse=True)
        self._json({'status': 'ok', 'data': out})

    @staticmethod
    def _in_schedule(r, now):
        st = str(r.get('start_time', '') or '').strip()
        et = str(r.get('end_time', '') or '').strip()
        try:
            if st and float(st) > now:
                return False
            if et and float(et) < now:
                return False
        except ValueError:
            return True
        return True

    @staticmethod
    def _target_match(r, app, view):
        t = r.get('target_type', 'app')
        if t == 'global':
            return True
        if t == 'app':
            return r.get('target_app', '') == app
        if t == 'view':
            return r.get('target_app', '') == app and r.get('target_view', '') == view
        return False

    @staticmethod
    def _role_match(r, role_set):
        raw = str(r.get('roles', '') or '').strip()
        if not raw:
            return True
        wanted = {x.strip() for x in raw.split(',') if x.strip()}
        return bool(role_set & wanted)


# ── Management: CRUD ──────────────────────────────────────────────────────────
class GazetteAdminHandler(_Base):

    def handle_GET(self):
        sys_key = self._sys_key()
        _, _, caps = _context(self._user_key())
        is_admin = CAP_ADMIN in caps
        scope_app = self._qp('scope_app')

        try:
            records = _kv_list(sys_key)
        except Exception as e:
            logger.exception('admin list failed')
            self._json({'status': 'error', 'message': str(e)})
            return

        if not is_admin:
            # Non-admin: must be scoped to an app; only app/view notices for that app.
            if not scope_app:
                self._json({'status': 'error', 'code': 'scope_required',
                            'message': 'scope_app required for non-admin users'}, status=403)
                return
            records = [r for r in records
                       if r.get('target_type') in ('app', 'view')
                       and r.get('target_app', '') == scope_app]
        elif scope_app:
            # Admin viewing a specific app's management page → scope to that app (+ global optional).
            records = [r for r in records if r.get('target_app', '') == scope_app
                       or r.get('target_type') == 'global']

        self._json({
            'status': 'ok',
            'data': [self._view(r) for r in records],
            'hasAdminCap': is_admin,
            'scopeApp': scope_app,
        })

    @staticmethod
    def _view(r):
        return {
            'key': r.get('_key', ''),
            'title': r.get('title', ''),
            'content_mode': r.get('content_mode', 'markdown'),
            'body_source': r.get('body_source', ''),
            'body_html_safe': r.get('body_html_safe', ''),
            'severity': r.get('severity', 'info'),
            'target_type': r.get('target_type', 'app'),
            'target_app': r.get('target_app', ''),
            'target_view': r.get('target_view', ''),
            'enabled': str(r.get('enabled', '1')),
            'start_time': str(r.get('start_time', '') or ''),
            'end_time': str(r.get('end_time', '') or ''),
            'roles': r.get('roles', ''),
            'frequency': _frequency(r),
            'dismissible': str(r.get('dismissible', '1')),
            'remember_days': str(r.get('remember_days', '0')),
            'priority': str(r.get('priority', '0')),
            'cta_label': r.get('cta_label', ''),
            'cta_url': r.get('cta_url', ''),
            'created_by': r.get('created_by', ''),
            'created_at': str(r.get('created_at', '') or ''),
            'updated_at': str(r.get('updated_at', '') or ''),
        }

    def handle_POST(self):
        sys_key = self._sys_key()
        username, _, caps = _context(self._user_key())
        is_admin = CAP_ADMIN in caps

        raw = self.request.get('payload', '') or ''
        params = urllib.parse.parse_qs(raw, keep_blank_values=True)

        def g(k, d=''):
            vals = params.get(k, [d])
            return vals[0] if vals else d

        action = g('action', 'upsert')
        key = g('key', '')
        scope_app = g('scope_app', '')

        try:
            if action == 'delete':
                if not key:
                    self._json({'status': 'error', 'message': 'key required for delete'}, status=400)
                    return
                if not self._can_write(key, scope_app, is_admin, sys_key):
                    self._json({'status': 'error', 'code': 'forbidden_scope',
                                'message': 'not allowed to modify this notice'}, status=403)
                    return
                _kv_req(_kv_path(key), method='DELETE', session_key=sys_key)
                self._json({'status': 'deleted'})
                return

            if action == 'reshow':
                # Bump the notice's version (updated_at) so prior client-side
                # dismissals no longer match — the notice reappears for everyone.
                if not key:
                    self._json({'status': 'error', 'message': 'key required for reshow'}, status=400)
                    return
                if not self._can_write(key, scope_app, is_admin, sys_key):
                    self._json({'status': 'error', 'code': 'forbidden_scope',
                                'message': 'not allowed to modify this notice'}, status=403)
                    return
                rec = _kv_req(_kv_path(key), method='GET', session_key=sys_key)
                if not isinstance(rec, dict) or not rec.get('_key'):
                    self._json({'status': 'error', 'message': 'notice not found'}, status=404)
                    return
                rec['updated_at'] = str(int(time.time()))
                _kv_req(_kv_path(key), method='POST', data=rec, session_key=sys_key)
                self._json({'status': 'ok', 'rev': rec['updated_at']})
                return

            # ── upsert ──
            target_type = g('target_type', 'app')
            content_mode = g('content_mode', 'markdown')
            target_app = g('target_app', '')

            # Privilege-escalation guards (server-side; client filtering is convenience only).
            if not is_admin:
                if target_type == 'global':
                    self._json({'status': 'error', 'code': 'forbidden_global',
                                'message': 'gazette_admin required for global notices'}, status=403)
                    return
                if content_mode == 'raw':
                    self._json({'status': 'error', 'code': 'forbidden_raw',
                                'message': 'gazette_admin required for Raw HTML mode'}, status=403)
                    return
                if not scope_app:
                    self._json({'status': 'error', 'code': 'scope_required',
                                'message': 'scope_app required for non-admin users'}, status=403)
                    return
                # Force the target app to the calling context and restrict target types.
                target_app = scope_app
                if target_type not in ('app', 'view'):
                    target_type = 'app'
                # If editing an existing notice, verify current ownership scope too.
                if key and not self._can_write(key, scope_app, is_admin, sys_key):
                    self._json({'status': 'error', 'code': 'forbidden_scope',
                                'message': 'not allowed to modify this notice'}, status=403)
                    return

            now = str(int(time.time()))
            record_key = key or ('gz_' + now + '_' + urllib.parse.quote(g('title', 'notice')[:20], safe=''))

            body_source = ''
            body_html_safe = ''
            if content_mode == 'raw':
                body_html_safe = _sanitize_html(g('body', ''))
            else:
                content_mode = 'markdown'
                body_source = g('body', '')

            record = {
                '_key': record_key,
                'title': g('title', ''),
                'content_mode': content_mode,
                'body_source': body_source,
                'body_html_safe': body_html_safe,
                'severity': g('severity', 'info'),
                'target_type': target_type,
                'target_app': target_app,
                'target_view': g('target_view', ''),
                'enabled': g('enabled', '1'),
                'start_time': g('start_time', ''),
                'end_time': g('end_time', ''),
                'roles': g('roles', ''),
                'frequency': g('frequency', 'every'),
                'dismissible': g('dismissible', '1'),
                'remember_days': g('remember_days', '0'),
                'priority': g('priority', '0'),
                'cta_label': g('cta_label', ''),
                'cta_url': g('cta_url', ''),
                'updated_at': now,
            }

            existing = None
            if key:
                try:
                    existing = _kv_req(_kv_path(key), method='GET', session_key=sys_key)
                except Exception:
                    existing = None

            if existing and isinstance(existing, dict) and existing.get('_key'):
                record['created_by'] = existing.get('created_by', username)
                record['created_at'] = str(existing.get('created_at', '') or now)
                _kv_req(_kv_path(record_key), method='POST', data=record, session_key=sys_key)
            else:
                record['created_by'] = username
                record['created_at'] = now
                _kv_req(_kv_path(), method='POST', data=record, session_key=sys_key)

            self._json({'status': 'ok', 'key': record_key})
        except Exception as e:
            logger.exception('admin POST error')
            self._json({'status': 'error', 'message': str(e)})

    def _can_write(self, key, scope_app, is_admin, sys_key):
        """Non-admins may only touch app/view notices belonging to their scope_app."""
        if is_admin:
            return True
        try:
            rec = _kv_req(_kv_path(key), method='GET', session_key=sys_key)
        except Exception:
            return False
        if not isinstance(rec, dict):
            return False
        return rec.get('target_type') in ('app', 'view') and rec.get('target_app', '') == scope_app
