import collections
import csv
import dataclasses
import datetime
import io
import os
import json
import pathlib
import re
import time
import typing as t
import uuid

from async_queue import apply_asyncio_queue

from splunk_api import SplunkApiClient


@dataclasses.dataclass
class JobParameters:
    max_concurrent_searches: int
    max_search_window_seconds: int
    search_latest_time: t.Optional[str]
    max_results_per_query: int
    search_timeout_seconds: int
    max_search_job_size_mb: int
    raw_logs: bool
    base_query_filter: str = None
    raw_logs_include_fields: t.List[str] = dataclasses.field(default_factory=list)
    raw_logs_exclude_fields: t.List[str] = dataclasses.field(default_factory=list)


class Scheduler(SplunkApiClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_type = self.RequestType.job
        self._job_kv = self.client.kvstore['snapattack_job']
        self._job_item_kv = self.client.kvstore['snapattack_job_item']

    def schedule_jobs(self):
        jobs = self.fetch_jobs()
        for job in jobs:
            self.acknowledge_job(job['guid'])
            self.execute_job(job['guid'], job['type'])
        return jobs

    def fetch_jobs(self):
        jobs = self.fetch_requested_items(self._request_type)
        for job_id, job in jobs.items():
            existing_job = self._job_kv.data.query(query={'guid': job_id})
            # TODO: We need a way to know if an existing job has been deleted and cancel it here
            if not existing_job and not job.get('deleted'):
                job['created_timestamp'] = datetime.datetime.now().timestamp()
                items = job.pop('items', []) or []
                self._job_kv.data.insert(job)
                for i in items:
                    i['snapattack_job_guid'] = job_id
                    i['status'] = self.JobStatus.NotStarted
                    i['item_ids'] = [i['id'] for i in (i.pop('indicators', []) or [])]
                    self._job_item_kv.data.insert(i)
        return self._job_kv.data.query(query={'status': self.JobStatus.Pending})

    def execute_job(self, job_id: str, type: str):
        """Dispatch the job in a new process"""
        self.dispatch_saved_search(f"SnapAttack Job Runner", wait=False, **{'args.guid': job_id, 'args.type': type})


class JobProcessor(SplunkApiClient):
    def __init__(self, *args, **kwargs):
        guid = kwargs.pop('guid', None)
        if not guid:
            raise RuntimeError('No job guid supplied to the processor')
        super().__init__(*args, **kwargs)
        self._guid = guid
        self._request_type = self.RequestType.job
        self._job_kv = self.client.kvstore['snapattack_job']
        self._job_item_kv = self.client.kvstore['snapattack_job_item']
        self.job = self._job_kv.data.query(query={'guid': self._guid})[0]

    def _update_job_status(self, key, status, detail=None):
        self._update_job_kv_record(
            key, dict(status=status, status_timestamp=datetime.datetime.now().timestamp(), status_detail=detail)
        )

    def _update_job_kv_record(self, key, data):
        self._update_kv_record(self._job_kv, key, data)

    def _update_kv_record(self, store, key, data):
        record = store.data.query(query={'_key': key})
        if not record:
            store.data.insert(data=dict(_key=key, **data))
        else:
            record[0].update(data)
            store.data.update(id=key, data=record[0])


class RankJobProcessor(JobProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = JobParameters(
            **{
                k: v
                for k, v in self.job['parameters'].items()
                if k in set(f.name for f in dataclasses.fields(JobParameters))
            }
        )
        self._temp_file_dir = self._get_temp_path()
        latest_time = (
            datetime.datetime.fromisoformat(self.parameters.search_latest_time.rstrip('Z')).replace(
                tzinfo=datetime.timezone.utc
            )
            if self.parameters.search_latest_time
            else datetime.datetime.now(tz=datetime.timezone.utc)
        )
        self.max_reachback = (
            min(self.max_reachback, self.parameters.max_search_window_seconds)
            if self.max_reachback
            else self.parameters.max_search_window_seconds
        )
        self._earliest_time = (latest_time - datetime.timedelta(seconds=self.max_reachback)).isoformat()
        self._latest_time = latest_time.isoformat()
        # base class parameter overrides
        self.send_log = self.send_log or self.parameters.raw_logs
        self.max_search_time = min(self.max_search_time, self.parameters.search_timeout_seconds)
        self.max_job_size = min(
            self.max_job_size, self.mebibytes_to_bytes(self.parameters.max_search_job_size_mb * 1024 * 1024)
        )
        self.max_concurrent_searches = min(self.max_concurrent_searches, self.parameters.max_concurrent_searches)

    def process_job(self):
        start = time.time()
        # This has caused numerous issues when run on very large Splunk instances, and we're eventually removing from SA anyway.
        total_event_count = 0
        host_count = 0
        items = self.fetch_job()
        self._update_job_status(
            self.job['_key'], status=self.JobStatus.Started, detail=f'Dispatching {len(items)} searches.'
        )
        tasks = []
        for item in items:
            tasks.append(self.execute_search(item))
            self._update_item_kv_record(item.get('_key'), dict(status=self.JobStatus.Pending))
        if tasks:
            apply_asyncio_queue(
                tasks,
                self.max_concurrent_searches,
                exception_callback=self._exception_handler,
                result_callback=self._async_result_handler,
            )
        end = time.time()
        return self.finalize_job(total_duration=int(end - start), event_count=total_event_count, host_count=host_count)

    def fetch_job(self):
        items = self._job_item_kv.data.query(
            query={'snapattack_job_guid': self._guid, 'status': self.JobStatus.NotStarted}
        )
        return items

    def finalize_job(self, total_duration: int, event_count: int, host_count: int):
        self._update_job_progress()
        status_result = self.dispatch_saved_search(
            'Job Runner - Final Status', raise_for_failure=True, **{'args.guid': self._guid}
        )[0]
        dispatch_errors = status_result.get('dispatch_errors', [])
        if not isinstance(dispatch_errors, list):
            dispatch_errors = [dispatch_errors]
        status_result['dispatch_errors'] = {
            i.split(":", maxsplit=1)[0]: i.split(":", maxsplit=1)[1] for i in dispatch_errors if i
        }
        payload = dict(
            total_event_count=event_count, host_count=host_count, total_job_duration=total_duration, **status_result
        )
        self.submit_job_result(self._guid, payload, self._temp_file_dir)
        self.logger.info(f'Finalized job {self._guid} - {payload}')
        self._job_kv.data.delete(query=json.dumps({'guid': self._guid}))
        self._job_item_kv.data.delete(query=json.dumps({'snapattack_job_guid': self._guid}))
        return payload

    async def execute_search(self, job_item):
        job_item_id = job_item.get('_key')
        if not self._fetch_job_status():
            # If the job is gone, cancel the search task
            raise RuntimeError('Job was cancelled before executing.')
        self.logger.info(f'Dispatching job item {job_item_id} for job {self._guid}')
        is_native = self.is_native_query(job_item)
        search = self._eval_adhoc_fields(job_item, job_item.get('search'))
        search = self._build_sanitized_query(search, limit=self.parameters.max_results_per_query, native=is_native)
        fields = self.fields_filter()
        query = (
            f'search `sa_base_index_filter` {self.parameters.base_query_filter or ""} {search} {fields}'
            if self.needs_search_prefix(search)
            else f'{search} {fields}'
        )
        try:
            self._update_item_status(
                job_item_id, status=self.JobStatus.Started, started_timestamp=datetime.datetime.now().timestamp()
            )
            duration, results = await self.async_search(
                query,
                {
                    'earliest_time': self._earliest_time,
                    'latest_time': self._latest_time,
                    'max_search_time_secs': self.max_search_time,
                    'job_ttl_secs': 300,
                },
                results_callback=self._splunk_job_handler,
                progress_callback=self._update_progress,
                results_args={'job_item': job_item},
            )
        except Exception as ex:
            self._exception_handler(ex, job_item_id)
            raise
        return job_item_id, duration, results

    def _eval_adhoc_fields(self, job, query):
        analytic = (
            f''', snapattack_analytic_guid="{job.get('analytic_guid')}"'''
            if 'analytic_guid' in job
            else f''', snapattack_analytic_guid="{job.get('guid')}"'''
        )
        name = f''', snapattack_analytic_name="{job.get('name')}"''' if 'name' in job else ''
        version_id = f''', snapattack_analytic_version_id="{job.get('version_id')}"''' if 'version_id' in job else ''
        eval_string = f''' | eval orig_source=source, orig_sourcetype=sourcetype{analytic}{name}{version_id}'''
        return query + eval_string

    def _fetch_job_status(self):
        return self._job_kv.data.query(query={'guid': self._guid})

    def _update_item_status(
        self,
        key,
        status,
        detail=None,
        started_timestamp=None,
        completed_timestamp=None,
    ):
        self._update_item_kv_record(
            key,
            dict(
                status=status,
                status_timestamp=datetime.datetime.now().timestamp(),
                status_detail=detail,
                started_timestamp=started_timestamp,
                completed_timestamp=completed_timestamp,
            ),
        )

    def _update_item_kv_record(self, key, data):
        self._update_kv_record(self._job_item_kv, key, data)

    def _exception_handler(self, ex: Exception, key: str = None):
        msg = str(ex)
        self.logger.exception(msg=msg)
        if key:
            self._update_item_status(
                key, status=self.JobStatus.Failed, detail=msg, completed_timestamp=datetime.datetime.now().timestamp()
            )

    def _async_result_handler(self, results):
        job_item_id, duration, result_list = results
        data = dict(
            status=self.JobStatus.Success,
            completed_timestamp=datetime.datetime.now().timestamp(),
            hits=len([i for i in result_list if not i.get('snapattack_null')]),
            duration=duration,
        )
        self._update_item_kv_record(job_item_id, data)
        output = dict(results=result_list)
        if result_list and self._temp_file_dir:
            self.save_to_file(
                output,
                self._temp_file_dir / f'{int(datetime.datetime.utcnow().timestamp())}_{job_item_id}_analytic.export',
            )
        self.logger.info(f'Completed job item {job_item_id} for job {self._guid} with {len(result_list)} results.')
        self._update_job_progress()

    def _update_job_progress(self):
        status_result = self.dispatch_saved_search(
            'Job Runner - Item Status', raise_for_failure=True, **{'args.guid': self._guid}
        )
        status_dict = dict(Started=0, Pending=0, Success=0, Failed=0)
        item_status = []
        for item in status_result:
            # We have an extra unreported state used during Splunk processing that we need to coalesce
            item['status'] = self.JobStatus.Pending if item['status'] == self.JobStatus.NotStarted else item['status']
            status_dict[item['status']] += 1
            item_ids = item.get('item_ids')
            item_status.append(
                dict(
                    guid=item['guid'],
                    state=item['status'],
                    detail=item.get('status_detail'),
                    start_time=item.get('started_timestamp'),
                    end_time=item.get('completed_timestamp'),
                    hits=item.get('hits'),
                    **(dict(item_ids=item_ids if isinstance(item_ids, list) else [item_ids]) if item_ids else {}),
                )
            )
        total_count = len(status_result)
        status = ' | '.join(f'{k}: {v}' for k, v in status_dict.items())
        status = f'Total: {total_count} | {status}'
        self.set_job_status(job_id=self._guid, status=self.JobStatus.Started, detail=status, item_status=item_status)
        self._update_job_status(self.job['_key'], status=self.JobStatus.Started, detail=status)

    def _get_temp_path(self):
        local_path = pathlib.Path(os.path.expandvars(self.config.get('RANK', 'TEMP_FILE_DIR'))) / str(uuid.uuid4())
        local_path.mkdir(parents=True, exist_ok=True)
        return local_path

    async def _splunk_job_handler(self, job, job_item=None):
        duration = float(job.content['runDuration'])
        result = await self.default_results_handler(job)
        always_include = [
            '_time',
            'row_id',
            'snapattack_unique_event_identifier',
            'snapattack_analytic_guid',
            'snapattack_analytic_name',
            'snapattack_analytic_version_id',
        ]
        if not result:
            result.append(
                {
                    'snapattack_null': True,
                    'snapattack_analytic_guid': job_item['guid'],
                    'snapattack_analytic_name': job_item['name'],
                    '_time': datetime.datetime.fromisoformat(self._latest_time).timestamp() - 1,
                }
            )
        events = []
        try:
            # if this is a stats or tstats aggregate with a count field, split event into multiple records up to maximum
            if re.search(r'\|\s+[t]?stats[^\|]+count\s', job_item['search']):
                new_result = []
                remaining = self.parameters.max_results_per_query
                for event in result:
                    num = int(event.get('count', 0))
                    if num:
                        for i in range(min(remaining, num)):
                            new_result.append(event)
                        remaining = max(remaining - num, 0)
                    if remaining == 0:
                        break
                result = new_result
        except:
            pass
        for event in result:
            if not self.send_log:
                event = {k: v for k, v in event.items() if k in always_include}
            else:
                if self.parameters.raw_logs_include_fields:
                    event = {
                        k: v for k, v in event.items() if k in self.parameters.raw_logs_include_fields + always_include
                    }
                if self.parameters.raw_logs_exclude_fields:
                    event = {k: v for k, v in event.items() if k not in self.parameters.raw_logs_exclude_fields}
            event['indextime'] = time.time()
            # Ensure time falls back to a time within the search window for reporting purposes
            event['_time'] = event.get('_time') or datetime.datetime.fromisoformat(self._earliest_time).timestamp() + 1
            event['snapattack_search_time'] = duration
            event['snapattack_analytic_last_updated'] = job_item['last_updated']
            event['snapattack_job_guid'] = self._guid
            events.append(event)
        return duration, events

    def _update_progress(self, job):
        # If we've exceeded the max job size, we need to cancel because the job may never be allowed to finish and will block everything else.
        job_size = int(job.state['content']['diskUsage'])
        if job_size > self.max_job_size:
            job.delete()
            raise RuntimeError(
                f'Job size of {job_size} exceeded max allowed size of {self.max_job_size}. Cancelling job.'
            )


class ImportJobProcessor(JobProcessor):
    native_import_fields = [
        'name',
        'description',
        'detection',
        'attack_names',
        'original_author',
        'severity',
        'unique_identifier',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._import_query = self.job['dispatch_options'].get('native_detection_import_query')

    def _import_native(self):
        detections = []
        for d in self.search(self._import_query, '-24h', 'now'):
            if 'name' in d:
                detections.append({k: v for k, v in d.items() if k in self.native_import_fields})
        if detections:
            csv_file = io.StringIO()
            dict_writer = csv.DictWriter(csv_file, self.native_import_fields)
            dict_writer.writeheader()
            dict_writer.writerows(detections)
        return self.import_native_detections(csv_file)

    def _update_status(self, status, msg):
        self.set_job_status(job_id=self._guid, status=status, detail=msg)
        self._update_job_status(self.job['_key'], status=status, detail=msg)

    def process_job(self):
        if not self._import_query:
            self._update_status(status=self.JobStatus.Canceled, msg='No query specified for native detections.')
            return
        try:
            self._update_status(status=self.JobStatus.Started, msg='Beginning Native Import.')
            results = self._import_native()
            self._update_status(status=self.JobStatus.Success, msg=str(results))
            return results
        except Exception as ex:
            import traceback

            msg = traceback.format_exc(limit=2)
            self._update_status(status=self.JobStatus.Failed, msg=f'Import failed: {str(ex)} {msg}')
            return []
        finally:
            self._job_kv.data.delete(query=json.dumps({'guid': self._guid}))
