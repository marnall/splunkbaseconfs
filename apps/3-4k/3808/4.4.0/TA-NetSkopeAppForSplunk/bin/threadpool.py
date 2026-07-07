import sys
from threading import Thread

IS_PY2 = sys.version_info < (3, 0)

if IS_PY2:
    from Queue import Queue
else:
    from queue import Queue


class Worker(Thread):
    """Execute tasks from a given tasks queue."""

    def __init__(self, tasks, helper):
        """Construct resources."""
        Thread.__init__(self)
        self.helper = helper
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        """Run main method."""
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as e:
                self.helper.log_error("Error occured {}".format(e))
            finally:
                self.tasks.task_done()


class ThreadPool(object):
    """Pool of threads consuming tasks from a queue."""

    def __init__(self, num_threads, helper):
        """Construct resources."""
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks, helper)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue."""
        self.tasks.put((func, args, kargs))

    def map(self, func, args_list):
        """Add a list of tasks to the queue."""
        for args in args_list:
            self.add_task(func, args)

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue."""
        self.tasks.join()
