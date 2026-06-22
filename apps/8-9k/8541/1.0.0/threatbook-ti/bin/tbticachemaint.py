"""tbticachemaint - Scheduled maintenance: auto cache cleanup."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import threatbook_ti_declare  # noqa: F401

from splunklib.searchcommands import dispatch, Configuration, EventingCommand
from threatbook_ti.core.environment import SplunkEnv
from threatbook_ti.core import constants
from threatbook_ti.core import system_log


def _run_auto_cleanup(env, now_ts):
    auto_enabled = env.get_config_value(
        constants.CACHE_STANZA, constants.CONFIG_AUTO_CLEANUP_ENABLED, 'true',
    )
    records_deleted = 0

    if str(auto_enabled).strip().lower() not in ('true', '1'):
        return records_deleted

    cleanup_days = env.get_config_value(
        constants.CACHE_STANZA, constants.CONFIG_AUTO_CLEANUP_TIME, 90,
    )
    try:
        cleanup_days = int(cleanup_days)
    except (TypeError, ValueError):
        cleanup_days = 90

    cutoff_ts = now_ts - cleanup_days * 86400
    query = json.dumps({'_created_at': {'$lt': cutoff_ts}})

    for coll_name in constants.ALL_CACHE_COLLECTIONS:
        try:
            coll = env.service.kvstore[coll_name]
            old_records = coll.data.query(query=query)
        except Exception as exc:
            detail = str(exc)
            system_log.log_event(
                'internal_error',
                f'Internal error in cache_manager: {detail}.',
                module='cache_manager',
                error_detail=detail,
            )
            continue

        for rec in old_records:
            try:
                coll.data.delete_by_id(rec['_key'])
                records_deleted += 1
            except Exception as exc:
                detail = str(exc)
                system_log.log_event(
                    'internal_error',
                    f'Internal error in cache_manager: {detail}.',
                    module='cache_manager',
                    error_detail=detail,
                )

    if records_deleted > 0:
        system_log.log_event(
            'cache_flush',
            f'Cache flushed by auto, {records_deleted} records removed.',
            flushed_by='auto',
            affected_records=records_deleted,
            module='cache_manager',
        )
    return records_deleted


@Configuration()
class TbtiCacheMaintCommand(EventingCommand):
    """Scheduled maintenance command.

    Delete cache records older than auto_cleanup_time days (if enabled).
    """

    def transform(self, records):
        system_log.refresh_system_logger()
        env = SplunkEnv(self._metadata.searchinfo.session_key)
        now_ts = int(time.time())
        records_deleted = _run_auto_cleanup(env, now_ts)

        yield {
            'cache_records_deleted': records_deleted,
            'timestamp': now_ts,
        }


if __name__ == '__main__':
    dispatch(TbtiCacheMaintCommand, sys.argv, sys.stdin, sys.stdout, __name__)
