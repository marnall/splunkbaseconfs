# Standard library imports
import sys
import os
from threading import Thread

if sys.version_info < (3, 0):
    from Queue import Queue
else:
    from queue import Queue


class Worker(Thread):
    """ Thread executing tasks from a given tasks queue. """

    def __init__(self, tasks, logger):
        """
        Init method of Worker class.
        :param tasks: queue containing list of tasks
        """
        Thread.__init__(self)
        self.tasks = tasks
        self.logger = logger
        self.daemon = True
        self.start()

    def run(self):
        """
        Thread execution method.
        """
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as e:
                self.logger.error(
                    "Reach Error: Error occured while thread is running. Error: " + str(e))
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue. """

    def __init__(self, num_threads, logger):
        """
        Init method of ThreadPool class.
        :param num_threads: Number of threads to add in pool
        """
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks, logger)

    def add_task(self, func, *args, **kargs):
        """
        Add a task to the queue.
        :param func: function name to execute
        """
        self.tasks.put((func, args, kargs))

    def map(self, func, args_list):
        """
        Add a list of tasks to the queue.
        :param func: function name to execute
        :param args_list: list of arguments to pass in function
        """
        for args in args_list:
            self.add_task(func, args)

    def wait_completion(self):
        """
        Wait for completion of all the tasks in the queue.
        """
        self.tasks.join()
