"""Custom UCC hooks for settings audit logging."""

from threatbook_ti.api import correlation
from threatbook_ti.core import audit_log
from threatbook_ti.core import constants

try:
    from threatbook_ti.core.environment import SplunkEnv
except Exception:
    SplunkEnv = None


def _to_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'yes'}


def _normalize_level(value):
    level = str(value or '').strip().upper()
    return level or 'ERROR'


def _normalize_region(value):
    return str(value or '').strip().lower()


def _build_env(session_key):
    env_cls = SplunkEnv
    if env_cls is None:
        from threatbook_ti.core.environment import SplunkEnv as env_cls
    return env_cls(session_key)


def _pause_tasks_for_region_change(session_key, new_region):
    env = _build_env(session_key)
    correlation.pause_tasks_for_region_change(env, new_region)


class CustomHookMixin:
    """Emit audit actions for settings create/edit operations."""

    def _operator(self):
        return getattr(self, 'userName', None) or getattr(self, 'user', None)

    @staticmethod
    def _emit_for_stanza(stanza, payload, operator, session_key=None):
        if stanza == constants.PROXY_STANZA:
            audit_log.log_action('update_proxy', 'Proxy settings updated.', operator=operator)
            return

        if stanza == constants.BASIC_STANZA:
            if constants.CONFIG_API_REGION in payload and session_key:
                env = _build_env(session_key)
                current_region = _normalize_region(
                    env.get_config_value(
                        constants.BASIC_STANZA,
                        constants.CONFIG_API_REGION,
                        'china',
                    )
                )
                new_region = _normalize_region(payload.get(constants.CONFIG_API_REGION))
                if new_region and new_region != current_region:
                    _pause_tasks_for_region_change(session_key, new_region)
            if (
                constants.CONFIG_API_KEY_CHINA in payload
                or constants.CONFIG_API_KEY_GLOBAL in payload
            ):
                audit_log.log_action('update_api_key', 'API Key updated.', operator=operator)
            return

        if stanza == constants.CACHE_STANZA:
            if constants.CONFIG_CACHE_POLICY in payload:
                audit_log.log_action('update_cache_policy', 'Cache policy updated.', operator=operator)
            if constants.CONFIG_TTL_VALUE in payload:
                audit_log.log_action('update_cache_ttl', 'Cache TTL updated.', operator=operator)
            if constants.CONFIG_AUTO_CLEANUP_ENABLED in payload:
                audit_log.log_action('toggle_auto_cleanup', 'Auto cleanup setting updated.', operator=operator)
            if constants.CONFIG_AUTO_CLEANUP_TIME in payload:
                audit_log.log_action(
                    'auto_cleanup_time_update',
                    'Auto cleanup time setting updated.',
                    operator=operator,
                )
            return

        if stanza == constants.LOGGING_STANZA:
            if constants.CONFIG_SYSTEM_LOG_LEVEL in payload:
                level = _normalize_level(payload.get(constants.CONFIG_SYSTEM_LOG_LEVEL))
                audit_log.log_action(
                    'update_log_level',
                    f'System log level updated to {level}.',
                    operator=operator,
                )
            if constants.CONFIG_AUDIT_ENABLED in payload:
                state = 'enabled' if _to_bool(payload.get(constants.CONFIG_AUDIT_ENABLED)) else 'disabled'
                audit_log.log_action(
                    'toggle_audit_log',
                    f'Audit trail {state}.',
                    operator=operator,
                    force=True,
                )

    def create_hook(self, session_key, config_name, stanza_id, payload):
        self.edit_hook(session_key, config_name, stanza_id, payload)

    def edit_hook(self, session_key, config_name, stanza_id, payload):
        try:
            stanza = stanza_id or config_name
            body = payload if isinstance(payload, dict) else {}
            operator = self._operator()
            self._emit_for_stanza(stanza, body, operator, session_key=session_key)
        except Exception as err:
            reason = str(err)
            audit_log.log_action(
                'config_save_failed',
                f'Configuration save failed: {reason}.',
                operator=self._operator(),
                reason=reason,
                force=True,
            )

    def delete_hook(self, session_key, config_name, stanza_id):
        del session_key, config_name, stanza_id
        return
