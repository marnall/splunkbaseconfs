"""REST endpoint entry for ThreatBook config operations."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import threatbook_ti_declare  # noqa: F401

from threatbook_ti.api import config as config_api
from threatbook_ti.core import system_log
from threatbook_ti.core import request_context
from threatbook_ti.core import rest_response
from threatbook_ti.core.environment import SplunkEnv

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ModuleNotFoundError:
    # Allow local unit tests to parse/import this module outside Splunk runtime.
    class PersistentServerConnectionApplication:
        """Fallback stub for local test runtime."""

        pass

handlers = {
    'test_connectivity': (config_api.test_connectivity, SplunkEnv),
    'test_proxy': (config_api.test_proxy, SplunkEnv),
    'cache_flush': (config_api.cache_flush, SplunkEnv),
    'cache_kpi': (config_api.cache_kpi, SplunkEnv),
}

WRITE_ACTIONS = {'cache_flush'}
ALLOWED_WRITE_ROLES = {'admin', 'sc_admin'}


def _is_authorized_for_action(action, in_dict, env):
    if action not in WRITE_ACTIONS:
        return True

    roles = request_context.extract_roles(in_dict)
    if not roles:
        operator = request_context.extract_operator(in_dict)
        roles = request_context.fetch_roles_from_service(
            getattr(env, 'service', None),
            operator,
        )

    return bool(roles & ALLOWED_WRITE_ROLES)


class ThreatBookConfigHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def _render(self, payload, status):
        return rest_response.render(payload, status)

    def handle(self, in_string):
        system_log.refresh_system_logger()
        try:
            in_dict = json.loads(in_string)
        except Exception:
            system_log.log_event(
                'internal_error',
                'Internal error in config_manager: Failed to parse request body.',
                module='config_manager',
                error_detail='Failed to parse request body',
            )
            return self._render(
                rest_response.error('Failed parsing request'),
                500,
            )

        try:
            path_info = in_dict.get('path_info', '').strip('/')
            action = path_info.split('/')[-1] if path_info else ''
            operator = request_context.extract_operator(in_dict)
            if operator != '-':
                in_dict['operator'] = operator

            handler_func, env_class = handlers.get(action, (None, None))
            if handler_func is None:
                system_log.log_event(
                    'internal_error',
                    f'Internal error in config_manager: No handler found for path {path_info}.',
                    module='config_manager',
                    error_detail=f'No handler found for path {path_info}',
                )
                return self._render(
                    rest_response.error('Not Found'),
                    404,
                )

            env = env_class(in_dict['session']['authtoken']) if env_class else None
            if not _is_authorized_for_action(action, in_dict, env):
                return self._render(
                    rest_response.error('Forbidden'),
                    403,
                )
            result, status = handler_func(env, in_dict)
            if status >= 400:
                return self._render(
                    rest_response.error(
                        rest_response.extract_error_message(result, 'Request failed')
                    ),
                    status,
                )
            return self._render(rest_response.success(action, result), status)
        except Exception as err:
            detail = str(err)
            system_log.log_event(
                'internal_error',
                f'Internal error in config_manager: {detail}.',
                module='config_manager',
                error_detail=detail,
            )
            return self._render(
                rest_response.error(str(err)),
                500,
            )
