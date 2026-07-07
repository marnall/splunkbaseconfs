"""
A simple thread pool implementation
"""

import threading
import Queue
import multiprocessing
import logging


_LOGGER = logging.getLogger("data_loader")


class ThreadPool(object):
    """
    A simple thread pool implementation
    """

    def __init__(self, min_size):
        if not min_size or min_size <= 0:
            min_size = multiprocessing.cpu_count() * 4

        self.work_queue = Queue.Queue()
        self.thrs = []
        for _ in range(min_size):
            thr = threading.Thread(target=self._run)
            self.thrs.append(thr)
        self._lock = threading.Lock()

    def start(self):
        """
        Start threads in the pool
        """

        with self._lock:
            for thr in self.thrs:
                thr.start()

    def enqueue_jobs(self, jobs):
        """
        @jobs: tuple/list-like or generator like object, job shall be callable
        """

        for job in jobs:
            self.work_queue.put(job)

    def resize(self, new_size):
        """
        Resize the pool size, spawn or destroy threads if necessary
        """

        if new_size < 0:
            return

        with self._lock:
            self._remove_exited_threads_with_lock()
            size = len(self.thrs)
            if new_size > size:
                for _ in range(new_size - size):
                    thr = threading.Thread(target=self._run)
                    thr.start()
                    self.thrs.append(thr)
            elif new_size < size:
                for _ in range(size - new_size):
                    self.work_queue.put(None)

    def tear_down(self):
        """
        Tear down thread pool
        """

        with self._lock:
            for thr in self.thrs:
                self.work_queue.put(None)

            for thr in self.thrs:
                thr.join()

            del self.thrs[:]

    def _remove_exited_threads_with_lock(self):
        """
        Join the exited threads last time when resize was called
        """

        joined_thrs = set()
        for thr in self.thrs:
            if not thr.is_alive():
                try:
                    thr.join(timeout=0.5)
                    joined_thrs.add(thr.ident)
                except RuntimeError:
                    pass

        if joined_thrs:
            live_thrs = []
            for thr in self.thrs:
                if thr.ident not in joined_thrs:
                    live_thrs.append(thr)
            self.thrs = live_thrs

    def _run(self):
        """
        Threads callback func, run forever to handle jobs from the job queue
        """

        work_queue = self.work_queue
        while 1:
            job = work_queue.get()
            if job is None:
                _LOGGER.info("Worker thread %s going to exit",
                             threading.current_thread().getName())
                break
            _LOGGER.info("thread work_queue_size=%d", work_queue.qsize())
            try:
                job()
            except Exception:
                import traceback
                _LOGGER.error(traceback.format_exc())
