import asyncio
import contextvars
import functools
import pathlib
import time
from datetime import datetime
from enum import Enum
from io import BufferedReader
import json
import os
import re
import sys
import typing as t

from snapattack_api import ApiClient

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'lib'))
import splunklib.client as splunk_client
import splunklib.results as splunk_results

# This is only available when running within Splunk
try:
    import splunk.mining.dcutils
except:
    pass

APP_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SearchMode(Enum):
    NORMAL = 'normal'
    BLOCKING = 'blocking'
    ONESHOT = 'oneshot'


async def to_thread(func, *args, **kwargs):
    """
    Python 3.9+ function ported to 3.7

    Asynchronously run function *func* in a separate thread.
    Any *args and **kwargs supplied for this function are directly passed
    to *func*. Also, the current :class:`contextvars.Context` is propagated,
    allowing context variables from the main thread to be accessed in the
    separate thread.
    Return a coroutine that can be awaited to get the eventual result of *func*.
    """
    loop = asyncio.events.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


class SplunkApiClient(ApiClient):
    try:
        # Log using built-in Splunk logger
        logger = splunk.mining.dcutils.getLogger()
    except NameError:

        class Logger:
            def __getattr__(self, name):
                def f(msg=''):
                    print(f'{name}: {msg}')

                return f

        logger = Logger()

    def __init__(
        self, splunk_session_key: str, secret_realm: str = 'snapattack_client_app_realm', secret_id: str = 'api_key'
    ):
        # TODO: make host and port configurable
        self.client = splunk_client.connect(token=splunk_session_key, host='localhost', port=8089, app=APP_NAME)
        self.splunk_internal_excluded_fields = [
            '_bkt',
            '_cd',
            '_indextime',
            '_pre_msg',
            '_raw',
            '_serial',
            '_si',
            '_sourcetype',
            'date_hour',
            'date_mday',
            'date_minute',
            'date_month',
            'date_second',
            'date_wday',
            'date_year',
            'date_zone',
            'punct',
            'sourcetype',
            'source',
            'host',
            'tag::*',
            'timeendpos',
            'timestartpos',
            '_eventtype_color',
            '_subsecond',
        ]
        super().__init__(api_key=self._fetch_api_key(secret_realm, secret_id))
        self.max_search_time = self.config.getint('SETTINGS', 'MAX_SEARCH_TIME_SEC', fallback=900)
        self.max_job_size = self.mebibytes_to_bytes(self.config.getint('SETTINGS', 'JOB_SIZE_LIMIT_MB', fallback=500))
        self.max_concurrent_searches = self.config.getint('RANK', 'MAX_CONCURRENT_SEARCHES', fallback=5)
        self.max_results = self.config.getint('SETTINGS', 'MAX_RESULTS', fallback=5000)
        self.max_reachback = self.config.getint('SETTINGS', 'MAX_REACHBACK_SEC', fallback=0)

    @staticmethod
    def mebibytes_to_bytes(mb: int):
        return mb * 1024 * 1024

    @staticmethod
    def result_pager(job: splunk_client.Job, count=0) -> t.Dict[str, t.Any]:
        """Uses an offset to iterate through events while respecting Splunk API limits"""
        result_size = (
            int(job.state['content']['resultCount'])
            if count == 0
            else min(int(job.state['content']['resultCount']), count)
        )
        offset = 0
        while offset < result_size:
            for result in SplunkApiClient.buffered_read(job.results(count=count, offset=offset)):
                yield result
                offset += 1
        return

    @staticmethod
    def buffered_read(result_handle: t.BinaryIO) -> splunk_results.ResultsReader:
        """
        Returns a buffered response reader for significantly improved iteration performance
        """
        return splunk_results.ResultsReader(BufferedReader(result_handle))

    def dispatch_saved_search(self, search_name: str, wait=True, raise_for_failure=True, **kwargs):
        search = self.client.saved_searches[search_name]
        job = search.dispatch(**kwargs)
        self.logger.info(f'Executing savedsearch="{search_name}" job={job.name}')
        if wait:
            return self._wait_for_job(job, raise_for_failure)
        return True

    def _fetch_api_key(self, realm: str, username: str) -> str:
        for password in self.client.storage_passwords:
            if password.username == username and password.realm == realm:
                return password.clear_password
        raise RuntimeError('Unable to retrieve API Key from Splunk storage.')

    def _build_sanitized_query(self, query_text: str, limit=None, native=False) -> str:
        """Remove command segments that could disrupt result processing (e.g. fields, table, stats, chart, timechart)"""
        if not native:
            # Split by '|' except when within a quoted string
            split_by = r'[|](?=(?:[^\"]*\"[^\"]*\")*[^\"]*\Z)'
            parts = re.split(split_by, query_text)
            excluded = r'^\s*(fields|table|stats|chart|timechart)\s'
            query_text = '|'.join([part for part in parts if not re.search(excluded, part)])
        limit = f'| head {limit}' if limit else ''
        return (
            query_text
            + f'| rename _raw as raw | eval snapattack_unique_event_identifier=sha256(splunk_server."_".index."_"._cd) {limit}'
        )

    def fields_filter(self):
        exclude = '| fields - ' + ','.join(self.splunk_internal_excluded_fields)
        if self.send_log:
            return f'| fields * {exclude}'
        else:
            fields = ','.join(
                [
                    '_time',
                    'indextime',
                    'orig_source',
                    'orig_sourcetype',
                    'snapattack_analytic_guid',
                    'snapattack_analytic_last_updated',
                    'snapattack_analytic_mitre_tactics',
                    'snapattack_analytic_mitre_techniques',
                    'snapattack_analytic_name',
                    'snapattack_unique_event_identifier',
                    'snapattack_analytic_mitre_subtechniques',
                    'snapattack_analytic_version_id',
                ]
            )
            return f'| fields {fields} {exclude}'

    @staticmethod
    def _parse_date_string(date_time: str):
        return datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S.%f')

    def _wait_for_job(self, job: splunk_client.Job, raise_for_failure=True):
        while not job.is_done():
            job.refresh()
            time.sleep(1)
        if job.dispatchState == 'FAILED':
            error = (
                job.state.get('content', {}).get('messages', {}).get('error', 'An unknown Splunk error has occurred')
            )
            self.logger.error(f'Splunk job {job.name} failed to complete. {error}')
            if raise_for_failure:
                raise RuntimeError(error)
            else:
                return None
        results = list(self.result_pager(job))
        job.delete()
        return results

    async def default_results_handler(self, job: splunk_client.Job) -> t.List[t.Dict[str, t.Any]]:
        """
        Default result handler for async search jobs. Returns a list of results and deletes the job.

        Args:
            job (splunk_client.Job): Job Instance

        Returns:
            List[Dict[str, Any]]: List of results
        """
        results = list(self.result_pager(job))
        job.delete()
        return results

    async def create_search_job(
        self,
        query: str,
        earliest_time: str = '-24h',
        latest_time: str = 'now',
        auto_cancel_secs: int = 0,
        auto_finalize_event_count: str = 0,
        execution_mode: SearchMode = SearchMode.NORMAL,
        job_ttl_secs: int = 604800,
        max_search_time_secs: int = 900,
        sample_ratio: int = 1,
        timeout_retry_count: int = 3,
    ) -> splunk_client.Job:
        """
        Create a Splunk search job

        Args:
            query (str): The Splunk SPL query
            earliest_time (str, optional): Earliest time, can be epoch timestamp, relative modifier (-7d), or formatted time string. Defaults to '-24h'.
            latest_time (str, optional): Latest time, can be epoch timestamp, relative modifier (-7d), or formatted time string. Defaults to 'now'.
            auto_cancel_secs (int, optional): If specified, the job automatically cancels after this many seconds of inactivity. Defaults to 0.
            auto_finalize_event_count (str, optional): Auto-finalize the search after at least this many events are processed. Defaults to 0.
            execution_mode (SearchMode, optional): Search mode to use. Defaults to SearchMode.NORMAL, which creates a non-blocking job.
            job_ttl_secs (int, optional): The number of seconds to keep this search after processing has stopped. Defaults to 604800 (7 days).
            max_search_time_secs (int, optional): The number of seconds to run this search before finalizing. Defaults to 900.
            sample_ratio (int, optional): The sample ratio to use. Defaults to 1 (all).
            timeout_retry_count (int, optional): The number of times to retry in case of connection timeout. Defaults to 3.
        Returns:
            splunk_client.Job: An instance of the newly created Job
        """
        query_args = {
            'earliest_time': earliest_time,
            'latest_time': latest_time,
            'auto_cancel': auto_cancel_secs,
            'auto_finalize_ec': auto_finalize_event_count,
            'exec_mode': execution_mode.value,
            'timeout': job_ttl_secs,
            'max_time': max_search_time_secs,
            'sample_ratio': sample_ratio,
        }
        for _ in range(timeout_retry_count + 1):
            try:
                job = self.client.jobs.create(query, **query_args)
            except TimeoutError:
                await asyncio.sleep(5)
                continue
            else:
                break
        else:
            raise TimeoutError(f'[Errno 110] Connection timed out when trying to create Splunk job.')
        return job

    async def async_search(
        self,
        query: str,
        query_args: t.Dict[str, t.Any] = None,
        results_callback: t.Awaitable = None,
        results_args: t.Dict[str, t.Any] = None,
        progress_callback: t.Callable = None,
        progress_args: t.Dict[str, t.Any] = None,
        progress_polling_interval_secs: int = 1,
    ) -> t.Any:
        """
        Run a non-blocking Splunk search, monitor for completion while optionally running a progress update function, and then returning the results (default) or running
        a supplied result handler function.

        Args:
            query (str): The Splunk SPL query
            query_args (Dict[str, Any], optional): Dictionary of query arguments. Supported arguments:
                earliest_time (str, optional): Earliest time, can be epoch timestamp, relative modifier (-7d), or formatted time string. Defaults to '-24h'.
                latest_time (str, optional): Latest time, can be epoch timestamp, relative modifier (-7d), or formatted time string. Defaults to 'now'.
                auto_cancel_secs (int, optional): If specified, the job automatically cancels after this many seconds of inactivity. Defaults to 0.
                auto_finalize_event_count (str, optional): Auto-finalize the search after at least this many events are processed. Defaults to 0.
                execution_mode (SearchMode, optional): Search mode to use. Defaults to SearchMode.NORMAL, which creates a non-blocking job.
                job_ttl_secs (int, optional): The number of seconds to keep this search after processing has stopped. Defaults to 604800 (7 days).
                max_search_time_secs (int, optional): The number of seconds to run this search before finalizing. Defaults to 900.
                sample_ratio (int, optional): The sample ration to use. Defaults to 1 (all).
            results_callback (Awaitable, optional): The function to call when the search is complete. Defaults to returning a list of results. Signature:
                results_callback(job:splunk_client.Job, **kwargs)
            results_args (Dict[str, Any], optional): Arguments to send to results_callback function. Defaults to None.
            progress_callback (Callable, optional): The function to call for reporting job status updates at the defined polling interval. Defaults to None. Signature:
                progess_callback(job:splunk_client.Job, **kwargs)
            progress_args (Dict[str, Any], optional): Arguments to send to progress_callback function. Defaults to None.
            progress_polling_interval_secs (int, optional): Number of seconds between job status checks. Defaults to 1.

        Raises:
            RuntimeError: If the Splunk job fails, will raise an Exception rather than execute the callback

        Returns:
            Any: Results of results_callback execution
        """
        results_callback = results_callback or self.default_results_handler
        results_args = results_args or {}
        progress_args = progress_args or {}
        if not progress_callback:
            progress_callback = lambda *args, **kwargs: None
        if not query_args:
            query_args = {}
        job = await self.create_search_job(query, **query_args)
        while not job.is_done():
            await to_thread(progress_callback, job, **progress_args)
            await asyncio.sleep(progress_polling_interval_secs)
        if job.dispatchState == 'FAILED':
            raise RuntimeError(
                job.state.get('content', {}).get('messages', {}).get('error', 'An unknown Splunk error has occurred')
            )
        return await results_callback(job, **results_args)

    def save_to_file(self, data: t.Dict, filename: pathlib.Path):
        with filename.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=True)

    def search(self, query: str, earliest_time: str, latest_time: str) -> t.Generator[t.Dict[str, t.Any], None, None]:
        """
        Run a blocking search and stream results back from Splunk

        Args:
            query (str): The query string to run
            earliest_time (str): Earliest time, can be epoch timestamp, relative modifier (-7d), or formatted time string
            latest_time (str): Lastest time, can be epoch timestamp, relative modifier (-7d), or formatted time string

        Yields:
            Dict[str, Any]: individual events
        """
        results = self.buffered_read(
            self.client.jobs.oneshot(query, earliest_time=earliest_time, latest_time=latest_time, count=0)
        )
        for result in results:
            if isinstance(result, splunk_results.Message):
                self.logger.warn(f'{result.type}: {result.message}')
            elif isinstance(result, dict):
                yield result

    def is_native_query(self, analytic: dict):
        return (
            analytic.get('logsource', '') == 'Native'
            or analytic.get('search', '').startswith('|')
            or analytic.get('is_native', False)
        )

    @staticmethod
    def needs_search_prefix(search: str):
        return not search.lstrip().startswith('|') and not search.lstrip().startswith('search')
