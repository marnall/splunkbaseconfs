"""tbcti - ThreatBook Global IO enrichment StreamingCommand."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import threatbook_ti_declare  # noqa: F401

from splunklib.searchcommands import (
    dispatch, Configuration, StreamingCommand, Option, validators,
)
from threatbook_ti.core.environment import SplunkEnv
from threatbook_ti.core.http_client import ThreatBookClient
from threatbook_ti.core import constants
from threatbook_ti.core import system_log
from threatbook_ti.core.cache import ThreatBookCache
from threatbook_ti.api import router
import tbti as tbti_common


API_FIELD_BINDING = {
    'ip_intelligence': 'ip',
    'domain_intelligence': 'domain',
    'file_intelligence': 'hash',
    'url_intelligence': 'url',
}

QUERY_FIELDS = ('ip', 'domain', 'url', 'hash')
BUFFER_SIZE = tbti_common.BUFFER_SIZE


def _load_json_list(value):
    if value in (None, '', '[]'):
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


@Configuration(distributed=False)
class TbctiCommand(StreamingCommand):
    """Global IO enrichment search command."""

    api = Option(require=True)
    ip = Option(validate=validators.Fieldname())
    domain = Option(validate=validators.Fieldname())
    url = Option(validate=validators.Fieldname())
    hash = Option(validate=validators.Fieldname())
    nocache = Option(default='false')
    tb_task_id = Option()
    tb_task_name = Option()

    def prepare(self):
        for f in QUERY_FIELDS:
            field_name = getattr(self, f, None)
            if field_name:
                self._configuration.required_fields = [field_name]
                break

    def stream(self, records):
        system_log.refresh_system_logger()

        api = self.api
        if api in constants.CHINA_APIS:
            self.write_error(f'api={api} is not supported by tbcti. Use tbti instead.')
            return
        if api not in API_FIELD_BINDING:
            allowed = ', '.join(sorted(API_FIELD_BINDING))
            self.write_error(f'Unknown api={api}. Allowed: {allowed}')
            return

        present = [
            (f, getattr(self, f, None))
            for f in QUERY_FIELDS
            if getattr(self, f, None)
        ]
        if len(present) == 0:
            self.write_error('No query field specified. Use ip=, domain=, url=, or hash=')
            return
        if len(present) > 1:
            self.write_error('Only one query field is allowed per command.')
            return

        field_type, field_name = present[0]
        expected = API_FIELD_BINDING[api]
        if field_type != expected:
            self.write_error(f'api={api} requires {expected}= field, got {field_type}=')
            return

        env = SplunkEnv(self._metadata.searchinfo.session_key)
        api_region_raw = env.get_config_value(constants.BASIC_STANZA, constants.CONFIG_API_REGION, 'china')
        if api_region_raw != 'global':
            self.write_error('tbcti requires api_region=global in Basic configuration.')
            return

        client = ThreatBookClient.from_env(env)
        ttl_seconds = tbti_common._get_ttl_seconds(env)
        skip_cache = self.nocache == 'true'
        cache_policy = env.get_config_value(
            constants.CACHE_STANZA,
            constants.CONFIG_CACHE_POLICY,
            'store_all_successful_calls',
        )
        ioc_cache = ThreatBookCache.for_ioc(api, env.service)

        extra = {}
        if api == 'ip_intelligence':
            extra['exclude'] = _load_json_list(
                env.get_config_value(constants.BASIC_STANZA, constants.CONFIG_IP_INTELLIGENCE_EXCLUDE, '[]')
            )
        elif api == 'domain_intelligence':
            extra['exclude'] = _load_json_list(
                env.get_config_value(constants.BASIC_STANZA, constants.CONFIG_DOMAIN_INTELLIGENCE_EXCLUDE, '[]')
            )
        elif api == 'file_intelligence':
            extra['sandbox_type'] = env.get_config_value(
                constants.BASIC_STANZA,
                constants.CONFIG_FILE_INTELLIGENCE_SANDBOX_TYPE,
                '',
            )

        sid = str(getattr(self._metadata.searchinfo, 'sid', ''))
        if not hasattr(self, '_task_lifecycle'):
            initial_fields = tbti_common._extract_task_fields(
                sid=sid,
                task_id=getattr(self, 'tb_task_id', ''),
                task_name=getattr(self, 'tb_task_name', ''),
            )
            self._task_lifecycle = {
                'fields': initial_fields,
                'started': False,
                'ended': False,
                'run_start': None,
                'stats': {'total_count': 0, 'success_count': 0},
            }

        lifecycle = self._task_lifecycle
        tbti_common._start_task_lifecycle(lifecycle, env.service)
        buffer = []
        for record in records:
            buffer.append(record)
            if len(buffer) >= BUFFER_SIZE:
                yield from tbti_common._flush_batch(
                    buffer, api, field_type, field_name,
                    client, ioc_cache, ttl_seconds, skip_cache,
                    cache_policy, 'GLOBAL', extra,
                    task_fields=lifecycle['fields'],
                    stats=lifecycle['stats'],
                )
                buffer = []

        if buffer:
            yield from tbti_common._flush_batch(
                buffer, api, field_type, field_name,
                client, ioc_cache, ttl_seconds, skip_cache,
                cache_policy, 'GLOBAL', extra,
                task_fields=lifecycle['fields'],
                stats=lifecycle['stats'],
            )

        is_last_chunk = bool(getattr(self, '_finished', True))
        if is_last_chunk and lifecycle.get('started') and not lifecycle.get('ended'):
            run_start = lifecycle.get('run_start')
            duration_ms = int((time.time() - run_start) * 1000) if run_start else 0
            tbti_common._emit_task_end(
                task_fields=lifecycle['fields'],
                duration_ms=duration_ms,
                total_count=lifecycle['stats']['total_count'],
                success_count=lifecycle['stats']['success_count'],
            )
            lifecycle['ended'] = True


if __name__ == '__main__':
    dispatch(TbctiCommand, sys.argv, sys.stdin, sys.stdout, __name__)
