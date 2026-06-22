"""REST handler backing the Setup page.

GET  /services/mcp_setup/mcpsetup/mcpsetup
    Returns metadata about credentials stored under this app's namespace in
    storage/passwords. Values are NEVER returned in plaintext — only the keys
    plus a masked flag. UI uses this to render rows and lets the user choose
    to overwrite or keep each value.

POST /services/mcp_setup/mcpsetup/mcpsetup
    Body: creds_json = JSON list of {"key": str, "value": str}
    - value == "__UNCHANGED__" → keep the existing stored value as-is.
    - value == "" → empty string is stored (allows explicit clearing).
    - keys missing from the incoming list (but currently stored) are deleted
      so the UI can rename or remove rows.
"""
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import splunk
import splunk.admin
import splunk.entity as entity
from validators import validate_key, ValidationError  # noqa: F401  (used below)

logger = logging.getLogger(__name__)

CREDENTIAL_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_.\-]{1,100}$')
APP_NAME = "AI_Query_Assistant_for_Splunk"
SENTINEL_UNCHANGED = "__UNCHANGED__"


class ConfigHandler(splunk.admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == splunk.admin.ACTION_EDIT:
            self.supportedArgs.addOptArg('creds_json')
            # Legacy field names tolerated only to ease rolling upgrade —
            # values are still treated as opaque secrets.
            self.supportedArgs.addOptArg('credential_key')
            self.supportedArgs.addOptArg('credential')

    def _list_app_credentials(self):
        entities = entity.getEntities(
            ['storage', 'passwords'],
            namespace=APP_NAME,
            owner='nobody',
            sessionKey=self.getSessionKey(),
        )
        results = []
        for _, c in entities.items():
            try:
                if c['eai:acl']['app'] == APP_NAME:
                    results.append({'key': c['username'], 'masked': True})
            except (KeyError, TypeError):
                continue
        return results

    def handleList(self, confInfo):
        try:
            creds = self._list_app_credentials()
            confInfo['mcpsetup'].append('creds_json', json.dumps(creds))
            # Backward-compat: include the key list under the legacy field so
            # older clients still see the keys; values are no longer returned.
            confInfo['mcpsetup'].append('credential_key', '::'.join(c['key'] for c in creds))
            confInfo['mcpsetup'].append('credential_count', str(len(creds)))
        except Exception as e:
            logger.exception("Error listing credentials")
            confInfo['mcpsetup'].append('creds_json', '[]')
            confInfo['mcpsetup'].append('credential_key', '')
            confInfo['mcpsetup'].append('error', str(e))

    def _parse_incoming(self):
        data = self.callerArgs.data or {}
        raw = (data.get('creds_json') or [None])[0]
        if raw:
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError):
                raise splunk.admin.ArgValidationException("creds_json must be valid JSON")
            if not isinstance(parsed, list):
                raise splunk.admin.ArgValidationException("creds_json must be a list")
            out = []
            seen = set()
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                key = (item.get('key') or '').strip()
                if not key:
                    continue
                if not CREDENTIAL_KEY_PATTERN.match(key):
                    raise splunk.admin.ArgValidationException(
                        f"Invalid credential key '{key}': must match {CREDENTIAL_KEY_PATTERN.pattern}"
                    )
                if key in seen:
                    continue
                seen.add(key)
                # Issue #12: front end can signal "keep existing stored value"
                # via a sibling boolean instead of a magic-string sentinel in
                # the value field, so a user can legitimately store the literal
                # string '__UNCHANGED__' as a secret.
                if item.get('unchanged') is True:
                    out.append({'key': key, 'value': SENTINEL_UNCHANGED})
                else:
                    out.append({'key': key, 'value': item.get('value', '')})
            return out

        # Legacy `::` payload — kept for one rolling-upgrade window.
        legacy_keys = (data.get('credential_key') or [''])[0]
        legacy_vals = (data.get('credential') or [''])[0]
        keys = [k.strip() for k in (legacy_keys or '').split('::') if k.strip()]
        vals = (legacy_vals or '').split('::')
        out = []
        seen = set()
        for i, k in enumerate(keys):
            if not CREDENTIAL_KEY_PATTERN.match(k):
                raise splunk.admin.ArgValidationException(
                    f"Invalid credential key '{k}'"
                )
            if k in seen:
                continue
            seen.add(k)
            out.append({'key': k, 'value': vals[i] if i < len(vals) else ''})
        return out

    def handleEdit(self, confInfo):
        try:
            incoming = self._parse_incoming()
            incoming_keys = {c['key'] for c in incoming}
            session_key = self.getSessionKey()

            # Snapshot existing credentials for diffing.
            existing_keys = set()
            try:
                for c in self._list_app_credentials():
                    existing_keys.add(c['key'])
            except Exception as e:
                logger.warning("Could not snapshot existing credentials: %s", e)

            # Delete credentials that the user removed from the UI.
            for old_key in existing_keys - incoming_keys:
                try:
                    entity.deleteEntity(
                        ['storage', 'passwords'], ":%s:" % old_key,
                        namespace=APP_NAME, owner='nobody',
                        sessionKey=session_key,
                    )
                except Exception as e:
                    logger.warning("Failed to delete obsolete credential '%s': %s", old_key, e)

            # Upsert the incoming set.
            for cred in incoming:
                key = cred['key']
                value = cred['value']
                # Sentinel from UI: keep existing stored value, do nothing.
                if value == SENTINEL_UNCHANGED:
                    if key not in existing_keys:
                        # Sentinel for a key that does not exist yet — treat as empty.
                        value = ''
                    else:
                        continue
                try:
                    new_credential = entity.Entity(
                        ['storage', 'passwords'], key,
                        contents={'password': value},
                        namespace=APP_NAME, owner='nobody',
                    )
                    entity.setEntity(new_credential, sessionKey=session_key)
                except Exception as e:
                    logger.error("Failed to upsert credential '%s': %s", key, e)
                    raise splunk.admin.ArgValidationException(
                        f"Failed to save credential '{key}'"
                    )

        except splunk.admin.ArgValidationException:
            raise
        except Exception:
            logger.exception("Error editing credentials")
            raise


splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_APP_AND_USER)
