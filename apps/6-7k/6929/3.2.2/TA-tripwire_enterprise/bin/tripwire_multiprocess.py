import csv
import glob
import gzip
import json
import logging
import os
import pickle
import shutil
import threading
import time
import zlib
from copy import copy
from datetime import timedelta
from io import open
from multiprocessing import Manager
from queue import Empty, Queue

from tripwire import ReportData, make_sure_path_exists
from tripwire_rest_api import TWRestAPI
from six.moves import range

MAX_RESULTS = 500000
MAX_PAGES = 5

logger = logging.getLogger('tripwire')


class CompressedCache:
    def __init__(self):
        self.started = False
        self._manager = None
        self._d = None

    def start(self):
        self._manager = Manager()
        self._d = self._manager.dict()
        self.started = True

    @property
    def manager(self):
        if not self.started:
            self.start()
        return self._manager

    @property
    def d(self):
        if not self.started:
            self.start()
        return self._d

    def __setitem__(self, key, value):
        self.d[key] = zlib.compress(pickle.dumps(value))

    def __getitem__(self, key):
        return pickle.loads(zlib.decompress(self.d[key]))

    def __contains__(self, key):
        return key in self.d

    def get(self, key, default=None):
        if key in self.d:
            return self.__getitem__(key)
        return default

    def keys(self):
        # NOTE: converting d.keys() to list(d.keys()) is unnecessary. Only making this change to silence
        # Splunk app readiness warnings
        return list(self.d.keys())


class DumpResultsThread(threading.Thread):
    def __init__(self, results, file_path):
        threading.Thread.__init__(self)
        self.results = results
        self.file_path = file_path

    def run(self):
        # ~296M on disk w/o gzip, ~7M with gzip
        f = gzip.open(self.file_path, 'w')
        try:
            f.write(json.dumps(self.results).encode('utf-8'))
        finally:
            f.close()
        logger.info(
            'Results dumped with %d entries to %s', len(self.results), self.file_path
        )
        self.results = []


class LargeResults:
    """We won't always be able to hold all the results in memory, so this class
    is designed to dump chunks of results periodically to disk.  The results
    will then be retrieved from disk when this class is iterated.
    """

    def __init__(
        self,
        name,
        cachedir,
        newer_only=False,
        permanent=False,
        timestamp_field=None,
        remove_dupes=False,
    ):
        self.results = []
        self.result_dump_thread = None
        self.num_results = 0
        self.num_new_results = 0
        self.name = name
        self.cachedir = os.path.join(cachedir, name)
        self.metadatadir = cachedir
        self.permanent = permanent
        self.timestamp_field = timestamp_field
        self.newer_only = newer_only
        self.remove_dupes = remove_dupes
        self.ids = set()
        # Clear the metadata file if we are resyncing so we get all results
        if not newer_only:
            metadata_file = self.metadata_file
            if os.path.isfile(metadata_file):
                os.remove(metadata_file)
        make_sure_path_exists(self.metadatadir)
        if not self.permanent:
            self.clear_cache_dir()
        else:
            make_sure_path_exists(self.cachedir)
        self.last_dt = None
        self.num_last_dt = 0
        logger.info('Using cache directory: %s', self.cachedir)
        self.num_files = 0
        # Iterate through existing cache files to obtain state
        if self.permanent or newer_only:
            files = glob.glob(os.path.join(self.cachedir, '%s-*.json.gz' % self.name))
            self.num_files = len(files)
            metadata_file = self.metadata_file
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.loads(f.read())
                    if self.permanent:
                        self.num_results = metadata['num_results']
                    self.last_dt = ReportData.isodatetime_to_datetime(
                        metadata['last_dt']
                    )
                    self.num_last_dt = metadata['num_last_dt']
            logger.info(
                '(%s) LargeResults preloaded with %d results from %d files',
                self.name,
                self.num_results,
                self.num_files,
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.permanent:
            self.clear_cache_dir()

    def __iter__(self):
        for i in range(self.num_files):
            file_path = self.get_cache_file(i + 1)
            logger.info('Opening results file: %s', file_path)
            results = self.read_file_cache(file_path)
            # We don't need this file anymore
            if not self.permanent:
                os.remove(file_path)
            for result in results:
                yield result

    @staticmethod
    def read_file_cache(file_path):
        f = gzip.open(file_path, 'r')
        try:
            return json.loads(f.read().decode('utf-8'))
        finally:
            f.close()

    def clear_cache_dir(self):
        if os.path.isdir(self.cachedir):
            shutil.rmtree(self.cachedir)
            logger.info('Cache directory removed: %s', self.cachedir)
        make_sure_path_exists(self.cachedir)

    def get_cache_file(self, num):
        return os.path.join(self.cachedir, '%s-%d.json.gz' % (self.name, num))

    @property
    def metadata_file(self):
        return os.path.join(self.metadatadir, '%s-metadata.json' % self.name)

    def add_result(self, result):
        thread_id, result = result
        # We could get duplicate entries if trying to use time ranges to avoid
        # pagination
        if not isinstance(result, list):
            result = [result]
        total = len(result)
        result = [r for r in result if r['id'] not in self.ids]
        if len(result) < total:
            logger.debug('Found %d duplicate items!', total - len(result))
        if not result:
            return
        self.results += result
        if self.remove_dupes:
            for r in result:
                self.ids.add(r['id'])
        num_results = len(result)
        logger.info('Added %d results', num_results)
        self.num_results += num_results
        self.num_new_results += num_results
        if len(self.results) > MAX_RESULTS:
            self.dump_results()
        if self.timestamp_field:
            for r in result:
                dt = ReportData.isodatetime_to_datetime(r[self.timestamp_field])
                if not self.last_dt or self.last_dt < dt:
                    self.last_dt = dt
                    self.num_last_dt = 0
                self.num_last_dt += 1

    def done(self):
        self.dump_results()
        with open(self.metadata_file, 'w') as f:
            f.write(
                json.dumps(
                    {
                        'last_dt': ReportData.datetime_to_isodatetime(self.last_dt),
                        'num_last_dt': self.num_last_dt,
                        'num_results': self.num_results,
                    }
                )
            )
        if self.result_dump_thread:
            self.result_dump_thread.join()

    def dump_results(self):
        if not self.results:
            logger.info('No results to dump')
            return
        self.num_files += 1
        file_path = self.get_cache_file(self.num_files)
        if self.result_dump_thread:
            self.result_dump_thread.join()
        self.result_dump_thread = DumpResultsThread(self.results, file_path)
        self.result_dump_thread.start()
        self.results = []


class GetPagesThread(threading.Thread):
    def __init__(
        self,
        id,
        name,
        work_q,
        result_q,
        report_data,
        url,
        params,
        dupe_params,
        page_interval=1,
        page_offset=0,
        max_pages=0,
    ):
        threading.Thread.__init__(self)
        self.id = id
        self.name = name
        self.work_q = work_q
        self.result_q = result_q
        self.report_data = report_data
        self.url = url
        self.params = copy(params)
        self.dupe_params = copy(dupe_params)
        self.page_interval = page_interval
        self.page_offset = page_offset
        self.max_pages = max_pages


class SplitGetPagesThread(GetPagesThread):
    def run(self):
        logger.info("(%s) Starting SplitGetPagesThread %d", self.name, self.id)
        self.report_data.api.get_pages(
            self.url,
            self.params,
            dupe_params=self.dupe_params,
            page_interval=self.page_interval,
            page_offset=self.page_offset,
            max_pages=self.max_pages,
            queue=self.result_q,
            thread_id=self.id,
        )
        logger.info("(%s) Finished SplitGetPagesThread %d", self.name, self.id)


class SplitGetPagesDupeParamsThread(GetPagesThread):
    def run(self):
        logger.info("(%s) Starting SplitGetPagesDupeParamThread %d", self.name, self.id)
        while not self.work_q.empty():
            dupe_params = self.work_q.get(block=False)
            self.report_data.api.get_pages(
                self.url,
                self.params,
                dupe_params=dupe_params,
                page_interval=self.page_interval,
                page_offset=self.page_offset,
                max_pages=self.max_pages,
                queue=self.result_q,
                thread_id=self.id,
            )
            self.work_q.task_done()
        logger.info("(%s) Finished SplitGetPagesDupeParamThread %d", self.name, self.id)


def _get_results(threads, result_queue, results, started_time, stats_file_name):
    with open(stats_file_name, 'a') as csv_stats:
        csv_writer = csv.writer(
            csv_stats, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL
        )
        end = False
        while True:
            try:
                result = result_queue.get(block=True, timeout=1)
                results.add_result(result)
                if logger.level >= logging.DEBUG:
                    elapsed = time.time() - started_time
                    if csv_writer:
                        csv_writer.writerow(
                            [
                                results.num_new_results,
                                elapsed,
                                results.num_new_results / elapsed,
                            ]
                        )
                    logger.debug(
                        '(%s) Retrieved %d records in %s seconds at %.3f '
                        'items/second',
                        results.name,
                        results.num_new_results,
                        elapsed,
                        results.num_new_results / elapsed,
                    )
            except Empty:
                if end:
                    break
                for thread in threads:
                    if thread.isAlive():
                        break
                else:
                    end = True
    logger.info(
        "(%s) Done getting results from queue. Waiting for threads to finish.",
        results.name,
    )
    for thread in threads:
        thread.join()
    logger.info("(%s) Final results retrieved", results.name)


def _split_get_pages(
    report_data,
    results,
    pool,
    url,
    params,
    dupe_params,
    timestamp_field=None,
    end_time=None,
    range_param=None,
):
    """Allows using a multiprocess pool to split up a single get_pages call"""
    page_interval = pool._processes
    result_q = Queue()
    threads = []
    work_qs = []
    max_pages = 0 if not timestamp_field else MAX_PAGES
    num_results = results.num_results
    started_time = time.time()
    stats_file_name = os.path.join(results.cachedir, '%s.csv' % results.name)
    if os.path.isfile(stats_file_name):
        os.remove(stats_file_name)
    # Whether or not we're finishing a datetime
    on_finish_dt = False
    while True:
        for i in range(pool._processes):
            work_q = Queue()
            work_qs.append(work_q)
            thread = SplitGetPagesThread(
                i + 1,
                results.name,
                work_q,
                result_q,
                report_data,
                url,
                params,
                dupe_params,
                page_interval,
                page_offset=i,
                max_pages=max_pages,
            )
            thread.start()
            threads.append(thread)

        _get_results(threads, result_q, results, started_time, stats_file_name)
        # It's theoretically only possible to get duplicate ids when we're
        # trying to finish a time
        if on_finish_dt:
            results.ids = set()
        # The REST API gets slower the higher your pageStart limit is
        # so we'll only get x number of pages in each thread, and start back at
        # 0 by changing our time range...
        if (
            (results.num_results > num_results or on_finish_dt)
            and timestamp_field
            and results.last_dt
        ):
            num_results = results.num_results
            if on_finish_dt:
                # Make a new date range starting at the last result we found
                time_range = TWRestAPI.make_date_range(
                    results.last_dt + timedelta(seconds=1), end_time
                )
                on_finish_dt = False
                max_pages = 0 if not timestamp_field else MAX_PAGES
                logger.debug('Shifting time range for %s' % timestamp_field)
            else:
                # Make a new date range to finish the last date time we saw
                # XXX: We could also skip results.num_last_dt
                time_range = TWRestAPI.make_date_range(
                    results.last_dt, results.last_dt + timedelta(seconds=1)
                )
                on_finish_dt = True
                # We need to retrieve ALL pages for this date
                max_pages = 0
                logger.debug('Finishing last %s' % timestamp_field)
            params[range_param] = time_range
            threads = []
            work_qs = []
            logger.debug('Made new date range %s', time_range)
            continue
        break
    results.done()


def _split_get_pages_dupe_params(report_data, results, pool, url, params, dupe_params):
    """Allows using a multiprocess pool to split up a get_pages call
    by dupe_params, such as in the case when filtering by many policy_id's
    """
    result_q = Queue()
    work_q = Queue()
    threads = []
    num_threads = pool._processes
    started_time = time.time()
    stats_file_name = os.path.join(results.cachedir, '%s.csv' % results.name)
    if os.path.isfile(stats_file_name):
        os.remove(stats_file_name)
    # Split our dupe_params up into groups of 10, otherwise the URL could get
    # too long.
    for param_group in [
        dupe_params[i : i + 10] for i in range(0, len(dupe_params), 10)
    ]:
        work_q.put(param_group)
    if work_q.qsize():
        for i in range(min(num_threads, work_q.qsize())):
            thread = SplitGetPagesDupeParamsThread(
                i + 1,
                results.name,
                work_q,
                result_q,
                report_data,
                url,
                params,
                dupe_params=[],
            )
            thread.start()
            threads.append(thread)
        _get_results(threads, result_q, results, started_time, stats_file_name)
    results.done()


def get_pages(
    report_data,
    results,
    pool,
    url,
    params,
    dupe_params,
    timestamp_field=None,
    end_time=None,
    range_param=None,
):
    if dupe_params and len(dupe_params) > 10:
        _split_get_pages_dupe_params(
            report_data, results, pool, url, params, dupe_params
        )
    else:
        _split_get_pages(
            report_data,
            results,
            pool,
            url,
            params,
            dupe_params,
            timestamp_field,
            end_time,
            range_param,
        )
    logger.info('Got %d %s', results.num_results, results.name)
