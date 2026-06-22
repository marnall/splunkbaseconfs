"""
MCP Core Handler
Shared base class with common utilities for all MCP endpoint handlers.
"""
import sys
import os
import json
import time
import logging

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import splunk.admin as admin
import splunk.entity as entity
from splunklib import client
from kv_store import KVStoreClient, KVStoreError
from license_verifier import get_cached_license_status, LicenseError

# NOTE: do not call logging.basicConfig() in library code — Splunkd already
# configures the root logger. We only request a named logger here.
logger = logging.getLogger(__name__)


class MCPBaseHandler(admin.MConfigHandler):
    """Base handler with shared utilities"""

    def _check_rate_limit(self, max_requests=30, window_seconds=60):
        """Token-bucket rate limit backed by the KV store so it survives
        handler-process restarts and applies across handler types.

        Falls open (returns True) if KV is unavailable — rate-limit failure
        must not block the user request, the underlying call site will still
        be subject to license + concurrency caps.
        """
        user = getattr(self, 'userName', None) or 'unknown'
        bucket_key = f"rl:{user}"
        now = time.time()
        cutoff = now - window_seconds
        try:
            service = self._get_splunk_service()
            coll = service.kvstore['mcp_usage'].data
            try:
                rec = coll.query_by_id(bucket_key) or {}
            except Exception as e:
                if '404' not in str(e) and 'not found' not in str(e).lower():
                    return True
                rec = {}
            timestamps = rec.get('rl_timestamps') or []
            timestamps = [t for t in timestamps if isinstance(t, (int, float)) and t > cutoff]
            if len(timestamps) >= max_requests:
                payload = {'_key': bucket_key, 'user': user,
                           'rl_timestamps': timestamps,
                           'updated_at': now}
                try:
                    coll.update(bucket_key, json.dumps(payload))
                except Exception:
                    coll.insert(json.dumps(payload))
                return False
            timestamps.append(now)
            payload = {'_key': bucket_key, 'user': user,
                       'rl_timestamps': timestamps[-max_requests:],
                       'updated_at': now}
            try:
                coll.update(bucket_key, json.dumps(payload))
            except Exception:
                try:
                    coll.insert(json.dumps(payload))
                except Exception as e:
                    logger.warning("rate_limit upsert failed for %s: %s", user, e)
            return True
        except Exception as e:
            logger.warning("rate_limit unavailable, allowing request: %s", e)
            return True

    @staticmethod
    def _normalize_bool(value):
        """Normalize various boolean representations to a Python bool.

        Accepts real bools, ints, and any string whose lowercase form is
        'true'/'1'/'yes'/'on'. Anything else (incl. None) returns False.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in ('true', '1', 'yes', 'on')
        return False

    @staticmethod
    def _dev_license_bypass_enabled():
        """True only for a DEV build explicitly launched with the bypass env
        var. C1 hardening: replaces the old ``mcp.conf [ai] dev_skip_license``
        switch, which let anyone with write access to local/*.conf disable all
        licensing in one line (a one-step crack). Two independent conditions,
        BOTH required:

          1. env ``RSTLIC_DEV_SKIP_LICENSE`` truthy — set by whoever starts
             splunkd, NOT reachable by editing app config files;
          2. marker file ``<app>/DEV_BUILD`` exists — present only in dev
             builds, stripped from the released package.

        Neither a stray env var on a customer install nor a copied marker
        alone disables licensing. Production ships without the marker → always
        False there.
        """
        import os as _os
        if not MCPBaseHandler._normalize_bool(
                _os.environ.get('RSTLIC_DEV_SKIP_LICENSE', '')):
            return False
        app_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        return _os.path.isfile(_os.path.join(app_root, 'DEV_BUILD'))

    @staticmethod
    def _handle_error(confInfo, error_type, message, as_exception=False):
        """Set a standardized error response on confInfo.

        Issue #17: when ``as_exception=True``, raise a typed
        ``splunk.admin`` exception instead of writing the error onto
        ``confInfo``. This lets external API clients receive proper HTTP
        status codes (400 / 4xx) for validation/security/license/rate-limit
        problems while preserving the legacy 200+payload-error contract for
        the existing front-end JS when ``as_exception=False``.

        Mapping:
          * 'security_blocked', 'invalid_input'  -> ArgValidationException (400)
          * 'license_invalid', 'rate_limit',
            'daily_limit', 'concurrent_limit'    -> AdminManagerException (4xx)
          * anything else                        -> AdminManagerException
        """
        if as_exception:
            arg_validation_types = {'security_blocked', 'invalid_input', 'arg_validation'}
            if error_type in arg_validation_types:
                raise admin.ArgValidationException(f"{error_type}: {message}")
            raise admin.AdminManagerException(f"{error_type}: {message}")
        confInfo['result'].append('error', error_type)
        confInfo['result'].append('message', str(message))

    def _log_prefix(self):
        """Return a log prefix with user context."""
        user = getattr(self, 'userName', None) or 'unknown'
        return f"[user={user}]"

    # Issue #14: shared once-only KV migration trigger. Both the license
    # activation path AND the first query call invoke this so customers who
    # upgraded WITHOUT re-activating their license still get migrated.
    # The flag lives in storage/passwords (key MIGRATION_FLAG_KEY) and the
    # migration script itself is idempotent, so concurrent triggers are safe.
    MIGRATION_FLAG_KEY = 'mcp_migration_v2210_done'

    def _maybe_run_v2210_migration(self):
        """Run the one-shot 2.2.x → 3.0.x KV cleanup if not already done.

        Returns True if the migration was attempted (success or fail), False
        if it was skipped because the flag was already set. Failures are
        logged but never raised — a metrics/cleanup task must NOT block the
        user's primary flow.
        """
        try:
            if self._get_encrypted_credential(self.MIGRATION_FLAG_KEY):
                return False
            from datetime import datetime, timezone
            try:
                from migrate_v2210 import migrate_providers
                stats = migrate_providers(self.getSessionKey())
                logger.info("v2210 migration completed: %s", stats)
            except Exception as e:
                logger.warning("v2210 migration failed (non-fatal): %s", e)
                return True  # Tried but failed — flag stays unset so we retry next time
            ts = datetime.now(timezone.utc).isoformat()
            self._store_encrypted_credential(self.MIGRATION_FLAG_KEY, ts)
            return True
        except Exception as e:
            # Outer guard — even reading the flag must not break anything.
            logger.warning("v2210 migration trigger crashed: %s", e)
            return False

    def _get_encrypted_credential(self, credential_key, raise_on_error=False):
        """Retrieve a decrypted credential from storage/passwords by key name.

        Returns None when the credential simply does not exist. By default a
        backend error also returns None (legacy callers swallow this); pass
        ``raise_on_error=True`` to distinguish 'absent' from 'storage hiccup'.
        """
        try:
            entities = entity.getEntities(
                ['storage', 'passwords'],
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
        except Exception as e:
            logger.error("Failed to enumerate storage/passwords: %s", e)
            if raise_on_error:
                raise
            return None
        for _, c in entities.items():
            try:
                if c['eai:acl']['app'] == 'AI_Query_Assistant_for_Splunk' and c['username'] == credential_key:
                    return c['clear_password']
            except (KeyError, TypeError):
                continue
        return None

    def _store_encrypted_credential(self, credential_key, credential_value):
        """Store a credential in storage/passwords (encrypted at rest)"""
        try:
            # Delete existing if present
            try:
                entity.deleteEntity(
                    ['storage', 'passwords'], ":%s:" % credential_key,
                    namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                    sessionKey=self.getSessionKey()
                )
            except Exception:
                pass  # May not exist yet

            new_credential = entity.Entity(
                ['storage', 'passwords'], credential_key,
                contents={'password': credential_value},
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody'
            )
            entity.setEntity(new_credential, sessionKey=self.getSessionKey())
            return True
        except Exception as e:
            logger.error(f"Failed to store encrypted credential '{credential_key}': {e}")
            return False

    def _delete_encrypted_credential(self, credential_key):
        """Delete a credential from storage/passwords"""
        try:
            entity.deleteEntity(
                ['storage', 'passwords'], ":%s:" % credential_key,
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete encrypted credential '{credential_key}': {e}")
            return False

    def _get_config(self):
        try:
            config = {}
            # 'license_server' added in 3.0.x for the RST License Server SDK —
            # mcp_license_phone_home._read_config() looks it up via this dict.
            # Listed last because it's optional; absent stanzas resolve to {}.
            for stanza_name in ('ai', 'security', 'integration', 'query', 'license_server'):
                try:
                    ent = entity.getEntity(
                        '/configs/conf-mcp', stanza_name,
                        namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                        sessionKey=self.getSessionKey()
                    )
                    config[stanza_name] = dict(ent)
                except Exception:
                    config[stanza_name] = {}
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _get_splunk_service(self):
        if getattr(self, '_svc', None) is None:
            self._svc = client.connect(
                token=self.getSessionKey(),
                owner='nobody',
                app='AI_Query_Assistant_for_Splunk',
                timeout=30,
            )
            # Wire usage_tracker so its per-user counters land in KV instead of
            # the per-process dict that defeated daily/concurrent limits.
            try:
                from usage_tracker import set_service_factory
                svc = self._svc
                set_service_factory(lambda: svc)
            except Exception as e:
                logger.warning("could not wire usage_tracker service factory: %s", e)
        return self._svc

    def _get_default_provider(self):
        try:
            config = self._get_config()
            default_id = config.get('ai', {}).get('default_provider_id', '')
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')

            provider = None
            if default_id:
                records = kv_client.query({'provider_id': default_id}, limit=1)
                if records:
                    provider = records[0]

            if not provider:
                # Scan and pick first record whose is_default normalises to True
                records = kv_client.query(limit=200)
                for r in records:
                    if self._normalize_bool(r.get('is_default')):
                        provider = r
                        break

            if not provider:
                records = kv_client.query(limit=1)
                if records:
                    provider = records[0]

            if not provider:
                return None

            # Resolve API key from storage/passwords
            credential_key = provider.get('credential_key', '')
            if credential_key:
                api_key = self._get_encrypted_credential(credential_key)
                if api_key:
                    provider['api_key'] = api_key

            return provider
        except Exception as e:
            logger.error(f"Failed to get default provider: {e}")
            return None

    def _clear_default_providers(self):
        try:
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            records = kv_client.query(limit=500)
            for record in records:
                if self._normalize_bool(record.get('is_default')):
                    record['is_default'] = False
                    try:
                        kv_client.update(record['_key'], record)
                    except Exception as e:
                        # Surface so we don't silently leave duplicate defaults
                        logger.warning("clear_default: failed to unset %s: %s", record.get('_key'), e)
                        raise
        except Exception as e:
            logger.warning(f"Failed to clear default providers: {e}")
            raise

    def _check_license(self):
        """Server-side license check. Raises admin.AdminManagerException if invalid.

        Layered: (1) local RSA-PSS signature + expiry + GUID check, then
        (2) RST License Server signals via the phone-home SDK. The local
        layer is authoritative when the server is unreachable (offline grace
        window); a remote *revoke* always wins regardless of grace.

        Dev-mode bypass: gated on the ENVIRONMENT variable
        ``RSTLIC_DEV_SKIP_LICENSE=1`` — NOT on any app.conf setting. This is
        deliberate (C1 hardening): the old ``[ai] dev_skip_license=true`` conf
        switch let anyone with write access to the app's local/*.conf disable
        all licensing with one line — a one-step crack that defeated every
        other gate. An env var is set by whoever launches splunkd, which a
        customer editing config files cannot reach; production splunkd is
        never started with it. The bypass also requires a debug build marker
        file so a stray env var on a release install does nothing.
        """
        try:
            if self._dev_license_bypass_enabled():
                logger.warning(
                    f"{self._log_prefix()} LICENSE CHECK BYPASSED via "
                    f"RSTLIC_DEV_SKIP_LICENSE env (dev build) — never on production"
                )
                return
        except Exception:
            # Reading bypass state failed; fall through to the real check
            # rather than letting a blip skip licensing accidentally.
            pass

        try:
            server_info = entity.getEntity(
                '/server', 'info',
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
            server_guid = server_info.get('guid', '')
        except Exception as e:
            logger.error(f"Failed to get server GUID for license check: {e}")
            raise admin.AdminManagerException(f"License check failed: cannot determine server GUID")

        license_key = self._get_encrypted_credential('mcp_license_key')
        if not license_key:
            raise admin.AdminManagerException("No valid license. Please activate your license.")

        result = get_cached_license_status(license_key, server_guid)
        if not result['valid']:
            raise admin.AdminManagerException(f"License invalid: {result['error']}")

        # Layer 2: remote-state checks via the RST License Server SDK. Wrapped
        # in try/except because an SDK import error or storage/passwords blip
        # must NOT block a customer whose locally-signed license is valid;
        # the worst outcome of an SDK fault here is missing a remote revoke,
        # not denying a paying customer. AdminManagerException raised inside
        # is preserved (it indicates a deliberate revoke / out-of-grace stop).
        try:
            from mcp_license_phone_home import (
                is_revoked, in_offline_grace, check_session_binding,
                _wire_crl_into_verifier,
            )
            # First-call: wire the CRL fetcher into license_verifier so
            # revoke status propagates faster than the daily heartbeat.
            # Idempotent — subsequent calls are no-ops.
            _wire_crl_into_verifier(self)
            if is_revoked(self, result['data'].get('license_id')):
                raise admin.AdminManagerException(
                    "License has been revoked by the issuer. Please contact support."
                )
            if not in_offline_grace(self, result['data'].get('license_id')):
                raise admin.AdminManagerException(
                    "License server has not been reachable for too long. "
                    "Please verify network connectivity to the license server."
                )
            # C2 / SEC-AC-1 host binding: once this install has activated (a
            # session_token is cached), the license must stay on the machine
            # it activated on. A copied license fails the fingerprint match
            # even fully offline. No session_token yet → returns ok (a freshly
            # pasted, not-yet-activated license is gated by the local
            # signature + expiry checks above, and activation binds it).
            bound_ok, bind_reason = check_session_binding(self, result['data'].get('license_id'))
            if not bound_ok:
                raise admin.AdminManagerException(
                    "This license is activated on a different machine and "
                    "cannot be used here. Each license is bound to one host; "
                    "contact support if you need to move it."
                )
        except admin.AdminManagerException:
            raise
        except Exception as e:
            logger.warning("license phone-home check failed (non-blocking): %s", e)

    def _get_license_data(self):
        """Get validated license data.

        Returns:
            dict: License data or None if invalid
        """
        try:
            server_info = entity.getEntity(
                '/server', 'info',
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
            server_guid = server_info.get('guid', '')
        except Exception as e:
            logger.error(f"Failed to get server GUID: {e}")
            return None

        license_key = self._get_encrypted_credential('mcp_license_key')
        if not license_key:
            return None

        result = get_cached_license_status(license_key, server_guid)
        return result.get('data') if result['valid'] else None

    def _get_license_limits(self):
        """Get license limits based on license type. Tier name comparison is
        case-insensitive (so an "Enterprise"-cased license does not silently
        fall back to starter limits)."""
        default_limits = {
            'daily_query_limit': 50,        # was -1 (unlimited) — starter must cap
            'max_providers': 1,
            'max_concurrent_queries': 2,    # was 5 — starter is single-user
            'history_retention_days': 7,
            'max_templates': 5,
            'base_seats': 1,
            'cache_ttl_seconds': 900,
            'allow_extra_seats': False
        }

        license_data = self._get_license_data()
        if not license_data:
            return default_limits

        license_type_raw = license_data.get('license_type', 'starter')
        license_type = (license_type_raw or '').strip().lower()

        limits_by_type = {
            # 7-day trial — same caps as starter so existing trial license
            # holders aren't surprised by limits below what an evaluation
            # would reasonably need. Trial is gated by expiry_date in the
            # signed payload, not by per-tier feature limits.
            'trial': {
                'daily_query_limit': 50,
                'max_providers': 2,
                'max_concurrent_queries': 2,
                'history_retention_days': 7,
                'max_templates': 10,
                'base_seats': 1,
                'cache_ttl_seconds': 900,
                'allow_extra_seats': False
            },
            'starter': {
                'daily_query_limit': 50,
                'max_providers': 1,
                'max_concurrent_queries': 2,
                'history_retention_days': 7,
                'max_templates': 5,
                'base_seats': 1,
                'cache_ttl_seconds': 900,
                'allow_extra_seats': False
            },
            # New RST License Server tier (slots between starter and
            # professional). Adjust if the official tier matrix changes.
            'standard': {
                'daily_query_limit': 200,
                'max_providers': 3,
                'max_concurrent_queries': 5,
                'history_retention_days': 14,
                'max_templates': 15,
                'base_seats': 2,
                'cache_ttl_seconds': 3600,
                'allow_extra_seats': False
            },
            'professional': {
                'daily_query_limit': 500,
                'max_providers': 5,
                'max_concurrent_queries': 10,
                'history_retention_days': 30,
                'max_templates': 30,
                'base_seats': 3,
                'cache_ttl_seconds': 14400,
                'allow_extra_seats': True,
                'extra_seat_price_cny_month': 199,
                'extra_seat_price_usd_month': 29
            },
            'enterprise': {
                'daily_query_limit': -1,
                'max_providers': -1,
                'max_concurrent_queries': 30,
                'history_retention_days': 365,
                'max_templates': -1,
                'base_seats': 5,
                'cache_ttl_seconds': 86400,
                'allow_extra_seats': True,
                'extra_seat_price_cny_month': 399,
                'extra_seat_price_usd_month': 59
            }
        }

        if license_type not in limits_by_type:
            logger.warning(
                "Unknown license_type %r — falling back to starter limits", license_type_raw
            )
            return default_limits
        return limits_by_type[license_type]

    def _check_provider_limit(self):
        """Check if adding a new provider would exceed the limit.

        Raises:
            admin.AdminManagerException: If limit would be exceeded
        """
        limits = self._get_license_limits()
        max_providers = limits.get('max_providers', 1)

        # -1 means unlimited
        if max_providers == -1:
            return

        try:
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            current_count = len(kv_client.query(limit=200))

            if current_count >= max_providers:
                license_data = self._get_license_data()
                license_type = license_data.get('license_type', 'starter') if license_data else 'starter'
                raise admin.AdminManagerException(
                    f"Provider limit reached ({current_count}/{max_providers}). "
                    f"Your {license_type} license allows up to {max_providers} provider(s). "
                    f"Please upgrade your license to add more providers."
                )
        except admin.AdminManagerException:
            raise
        except Exception as e:
            logger.error(f"Failed to check provider limit: {e}")

    def _check_template_limit(self):
        """Check if adding a new template would exceed the limit.

        Raises:
            admin.AdminManagerException: If limit would be exceeded
        """
        limits = self._get_license_limits()
        max_templates = limits.get('max_templates', 5)

        # -1 means unlimited
        if max_templates == -1:
            return

        try:
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            current_count = len(kv_client.query(limit=200))

            if current_count >= max_templates:
                license_data = self._get_license_data()
                license_type = license_data.get('license_type', 'starter') if license_data else 'starter'
                raise admin.AdminManagerException(
                    f"Template limit reached ({current_count}/{max_templates}). "
                    f"Your {license_type} license allows up to {max_templates} template(s). "
                    f"Please upgrade your license to add more templates."
                )
        except admin.AdminManagerException:
            raise
        except Exception as e:
            logger.error(f"Failed to check template limit: {e}")

    def _check_daily_query_limit(self):
        """Check if executing a query would exceed the daily limit.

        Raises:
            admin.AdminManagerException: If limit would be exceeded
        """
        from usage_tracker import get_daily_query_count

        limits = self._get_license_limits()
        daily_limit = limits.get('daily_query_limit', -1)

        # -1 means unlimited
        if daily_limit == -1:
            return

        user = getattr(self, 'userName', None) or 'unknown'
        current_count = get_daily_query_count(user)

        if current_count >= daily_limit:
            license_data = self._get_license_data()
            license_type = license_data.get('license_type', 'starter') if license_data else 'starter'
            raise admin.AdminManagerException(
                f"Daily query limit reached ({current_count}/{daily_limit}). "
                f"Your {license_type} license allows up to {daily_limit} queries per day. "
                f"Please upgrade your license or wait until tomorrow."
            )

    def _check_concurrent_query_limit(self):
        """Check if starting a query would exceed the concurrent limit.

        Raises:
            admin.AdminManagerException: If limit would be exceeded
        """
        from usage_tracker import get_concurrent_query_count

        limits = self._get_license_limits()
        concurrent_limit = limits.get('max_concurrent_queries', 5)

        user = getattr(self, 'userName', None) or 'unknown'
        current_count = get_concurrent_query_count(user)

        if current_count >= concurrent_limit:
            license_data = self._get_license_data()
            license_type = license_data.get('license_type', 'starter') if license_data else 'starter'
            raise admin.AdminManagerException(
                f"Concurrent query limit reached ({current_count}/{concurrent_limit}). "
                f"Your {license_type} license allows up to {concurrent_limit} concurrent queries. "
                f"Please wait for existing queries to complete or upgrade your license."
            )

    def _update_default_provider_id(self, provider_id):
        try:
            ent = entity.getEntity(
                '/configs/conf-mcp', 'ai',
                namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                sessionKey=self.getSessionKey()
            )
            ent['default_provider_id'] = provider_id
            entity.setEntity(ent, sessionKey=self.getSessionKey())
        except Exception as e:
            logger.warning(f"Failed to update default_provider_id: {e}")
