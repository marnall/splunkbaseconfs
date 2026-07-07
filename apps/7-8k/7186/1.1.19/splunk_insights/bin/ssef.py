"""
The ssef custom search command orchestrates and runs a sequence of
searchbase.conf searches. It takes three primary arguments, jobs, checksgroup
and adhoc:

* jobs: comma-separated list of stanzas in searchbase.conf which will be executed
in parallel, via max_concurrent_jobs, with a default parallelization based on
the setup input (via setup.conf).
* checksgroup: a stanza in ssef.conf which contains a
comma-separated list of stanzas in searchbase.conf which will also be executed
in parallel, via max_concurrent_jobs, with a default parallelization of 1 (via
setup.conf).
* adhoc: a stanza in searchbase.conf which will be executed ad hoc,
similar to the | savedsearch command.

Note that jobs and checksgroup report statistics on the output and rely on the
search to save the results. Adhoc produces the search output.

time_from_searchbase: boolean argument to use searchbase to determine the
appropriate time range for the job

historical: boolean - true or other as to whether to log results in the configured
summary index

Based on the input, the checks_to_run are identified and executed. Throughout
the execution the command will log to ssef.log.

Time ranges of created search jobs are handled similar to the | savedsearch
command:
* When All-Time is provided:
  * When dispatch_earliest_time and/or dispatch_latest_time is provided in
    searchbase.conf - use these values
  * When dispatch_earliest_time is not provided, default to the last 24 hours
  * When dispatch_latest_time is not provided, default to now * If neither is
    provided in searchbase.conf, use All-Time
* When the command is executed with a time range (eg. -7days):
  * Use time range provided by the command for all downstream jobs

For legacy reasons, the terminology isn't as clean as it could be but the
current state is as follows:
- task_id, task_status describe the overall state of the ssef command execution
- job_name, job_status describe the state of the individual search jobs
"""

import sys
import time
import uuid
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)


from splunklib.results import JSONResultsReader
import splunklib.results as splunklib_results
from structlogger import StructuredContextualLogger

'''
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
'''


class TextOnlyWriter:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def write(self, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8", errors="replace")
        self.wrapped.write(s)

    def flush(self):
        self.wrapped.flush()


sys.stdout = TextOnlyWriter(sys.stdout)
sys.stderr = TextOnlyWriter(sys.stderr)


class SearchbaseCommandException(Exception):
    """
    General exception to be thrown by the ssef custom search command
    """


def setup_searchbase_logging():
    """
    Sets up the logger that writes to ssef.log
    """
    # setup logging
    splunk_home = os.environ.get("SPLUNK_HOME")
    initial_log_level = logging.DEBUG
    log_file_name = "ssef.log"

    log_format = (
        "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    )

    logger = StructuredContextualLogger("searchbase_logger", initial_log_level)
    logger.setLevel(initial_log_level)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(splunk_home, "var", "log", "splunk", log_file_name),
        mode="a",
        maxBytes=1000000,
        backupCount=2,
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


@Configuration(type="reporting")
class SearchbaseV2Command(GeneratingCommand):
    """
    Runs searches defined in searchbase
    """

    jobs = Option(validate=validators.List())
    checksgroup = Option()
    adhoc = Option()
    time_from_searchbase = Option(validate=validators.Boolean())
    timeout = Option(validate=validators.Integer())
    historical = Option()

    # Optional argument that will create a deterministic taskid
    taskid = Option()

    searchbase_logger = None
    task_id = None
    task_status = None
    searchbase_conf = None
    searchbase_conf_stanzas = None
    ssef_conf = None
    sid = None
    DEFAULT_TIME_RANGE = {
        "earliest_time": "-24h",
        "latest_time": "now",
    }
    ADHOC_CHECK_INTERVAL = 2  # seconds

    def generate(self):

        #dbg.set_breakpoint()
        self.load_searchbase_config()
        self.load_ssef_config()
        self.load_settings_config()
        self.validate_args()

        self.searchbase_logger = setup_searchbase_logging()
        self.task_id = self.taskid if self.taskid else str(uuid.uuid4())
        self.task_status = "STARTING"
        self.sid = self._metadata.searchinfo.sid

        checks_to_run = self.get_checks_to_run()
        validated_checks = self.validate_checks(checks_to_run)

        if self.checksgroup is not None and validated_checks == []:
            yield {"message": "No searches found matching this checksgroup"}
            return

        self.searchbase_logger.info(
            "initiating task run",
            extra={
                "task_status": self.task_status,
                "task_id": self.task_id,
                "task_sid": self.sid,
            },
        )

        self.task_status = "RUNNING"

        if self.adhoc:
            try:
                for result in self.execute_check_adhoc(checks_to_run[0]):
                    yield result
            except Exception as e:
                raise SearchbaseCommandException(
                    f"Error running ad hoc task: {str(e)}"
                ) from e
        else:
            max_concurrent_jobs = 5
            setting_conf_stanzas = [entry.name for entry in self.settings_conf]

            if "limits" in setting_conf_stanzas:
                max_concurrent_jobs = int(
                    self.settings_conf["limits"].max_concurrent_search
                )

            for output in self.execute_checks_parallel(
                checks_to_run, max_concurrent_jobs
            ):
                yield output

        self.searchbase_logger.info(
            "finalizing task run",
            extra={
                "task_status": self.task_status,
                "checks_executed": f"{len(checks_to_run)}",
                "task_id": self.task_id,
                "task_sid": self.sid,
            },
        )

        # Flush log buffers at the end
        for handler in self.logger.handlers:
            handler.flush()

    def validate_checks(self, checks):
        if self.adhoc and len(checks) != 1:
            raise SearchbaseCommandException(
                f"Adhoc needs exactly 1 search, but {len(checks)} were requested"
            )
        return checks

    def validate_args(self):
        """
        Validate whether the provided arguments are permissible
        """

        set_properties = sum(
            [
                self.jobs is not None,
                self.checksgroup is not None,
                self.adhoc is not None,
            ]
        )

        if set_properties > 1:
            raise SearchbaseCommandException(
                "jobs, checksgroup and adhoc arguments are mutually exclusive - pick one"
            )

    def load_searchbase_config(self):
        """
        Load up the searchbase.conf file contents
        """
        self.searchbase_conf = self.service.confs["searchbase"]
        self.searchbase_conf_stanzas = [entry.name for entry in self.searchbase_conf]

    def load_ssef_config(self):
        """
        Load up the ssef.conf file contents
        """

        self.ssef_conf = self.service.confs["ssef"]

    def load_settings_config(self):
        """
        Load up the ssef.conf file contents
        """

        self.settings_conf = self.service.confs["setup"]

    def get_checks_to_run(self):
        """
        Depending on the provided input arguments, identify the checks to run
        """
        if self.jobs:
            return self.get_checks_to_run_for_jobs()
        elif self.checksgroup:
            return self.get_checks_to_run_for_checkgsroup()
        elif self.adhoc:
            return self.get_checks_to_run_for_adhoc()
        else:
            return []

    def get_checks_to_run_for_jobs(self):
        """
        Given a list of jobs, identify jobs to run
        """

        return self.get_checks_to_run_from_searchbase_conf(self.jobs)

    def get_checks_to_run_for_checkgsroup(self):
        """
        Given a particular checksgroup, identify checks to run
        """
        ssef_conf_stanzas = [entry.name for entry in self.ssef_conf]

        if self.checksgroup in ssef_conf_stanzas:
            checkgroup_checks = self.ssef_conf[self.checksgroup].checks
            if not checkgroup_checks:
                return []
            try:
                checks = self.get_checks_to_run_from_searchbase_conf(
                    checkgroup_checks.split(",")
                )
                return checks
            except Exception as exc:
                self.logger.error(str(exc))
                return []

        else:
            raise SearchbaseCommandException(
                "Could not find provided checksgroup in ssef.conf"
            )

    def get_checks_to_run_for_adhoc(self):
        check = self.adhoc
        found_checks = self.get_checks_to_run_from_searchbase_conf([check])

        if len(found_checks) != 1:
            raise SearchbaseCommandException(
                "Could not find adhoc value in searchbase.conf"
            )

        return found_checks

    def get_checks_to_run_from_searchbase_conf(self, checks):
        """
        Given a list of search names, look them up in sert
        """
        checks_to_run = []
        for check in checks:
            if check in self.searchbase_conf_stanzas:
                checks_to_run.append(self.searchbase_conf[check])
            else:
                self.logger.warning("Search name %s not found. Skipping.", check)
        return checks_to_run

    def execute_checks_parallel(self, checks_to_run, max_concurrent_jobs=5):
        """
        Runs a list of checks concurrently up to a limit.
        """

        def run_check(check, is_last=False):

            check_search_name = check.content.get("search_name")
            check_category = (
                f"{check.content.get('category')}: {check.content.get('sub_category')}"
            )
            check_tags = check.content.get("tags")
            check_job_status = ""
            job_runtime = "0"
            time_range = self.determine_job_time_range(check.content)
            self.searchbase_logger.info("time_range:", time_range)

            if self.timeout:
                time.sleep(self.timeout)

            try:

                job = self.trigger_search_job(check, time_range)
                self.searchbase_logger.info(
                    "triggered search job for check",
                    extra={"check": check.name, "check_job_id": str(job.sid)},
                )

                while not job.is_done():
                    time.sleep(2)
                    check_job_status = job.state.content.get("dispatchState").lower()

                    self.searchbase_logger.info(
                        "waiting for check job to complete",
                        extra={
                            "check_job_status": check_job_status,
                            "check": check.name,
                            "task_id": self.task_id,
                            "task_sid": self.sid,
                        },
                    )

                check_job_status = job.state.content.get("dispatchState").lower()
                job_runtime = job.state.content.get("runDuration").lower()

                self.searchbase_logger.info(
                    "search job for check done, retrieving results count",
                    extra={
                        "check_job_status": check_job_status,
                        "check_job_runtime": job_runtime,
                        "check": check.name,
                        "task_id": self.task_id,
                        "task_sid": self.sid,
                    },
                )

                job_result_count = self.get_job_results_count(job)

                self.searchbase_logger.info(
                    "check complete",
                    extra={
                        "check_job_status": check_job_status,
                        "check_job_runtime": job_runtime,
                        "check_job_num_results": job_result_count,
                        "check_category": check_category,
                        "check": check.name,
                        "task_id": self.task_id,
                        "task_sid": self.sid,
                    },
                )

                if "sleep_after" in check.content:
                    time.sleep(int(check.content["sleep_after"]))

                return {
                    "_time": time.time(),
                    "job_name": check.name,
                    "job_search_name": check_search_name,
                    "job_tags": check_tags,
                    "job_app": check.access["app"],
                    "job_category": check_category,
                    "job_status": check_job_status,
                    "job_result_count": job_result_count,
                    "job_run_duration": job_runtime,
                    "job_dispatch_earliest_time": time_range.get("earliest_time", None),
                    "job_dispatch_latest_time": time_range.get("latest_time", None),
                    "job_time_from_searchbase": str(bool(self.time_from_searchbase)),
                }

            except Exception as exc:
                check_job_status = check_job_status or "failed"

                self.searchbase_logger.error(
                    "failed to process check",
                    extra={
                        "check_job_status": check_job_status,
                        "check_job_runtime": job_runtime,
                        "check_category": check_category,
                        "check_job_exception": str(exc).replace('"', "'"),
                        "check": check.name,
                        "task_id": self.task_id,
                        "task_sid": self.sid,
                    },
                )

                return {
                    "_time": time.time(),
                    "job_name": check.name,
                    "job_search_name": check_search_name,
                    "job_tags": check_tags,
                    "job_app": check.access["app"],
                    "job_category": check_category,
                    "job_status": "failed",
                    "job_result_count": 0,
                    "job_run_duration": "0",
                    "job_dispatch_earliest_time": time_range.get("earliest", None),
                    "job_dispatch_latest_time": time_range.get("latest", None),
                    "job_time_from_searchbase": str(bool(self.time_from_searchbase)),
                }

            finally:
                if is_last:
                    self.task_status = "COMPLETED"

                self.searchbase_logger.info(
                    "processed check",
                    extra={
                        "task_status": self.task_status,
                        "check_job_status": check_job_status,
                        "check_job_runtime": job_runtime,
                        "check_category": check_category,
                        "check": check.name,
                        "task_id": self.task_id,
                        "task_sid": self.sid,
                    },
                )
                self.searchbase_logger.delVar("check_job_id")
                self.searchbase_logger.delVar("check")

        # Run with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_concurrent_jobs) as executor:
            futures = {
                executor.submit(run_check, check, i == len(checks_to_run) - 1): check
                for i, check in enumerate(checks_to_run)
            }
            results = []
            for future in as_completed(futures):
                """result = future.result()
                yield result"""
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.searchbase_logger.error(
                        "Unexpected exception in future", extra={"error": str(e)}
                    )

            for result in results:
                yield result

    def execute_check_adhoc(self, check):
        """
        Runs a single check adhoc and in the foreground and waits for completion before yielding results
        """

        self.searchbase_logger.info("performing adhoc task run")

        time_range = self.determine_job_time_range(check.content)
        self.searchbase_logger.info(
            f"time_range: {time_range}",
            extra={
                "check": check.name,
                "task_status": self.task_status,
                "task_id": self.task_id,
                "task_sid": self.sid,
            },
        )
        job = self.trigger_search_job(check, time_range, {"preview": True})
        while True:
            while not job.is_ready():
                pass

            time.sleep(self.ADHOC_CHECK_INTERVAL)

            if job["isDone"] == "1":
                break

        job.refresh()
        offset = 0
        result_count = int(job["resultCount"])
        count = 10000

        seen_fields = set()
        while offset < result_count:
            for result in self.get_job_results(job, count, offset):
                if isinstance(result, splunklib_results.Message):
                    self.searchbase_logger.info(result)
                    continue
                new_fields = set(result).difference(seen_fields)
                for new_field in new_fields:
                    self.add_field(result, new_field, result[new_field])
                seen_fields = seen_fields.union(new_fields)
                yield result
            offset += count

    def get_job_results(self, job, count=0, offset=0):
        """
        Returns search results from the search job. Requires the job be finished.
        """
        job_results = job.results(output_mode="json", count=count, offset=offset)
        for result in JSONResultsReader(job_results):
            yield result

    def follow_job(job, count, items):
        offset = 0  # High-water mark
        while True:
            total = count()
            if total <= offset:
                time.sleep(1)  # Wait for something to show up
                job.refresh()
                continue
            stream = items(offset + 1)
            for event in splunklib_results.JSONResultsReader(stream):
                yield event
            offset = total

    def get_job_results_count(self, job):
        """
        Given a Splunk job, return the number of results that job returned
        """
        job_results = job.results(output_mode="json")
        job_results_count = sum(
            1 for _ in JSONResultsReader(job_results) if isinstance(_, dict)
        )

        return job_results_count

    def trigger_search_job(self, check, time_range, settings=None):
        """
        Create a search job for the given searchbase stanza
        """

        if not settings:
            settings = {}
        if (
            check
            and check.content
            and isinstance(check.content, dict)
            and "search" in check.content
        ):
            search = check.content["search"]

            if "severity_rule" in check.content :
                search = search + check.content.severity_rule

            if self.historical == "true" and "`ssef_summarize_data" not in search:
                search = search + f" | `ssef_summarize_data_normal({check.name})`"

            search_spaced = search.split(" ")

            if search[0] != "|" and search_spaced[0] != "search":
                search = f"search {search}"

            search_job_args = {
                "exec_mode": "normal",
                "output_mode": "json",
                **time_range,
                **settings,
            }

            # honor the dispatch context app if needed
            
            dispatch_context = (
                check.content["dispatch_context"]
                if check.content["dispatch_context_force"] == "1"
                else self.service.namespace["app"]
            )
            return self.service.jobs.create(search, app=dispatch_context, **search_job_args)
        else:
            raise ValueError(
                f"Invalid check {check.name}: 'search' key missing in check.content"
            )

    def is_all_time(self):
        """
        Whether or not the command is executed across all-time
        """
        return (
            self.metadata.searchinfo.earliest_time == 0
            and self.metadata.searchinfo.latest_time == 0
        )

    def determine_job_time_range(self, searchbase_stanza_content):
        """
        Determine the time range for a job.
        """
        time_range = self.DEFAULT_TIME_RANGE

        if self.time_from_searchbase:
            self.searchbase_logger.debug("time_from_searchbase override passed")

        if self.is_all_time() or self.time_from_searchbase:
            dispatch_earliest_time = searchbase_stanza_content.get(
                "dispatch_earliest_time"
            )
            dispatch_latest_time = searchbase_stanza_content.get("dispatch_latest_time")

            if dispatch_latest_time is not None and dispatch_earliest_time is not None:

                time_range["earliest_time"] = dispatch_earliest_time
                time_range["latest_time"] = dispatch_latest_time

            elif dispatch_latest_time is not None and dispatch_earliest_time is None:
                time_range["latest_time"] = dispatch_latest_time

            elif dispatch_latest_time is None and dispatch_earliest_time is not None:
                time_range["earliest_time"] = dispatch_earliest_time
        else:
            time_range["earliest_time"] = int(self.metadata.searchinfo.earliest_time)
            time_range["latest_time"] = int(self.metadata.searchinfo.latest_time)

        self.searchbase_logger.debug(
            "determined effective time_range", extra=time_range
        )
        return time_range


dispatch(SearchbaseV2Command, sys.argv, sys.stdin, sys.stdout, __name__)
