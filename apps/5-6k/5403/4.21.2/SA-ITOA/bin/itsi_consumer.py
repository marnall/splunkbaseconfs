# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
"""
This is a re-implementation of the refresh queue that we had before, with the major change that this one is designed to be run
concurrently.  Itself, it will behave appropriately.  However, it is paramount that any new/existing refresh queues be audited for
the amount of risk that they can have.  Currently we have no transaction support from our supporting datastore, so
theres definitely a risk of race conditions.
"""
import json
import os
import signal
import sys
from abc import ABCMeta, abstractmethod
from multiprocessing.pool import ThreadPool
from time import time

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.rest import simpleRequest
from splunk import LicenseRestriction

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from SA_ITOA_app_common.solnlib.modular_input import ModularInput

from ITOA import itoa_refresh_queue_utils
from ITOA.itoa_common import modular_input_should_run
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import logger, InstrumentCall, getLogger4ModInput
from itsi.objects.changehandlers.handler_manifest import handler_manifest
from itsi.objects.itsi_refresh_queue_job import ItsiRefreshQueueJob
from kvstore_queue.kvstore_queue_consumer import DEFAULT_HIGH_JOB_RATIO, DEFAULT_JOB_TIMEOUT, DEFAULT_MAX_RETRIES, KVStoreQueueConsumer
from kvstore_queue.refresh_queue_status_reporter import report_refresh_queue_status

_instrumentation = InstrumentCall(logger)
# Flag used for generating the restartless testing logs only once.
modular_input_reloaded = False

DEFAULT_POOL_SIZE = 8
DEFAULT_QUEUE_SIZE_LOGGING_FREQUENCY = 600  # Minimum number of seconds between attempts to log the size of the queue
INCOMPLETE_JOB_CLEANUP_INTERVAL = 3600
QUEUE_METRICS_REPORT_INTERVAL = 86400


class JobProcessor(metaclass=ABCMeta):
    """
    Abstract interface for a job processor
    """

    @abstractmethod
    def preprocess_job(self, job_data, other_jobs):
        """
        Perform job preprocessing steps before execution.

        @param job_data: the current job object selected for processing
        @type job_data: dict

        @param other_jobs: list of other job objects in the queue; e.g. for deduplication
        @type other_jobs: list(dict)
        """

    @abstractmethod
    def process_job(self, job_data):
        """
        Perform job processing.

        @param job_data: Job data for processing
        @type job_data: dict

        @return: True if processing was successful, otherwise False
        @rtype: bool
        """


class JobDemultiplexer(JobProcessor):
    """
    De-Multiplexer for ITSI objects.  A user passes in a field that
    will select what action to run - the demultiplexer field (demux_field)
    Essentially the job type, but can be used for other things
    """

    def __init__(self, session_key, demux_field, number_of_thread=DEFAULT_POOL_SIZE):
        """
        Initialize the process object
        @param session_key: The splunkd session key
        @param demux_field: The field in the job data to demultiplex on
        @param number_of_thread: number of thread to allocate - must be a none-zero value
        """
        self.demux_field = demux_field
        self.session_key = session_key
        self.handler_manifest = handler_manifest
        if number_of_thread < 1:
            number_of_thread = DEFAULT_POOL_SIZE
        self.thread_pool = ThreadPool(processes=number_of_thread)
        self.refresh_queue_job_interface = ItsiRefreshQueueJob(self.session_key, 'nobody')
        self.last_size_logging_time = None

    def preprocess_job(self, job_data, other_jobs):
        """
        If the handler is configured to, check for duplicate jobs
        @param job_data: job object the handler is currently working on
        @param other_jobs: list of job objects in the queue
        @return: list of duplicate job objects
        @rtype List
        """
        job_changed_object_type = job_data.get("changed_object_type")
        job_change_key = job_data.get("changed_object_key")
        if job_changed_object_type and job_change_key:
            selector = job_data.get(self.demux_field, None)
            handler_object = self._get_handler(job_data, selector)(logger, self.session_key, self.thread_pool)
            should_remove_duplicates = getattr(handler_object, 'should_remove_duplicates', None)
            if should_remove_duplicates and callable(should_remove_duplicates) and should_remove_duplicates(job_data):
                duplicates = [job for job in other_jobs if job.get("changed_object_type") == job_changed_object_type
                              and job.get("changed_object_key") == job_change_key]
                return duplicates
        return []

    def process_job(self, job_data):
        """
        Using the demultiplexer field, process the job_data
        @param job_data: JSON data coming in to be processed.  In this case, it will be a refresh
        queue job
        @type job_data: Dictionary
        @return: Was this job successful?
        @rtype: Boolean
        """
        start_time = time()
        create_time = float(job_data.get("create_time"))
        job_change_type = job_data.get("change_type")
        job_change_key = job_data.get("changed_object_key", "Unknown Key")
        transaction_id = job_data.get("transaction_id", None)
        job_changed_object_type = job_data.get("changed_object_type", "Unknown Change Object Type")
        successful = False
        try:
            selector = job_data.get(self.demux_field, None)
            handler_object = self._get_handler(job_data, selector)(logger, self.session_key, self.thread_pool)
            handler_object.assert_valid_change_object(job_data)
            method_name = selector + ".deferred"
            with _instrumentation.track(method_name, transaction_id):
                itoa_refresh_queue_utils.process_map[os.getpid()] = job_data
                successful = handler_object.deferred(job_data, job_data.get("transaction_id"))
        except Exception:
            logger.exception(
                "Error processing job=%s change_type=%s tid=%s",
                job_data.get("_key"),
                job_data.get("change_type"),
                job_data.get("transaction_id"),
            )
            raise
        finally:
            # Remove current job context
            del itoa_refresh_queue_utils.process_map[os.getpid()]

            # Log the entire experience
            job_key = job_data.get("_key")
            end_time = time()
            job_time = end_time - start_time
            queue_time = job_data.get("queue_time")
            overall_time = end_time - create_time
            completion = "Successful" if successful else "Failed"
            number_of_failures = job_data.get("number_of_failures", 0)
            parent_job = job_data.get("parent_job", None)
            log_message = (
                "Transaction: Job %s: job_key=%s tid=%s job_change_type=%s job_changed_object_type=%s "
                "start_time=%s end_time=%s job_time=%s queue_time=%s transaction_time=%s job_change_key=%s "
                "create_time=%s handler_object=%s number_of_failures=%s parent_job=%s "
            )
            current_time = time()
            if self.last_size_logging_time is None \
                    or current_time - self.last_size_logging_time > DEFAULT_QUEUE_SIZE_LOGGING_FREQUENCY:
                self.last_size_logging_time = current_time
                current_queue_size = self.refresh_queue_job_interface.get_queue_size(
                    "nobody",
                    transaction_id=transaction_id
                )
                log_message += "current_queue_size=%s"
                logger.info(
                    log_message, completion, job_key, transaction_id, job_change_type,
                    job_changed_object_type, start_time, end_time, job_time, queue_time,
                    overall_time, job_change_key, create_time, type(handler_object).__name__,
                    number_of_failures, parent_job, current_queue_size,
                )
            else:
                logger.info(
                    log_message, completion, job_key, transaction_id, job_change_type,
                    job_changed_object_type, start_time, end_time, job_time, queue_time,
                    overall_time, job_change_key, create_time, type(handler_object).__name__,
                    number_of_failures, parent_job,
                )
        return successful

    def _get_handler(self, job_data, selector):
        """
        Get the handler class for job
        @param job_data: the refresh queue job object
        @param selector: the demux field
        @return: Handler class
        """
        key = job_data.get("_key")
        transaction_id = job_data.get('transaction_id')
        if selector is None:
            raise Exception("No selector found in data field=%s, key=%s, tid=%s" %
                            (self.demux_field, key, transaction_id))
        handler_class = self.handler_manifest.get(selector)
        if handler_class is None:
            raise Exception("No handler manifest could be found selector=%s, key=%s, tid=%s" %
                            (selector, key, transaction_id))
        return handler_class


class ItsiConsumerModularInput(ModularInput):
    """
    Modular input that processes job objects from the specified queue and collection
    """
    # Required options for Modular Input
    title = "ITSI Multiple Job Queue Processor"
    description = "Runs deferred operations to ensure consistency for ITSI knowledge objects."
    app = "SA-ITOA"
    name = "itsi_consumer"
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    process_jobs = True

    def __init__(self):
        """
        Basic constructor

        Initialize class and setup shutdown signals
        """
        super(ItsiConsumerModularInput, self).__init__()
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def extra_arguments(self):
        """
        Additional argument definitions required for the modular input class
        """
        return [
            {
                'name': "log_level",
                'title': 'Logging Level',
                'description': 'Logging level to use for logging errors (ERROR, WARNING, INFO, DEBUG)',
            },
            {
                'name': 'number_of_thread',
                'title': 'Number of Thread',
                'description': 'Sets the thread pool count, or the number of actions that can execute in parallel '
                               'within a single job. For example, multiple independent actions on different '
                               'entities can execute at once.',
            },
            {
                'name': 'high_job_ratio',
                'title': 'High Job Ratio',
                'description': 'Executes high priority jobs N:1 compared to normal priority jobs. Setting this value '
                               'to 0 causes all jobs to execute regardless of priority.',
            },
            {
                'name': 'job_timeout',
                'title': 'Job Timeout',
                'description': 'The maximum amount of time, in seconds, that a job can execute. Jobs that exceed '
                               'this time limit will not run, and generate a timeout error. Setting this value to 0 '
                               'turns off the job timeout.',
            },
            {
                'name': 'max_retries',
                'title': 'Max Retries',
                'description': 'The number of times a failed job can automatically attempt to run again. '
                               'Setting this value to 0 turns off retry attempts.',
            },
        ]

    # It may seem a little strange to have these wrapped, but the good reason is
    # So that we can do good unit testing around this feature
    def request_shc_members(self):
        """
        The reason that we split this up into a separate method is so that we can
        abstract everything else out and test it by overwriting this method
        """
        return simpleRequest('/services/shcluster/member/members',
                             sessionKey=self.session_key,
                             getargs={"output_mode": "json"},
                             raiseAllErrors=False)

    # It may seem a little strange to have these wrapped, but the good reason is
    # So that we can do good unit testing around this feature
    def request_input_conf_entries(self):
        """
        The reason that we split this up into a separate method is so that we can
        abstract everything else out and test it by overwriting this method
        """
        return simpleRequest('/services/properties/inputs',
                             sessionKey=self.session_key,
                             getargs={"output_mode": "json"},
                             raiseAllErrors=False)

    def unclaim_incomplete_jobs(self, localhost):
        """
        So, with multiple processing queues, what happens if one dies unexpectedly?  We need to
        find a way to
        1) Determine that the process has died
        2) Adjust all of its jobs to unclaimed
        3) Do this all within splunk.  The worst part.

        For 1, what we need to do is first compare what hosts are up and which ones are not.  Now,
        this is only possible as far as the different search heads share the same kvstore - which
        is only possible if they are clustered. That means that we can look through all of the
        hosts that we're informed of in our shc (or single instance) and see if there are any hosts
        in the list of jobs that are not in the list provided by splunk

        If there are any jobs assigned to hosts that don't exist, we put those back on the open
        market.

        Next, we look for jobs that are assigned to job processors that don't exist.
        Unfortunately, we can't check other hosts that well, but we can check our own host
        pretty easily.  So lets do that.  Once we have dead hosts and dead input stanzas covered,
        we've covered a large portion of the jobs.  The only thing that isn't covered are hosts up
        that have 0 jobs assigned to them (usually through user intervention).

        We'll need a special way of dealing with that case

        For 2, thats easy.  Just rewrite the job itself to take out the processing piece

        For 3, we'll be limited to conf files, the kvstore, etc.  Not great, but whatever
        """
        # Step 0: Are we a part of a shc?
        valid_hosts = []
        try:
            response, content = self.request_shc_members()
            if response.status != 200:
                # Assume that we are not a part of the search head cluster, just grab localhost
                is_shc = False  # noqa F842
                valid_hosts.append(localhost)
            else:
                is_shc = True  # noqa F842
                parsed_content = json.loads(content)
                for entry in parsed_content.get("entry", []):
                    entry_content = entry.get('content', {})
                    label = entry_content.get("label")
                    status = entry_content.get("status")
                    if label is not None and status == "Up":
                        valid_hosts.append(label)
        except LicenseRestriction:
            logger.exception("Must update your license. Continuing with localhost awareness only.")
            valid_hosts.append(localhost)
        # Step 1: Check for any hosts that are not a part of the shc.
        # Find jobs that are assigned to the dead hosts
        valid_local_workers = []
        response, content = self.request_input_conf_entries()
        if response.status == 200:
            # If we don't get status = 200, then we should skip any of the local workers
            parsed_content = json.loads(content)
            for entry in parsed_content.get("entry", []):
                entry_content = entry.get('name')
                if "itsi_consumer://" in entry_content:
                    valid_local_workers.append(entry_content + ":" + localhost)
        # Step 2: Check for any jobs that are assigned to workers not present on this host.
        if not hasattr(self, "refresh_queue_job_interface"):
            self.refresh_queue_job_interface = ItsiRefreshQueueJob(self.session_key, 'nobody')

        queue_jobs = self.refresh_queue_job_interface.get_bulk('nobody')
        redo_jobs = []
        for job in queue_jobs:
            processor = job.get("processor")
            if processor is None or len(processor) == 0:
                continue
            worker_host = processor[processor.rfind(":") + 1:]
            if worker_host not in valid_hosts:
                redo_jobs.append(job)
            elif processor not in valid_local_workers and worker_host == localhost:
                redo_jobs.append(job)

        # Individually save all of the jobs
        for job in redo_jobs:
            old_job = self.refresh_queue_job_interface.get('nobody', job['_key'])
            if old_job.get('processor') == job.get('processor'):
                # Step 3: For any jobs in 1 or 2,
                # nullify their workers (if they are not claimed by other workers)
                del old_job['processor']
                self.refresh_queue_job_interface.update('nobody', job['_key'], old_job)

    @skip_run_during_migration
    def do_run(self, stanzas):
        """
        Run the modular input
        """
        if len(stanzas) == 0:
            # The feature is disabled, no stanzas are present.
            return

        logger = getLogger4ModInput(stanzas)
        # log the message for restartless upgrade testing which can be useful while debugging.
        global modular_input_reloaded
        if not modular_input_reloaded:
            stanza_name = next(iter(stanzas.keys()))
            logger.info(f"Restartless upgrade - Reloaded modular input {stanza_name}")
            modular_input_reloaded = True
        # We only want the first instance of the stanza, it has the name that we want

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run itsi_consumer queue on this node")
            return

        stanza_name = next(iter(stanzas.keys()))
        stanza_config = next(iter(stanzas.values()))

        level = stanza_config.get("log_level")
        if level is not None:
            level = level.upper()
            if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
                level = "INFO"
            logger.setLevel(level)

        # A mostly unique identifier that will persist across different iterations
        # Here we're assuming that the stanza name itself is unique across stanza types
        # It could be a uuid though
        # Anything as long as it persists across reboots
        self.uuid = stanza_name + ":" + stanza_config.get("host")
        logger.debug("Running with uid=%s", self.uuid)

        try:
            number_of_thread = int(stanza_config.get("number_of_thread", DEFAULT_POOL_SIZE))
        except ValueError:
            number_of_thread = DEFAULT_POOL_SIZE
        try:
            high_job_ratio = int(stanza_config.get("high_job_ratio", DEFAULT_HIGH_JOB_RATIO))
            high_job_ratio = max(0, high_job_ratio)
        except ValueError:
            high_job_ratio = DEFAULT_HIGH_JOB_RATIO
        try:
            job_timeout = int(stanza_config.get("job_timeout", DEFAULT_JOB_TIMEOUT))
            job_timeout = max(0, job_timeout)
        except ValueError:
            job_timeout = DEFAULT_JOB_TIMEOUT
        try:
            max_retries = int(stanza_config.get("max_retries", DEFAULT_MAX_RETRIES))
            max_retries = max(0, max_retries)
        except ValueError:
            max_retries = DEFAULT_MAX_RETRIES

        logger.debug('number of thread is set to %s', number_of_thread)
        demux = JobDemultiplexer(self.session_key, 'change_type', number_of_thread)
        self.consumer = KVStoreQueueConsumer(
            self.session_key,
            logger,
            self.uuid,
            demux,
            high_job_ratio,
            job_timeout,
            max_retries,
        )
        # Next, wait for the kvstore to get up and running
        self.consumer.block_until_ready()
        last_incomplete_job_cleanup = None
        last_queue_metrics_report = None

        while self.process_jobs:
            try:
                self.consumer.process_job()
            except Exception as e:
                if "Splunkd daemon is not responding: " in str(e):
                    logger.warning('Connection issue while processing handler on uid=%s. "%s" If this message occurs '
                                   'only once, KV Store may still be initializing.', self.uuid, e)
                else:
                    logger.exception("Exception processing handler on uid=%s", self.uuid)
                # Once it is logged, we want to crash out and let splunk bring us back up
                raise
            end_time = time()

            if (last_incomplete_job_cleanup is None
                    or end_time - last_incomplete_job_cleanup > INCOMPLETE_JOB_CLEANUP_INTERVAL):
                logger.debug("Checking for cleanup on incomplete jobs uid=%s", self.uuid)
                self.unclaim_incomplete_jobs(stanza_config.get("host"))
                last_incomplete_job_cleanup = end_time

            if last_queue_metrics_report is None or end_time - last_queue_metrics_report > QUEUE_METRICS_REPORT_INTERVAL:
                report_refresh_queue_status(logger, self.session_key, "nobody")
                last_queue_metrics_report = end_time

        logger.info("Exit modular input uid=%s", self.uuid)

    # pylint: disable=unused-argument
    def shutdown(self, signum, frame):
        """
        Listen for signals and shutdown processing
        """
        logger.info(
            f"itsi_consumer received queue shutdown signal {signum}; "
            "finishing current job and exiting"
        )
        self.process_jobs = False


if __name__ == "__main__":
    worker = ItsiConsumerModularInput()
    worker.execute()
    sys.exit(0)
