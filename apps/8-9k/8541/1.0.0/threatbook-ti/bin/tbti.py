"""tbti - ThreatBook TI enrichment StreamingCommand."""

import json
import os
import sys
import time
import ipaddress

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import threatbook_ti_declare  # noqa: F401

from splunklib.searchcommands import (
    dispatch, Configuration, StreamingCommand, Option, validators,
)
from threatbook_ti.core.environment import SplunkEnv
from threatbook_ti.core.http_client import ThreatBookClient
from threatbook_ti.core import constants
from threatbook_ti.core import system_log
from threatbook_ti.core import cache_policy as policy_mod
from threatbook_ti.core import cache_record_builder as builder
from threatbook_ti.core.cache import ThreatBookCache
from threatbook_ti.core.utils import detect_ioc_type
from threatbook_ti.api import router

API_FIELD_BINDING = {
    'compromise':       'ioc',
    'ip_reputation':    'ip',
    'url_reputation':   'url',
    'file_multiengine': 'hash',
}

QUERY_FIELDS     = ('ip', 'ioc', 'url', 'hash')
DEFAULT_TTL_VALUE = 24
BUFFER_SIZE       = 500

# 每个 API 输出字段的空值模板。
# 作用与 VT 的 init_vt_fields() 相同：预填所有 tb_* 字段让 Splunk
# 在第一条 record 就能发现字段，使 `table tb_*` 通配符能正常命中。
_EMPTY_TB_FIELDS = {
    'ip_reputation': {
        'tb_is_malicious': '', 'tb_confidence_level': '', 'tb_severity': '',
        'tb_judgments': [],    'tb_tags_classes': [],
        'tb_scene': '',
        'tb_country': '',      'tb_country_code': '', 'tb_province': '', 'tb_city': '',
    },
    'compromise': {
        'tb_is_malicious': '', 'tb_confidence_level': '', 'tb_severity': '',
        'tb_judgments': [],    'tb_tags_classes': [],
    },
    'file_multiengine': {
        'tb_threat_level': '',  'tb_is_white': '',        'tb_detected_engines': '',
        'tb_scanned_engines': '', 'tb_positives': '',     'tb_scan_date': '',
        'tb_malware_type': '',  'tb_malware_family': '',
    },
    'url_reputation': {
        'tb_threat_level': '',
        'tb_positives': '',              'tb_ratio': '',
        'tb_sandbox_threat_level': '',   'tb_sandbox_submit_time': '',
        'tb_sandbox_file_name': '',      'tb_sandbox_sample_sha256': '',
        'tb_sandbox_type_list': [],
    },
}


def _detect_ioc_type(value):
    """Backward-compatible wrapper (existing tests import this name)."""
    return detect_ioc_type(value)


def _get_ttl_seconds(env):
    """Read cache TTL config from the cache stanza and return seconds."""
    ttl_value = env.get_config_value(
        constants.CACHE_STANZA, constants.CONFIG_TTL_VALUE, DEFAULT_TTL_VALUE,
    )
    try:
        ttl_value = int(ttl_value)
        if ttl_value <= 0:
            raise ValueError('TTL must be positive')
    except (TypeError, ValueError):
        ttl_value = DEFAULT_TTL_VALUE

    return ttl_value * 60 * 60


def _is_private_ip(field_type, value):
    """Return True if value is a private/loopback IP that should be skipped.

    Returns False for non-IP field types, domain strings (ValueError from
    ipaddress) and invalid IP strings — they go through the normal query
    path (API will return empty, which is the correct fallback).
    """
    if field_type not in ('ip', 'ioc'):
        return False
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError:
        return False


def _extract_task_fields(sid, task_id, task_name=''):
    task_id = str(task_id or '').strip()
    if not task_id:
        return {}

    task_fields = {
        'tb_task_id': task_id,
        'sid': str(sid),
    }

    task_name = str(task_name or '').strip()
    if task_name:
        task_fields['task_name'] = task_name

    return task_fields


def _emit_task_start(task_fields):
    task_id = task_fields['tb_task_id']
    task_name = task_fields.get('task_name', '')
    system_log.log_event(
        'task_start',
        f'Task {task_id}({task_name}) started.',
        **task_fields,
    )


def _emit_task_end(task_fields, duration_ms, total_count, success_count):
    failed_count = max(total_count - success_count, 0)
    status = 'success' if failed_count == 0 else 'failed'
    task_id = task_fields['tb_task_id']
    task_name = task_fields.get('task_name', '')
    system_log.log_event(
        'task_end',
        f'Task {task_id}({task_name}) finished with status {status}.',
        status=status,
        duration_ms=duration_ms,
        total_count=total_count,
        success_count=success_count,
        failed_count=failed_count,
        **task_fields,
    )


def _persist_task_last_run(service, task_fields, _now_ts=None):
    task_id = task_fields.get('tb_task_id')
    if not task_id:
        return

    try:
        corr_cache = ThreatBookCache.for_correlation(service)
        corr_cache.update_last_run_at(task_id, int(_now_ts or time.time()))
    except Exception:
        pass


def _start_task_lifecycle(lifecycle, service, _now_ts=None):
    if lifecycle.get('started') or not lifecycle.get('fields'):
        return

    _emit_task_start(lifecycle['fields'])
    _persist_task_last_run(service, lifecycle['fields'], _now_ts=_now_ts)
    lifecycle['started'] = True
    lifecycle['run_start'] = _now_ts or time.time()


def _flush_batch(buffer, api, field_type, field_name,
                 client, ioc_cache, ttl_seconds, skip_cache,
                 cache_policy, api_region, extra, _now_ts=None,
                 task_fields=None, stats=None):
    """Process one buffer of records: cache check → API call → yield enriched.

    _now_ts is injectable for unit-testing; defaults to int(time.time()).
    """
    now_ts               = _now_ts if _now_ts is not None else int(time.time())
    result_map           = {}
    api_misses           = []
    existing_created_ats = {}
    unique_values        = []
    task_fields          = task_fields or {}

    for record in buffer:
        value = record.get(field_name)

        if not value or value in result_map:
            continue

        if _is_private_ip(field_type, value):
            result_map[value] = None
            continue

        result_map[value] = None
        unique_values.append(value)

    if stats is not None:
        stats['total_count'] = stats.get('total_count', 0) + len(unique_values)

    if unique_values and not skip_cache:
        result_map, api_misses, existing_created_ats = ioc_cache.query_batch(
            api, unique_values, now_ts,
        )
        hit_count = sum(1 for v in unique_values if result_map.get(v) is not None)
        miss_count = len(unique_values) - hit_count
        if hit_count:
            system_log.log_event(
                'cache_hit',
                f'Cache hit for {api}: {hit_count} values.',
                api_name=api, count=hit_count, **task_fields,
            )
        if miss_count:
            system_log.log_event(
                'cache_miss',
                f'Cache miss for {api}: {miss_count} values.',
                api_name=api, count=miss_count, **task_fields,
            )
    else:
        api_misses.extend(unique_values)

    if api_misses:
        api_results = router.batch_call(api, api_misses, client, **extra)
        to_save = []
        skip_count = 0

        for value, raw in api_results.items():
            if not raw:
                continue
            try:
                cache_obj = builder.build_cache_object(
                    api_name=api,
                    query_value=value,
                    api_result=raw,
                    ttl_seconds=ttl_seconds,
                    api_region=api_region,
                    cache_policy=cache_policy,
                    now_ts=now_ts,
                    existing_created_at=existing_created_ats.get(value),
                )
                result_map[value] = cache_obj
                if policy_mod.should_cache(api, raw, cache_policy):
                    to_save.append(cache_obj)
                else:
                    skip_count += 1
            except Exception as exc:
                detail = str(exc)
                system_log.log_event(
                    'internal_error',
                    f'Internal error in task_runner: {detail}.',
                    module='task_runner',
                    error_detail=detail,
                    **task_fields,
                )
                result_map[value] = raw

        if to_save:
            ioc_cache.save_batch(to_save)
            system_log.log_event(
                'cache_write',
                f'Cache updated for {api}: {len(to_save)} values, ttl={int(ttl_seconds / 3600)} hours.',
                api_name=api, count=len(to_save),
                ttl_value=int(ttl_seconds / 3600), **task_fields,
            )
        if skip_count:
            system_log.log_event(
                'cache_skip',
                f'Cache skipped for {api}: {skip_count} values.',
                api_name=api, count=skip_count, **task_fields,
            )

    if stats is not None:
        stats['success_count'] = stats.get('success_count', 0) + sum(
            1 for value in unique_values if result_map.get(value)
        )

    empty_fields = _EMPTY_TB_FIELDS.get(api, {})
    for record in buffer:
        value = record.get(field_name)
        # 预填空字段模板，让 Splunk 字段发现机制能识别 tb_* 通配符
        for k, v in empty_fields.items():
            record.setdefault(k, list(v) if isinstance(v, list) else v)
        enrichment = result_map.get(value)
        if value and enrichment:
            record.update(enrichment)
        yield record


@Configuration(distributed=False)
class TbtiCommand(StreamingCommand):
    """SPL usage:
      ... | tbti api=compromise ioc=<field>
      ... | tbti api=ip_reputation ip=<field>
      ... | tbti api=url_reputation url=<field>
      ... | tbti api=file_multiengine hash=<field>
      ... | tbti api=compromise ioc=<field> nocache=true
    """

    api = Option(
        doc='**Syntax:** api=<name>  **Description:** ThreatBook API to call',
        require=True,
    )
    ip = Option(
        doc='**Syntax:** ip=<field>  **Description:** IP field (use with api=ip_reputation)',
        validate=validators.Fieldname(),
    )
    ioc = Option(
        doc='**Syntax:** ioc=<field>  **Description:** IOC field - IP or domain (use with api=compromise)',
        validate=validators.Fieldname(),
    )
    url = Option(
        doc='**Syntax:** url=<field>  **Description:** URL field (use with api=url_reputation)',
        validate=validators.Fieldname(),
    )
    hash = Option(
        doc='**Syntax:** hash=<field>  **Description:** Hash field (use with api=file_multiengine)',
        validate=validators.Fieldname(),
    )
    nocache = Option(
        doc='**Syntax:** nocache=true  **Description:** Skip cache read (still writes cache)',
        default='false',
    )
    tb_task_id = Option(
        doc='**Syntax:** tb_task_id=<id>  **Description:** Correlation task id for task lifecycle logs',
    )
    tb_task_name = Option(
        doc='**Syntax:** tb_task_name=<name>  **Description:** Correlation task name for task lifecycle logs',
    )

    def prepare(self):
        # 将用户指定的查询字段声明为 required_fields，写入 getinfo 响应。
        # 若不声明，Splunk 的字段投影优化会在 table tb_* 等场景下
        # 将 ip/ioc/url/hash 字段在到达本命令前剥离，导致无法查询。
        # 必须使用 self._configuration.required_fields，而非 self.fieldnames；
        # 前者才会被 write_metadata 序列化到 getinfo 协议响应中。
        for f in QUERY_FIELDS:
            field_name = getattr(self, f, None)
            if field_name:
                self._configuration.required_fields = [field_name]
                break

    def stream(self, records):
        system_log.refresh_system_logger()

        api = self.api
        if api in constants.GLOBAL_APIS:
            self.write_error(f'api={api} is not supported by tbti. Use tbcti instead.')
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
            self.write_error('No query field specified. Use ip=, ioc=, url=, or hash=')
            return
        if len(present) > 1:
            self.write_error('Only one query field is allowed per command.')
            return

        field_type, field_name = present[0]

        expected = API_FIELD_BINDING[api]
        if field_type != expected:
            self.write_error(
                f'api={api} requires {expected}= field, got {field_type}='
            )
            return

        env          = SplunkEnv(self._metadata.searchinfo.session_key)
        client       = ThreatBookClient.from_env(env)
        ttl_seconds  = _get_ttl_seconds(env)
        skip_cache   = self.nocache == 'true'
        cache_policy = env.get_config_value(
            constants.CACHE_STANZA, constants.CONFIG_CACHE_POLICY,
            'store_all_successful_calls',
        )
        api_region_raw = env.get_config_value(
            constants.BASIC_STANZA, constants.CONFIG_API_REGION, 'china',
        )
        api_region = 'CN' if api_region_raw == 'china' else 'GLOBAL'
        ioc_cache  = ThreatBookCache.for_ioc(api, env.service)

        extra = {}
        if api == 'compromise':
            extra['lang'] = env.get_config_value(
                constants.BASIC_STANZA, constants.CONFIG_COMPROMISE_LANG, 'en',
            )
            extra['realtime_verdict'] = str(
                env.get_config_value(
                    constants.BASIC_STANZA,
                    constants.CONFIG_COMPROMISE_REALTIME_VERDICT,
                    'false',
                )
            ).lower() in ('true', '1')
        elif api == 'ip_reputation':
            extra['lang'] = env.get_config_value(
                constants.BASIC_STANZA, constants.CONFIG_IP_REPUTATION_LANG, 'en',
            )
            extra['realtime_verdict'] = str(
                env.get_config_value(
                    constants.BASIC_STANZA,
                    constants.CONFIG_IP_REPUTATION_REALTIME_VERDICT,
                    'false',
                )
            ).lower() in ('true', '1')

        sid = str(getattr(self._metadata.searchinfo, 'sid', ''))

        # stream() under SCPv2 may be invoked many times (chunked input).
        # Keep task lifecycle state on self to ensure one start/end per task run.
        if not hasattr(self, '_task_lifecycle'):
            initial_fields = _extract_task_fields(
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
        _start_task_lifecycle(lifecycle, env.service)

        buffer = []

        for record in records:
            if not lifecycle.get('started'):
                maybe_task_fields = _extract_task_fields(
                    sid=sid,
                    task_id=record.get('tb_task_id', ''),
                    task_name=record.get('task_name') or record.get('tb_task_name') or '',
                )
                if maybe_task_fields:
                    lifecycle['fields'] = maybe_task_fields
                    _start_task_lifecycle(lifecycle, env.service)

            buffer.append(record)
            if len(buffer) >= BUFFER_SIZE:
                yield from _flush_batch(
                    buffer, api, field_type, field_name,
                    client, ioc_cache, ttl_seconds, skip_cache,
                    cache_policy, api_region, extra,
                    task_fields=lifecycle['fields'],
                    stats=lifecycle['stats'],
                )
                buffer = []

        if buffer:
            yield from _flush_batch(
                buffer, api, field_type, field_name,
                client, ioc_cache, ttl_seconds, skip_cache,
                cache_policy, api_region, extra,
                task_fields=lifecycle['fields'],
                stats=lifecycle['stats'],
            )

        is_last_chunk = bool(getattr(self, '_finished', True))
        if is_last_chunk and lifecycle.get('started') and not lifecycle.get('ended'):
            run_start = lifecycle.get('run_start')
            duration_ms = int((time.time() - run_start) * 1000) if run_start else 0
            _emit_task_end(
                task_fields=lifecycle['fields'],
                duration_ms=duration_ms,
                total_count=lifecycle['stats']['total_count'],
                success_count=lifecycle['stats']['success_count'],
            )
            lifecycle['ended'] = True


if __name__ == '__main__':
    dispatch(TbtiCommand, sys.argv, sys.stdin, sys.stdout, __name__)
