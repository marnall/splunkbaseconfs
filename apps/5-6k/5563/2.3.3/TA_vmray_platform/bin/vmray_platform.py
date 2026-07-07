import calendar
import itertools
import json
import logging
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple
from http.client import HTTPConnection

# pylint: disable=wrong-import-order,wrong-import-position
from requests import ConnectionError  # pylint: disable=redefined-builtin
from requests.exceptions import ReadTimeout
# it's ugly but this is how splunk wants it...

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as sc  # pylint: disable=no-name-in-module
import splunklib.modularinput as smi
from splunklib import six

from vmraylib.rest_cmds import VMRay

import aggregator_functions
import writeback_generic

from writeback_v2 import SummaryV2EventWriter

if TYPE_CHECKING:
    from splunklib.modularinput.event_writer import EventWriter

DEFAULT_LOG_LEVEL = logging.WARNING

# this will be shown in the source and is the name of our modinput
MODIN_NAME = "vmray_platform"
APP_FOLDER = "TA_vmray_platform"
DEF_MAX_ITEMS = 100
DEF_SUBMISSION_MAX_TIMEOUT = 4.0
DEF_FILE_INTEL_EXPORT_THRESHOLD = 75
DEBUG_TIMING = True
DEF_MAX_WORKER_THREADS = 8
# How many times we try an import task before we give up on it.
MAX_TRIES = 10
MUTEX = threading.Lock()


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


# from https://docs.python.org/2/library/itertools.html#recipes
def roundrobin(*iterables):
    """roundrobin('ABC', 'D', 'EF') --> A D E B F C"""
    # Recipe credited to George Sakkis
    pending = len(iterables)
    if six.PY2:
        nexts = itertools.cycle(iter(it).next for it in iterables)
    else:
        # py3
        nexts = itertools.cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for _next in nexts:
                yield _next()
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))


class VMRayModularInput(smi.Script):

    MASK = "**********"

    def __init__(self):
        super().__init__()
        self.event_type = None

        self.import_analysis = False
        self.import_vti_match = False
        self.import_yara_match = False
        self.import_av_match = False
        self.import_reputation_lookup = False
        self.import_artifacts = False
        self.import_iocs_only = False
        self.import_extracted_strings = False
        self.import_network = False
        self.import_malware_config = False
        self.import_analysis_details = False
        self.import_remark = False
        self.import_static_data = False
        self.import_submission = False
        self.import_sample = False
        self.import_timing = False
        self.import_size = False

        self.restricted_mode = False

        self.should_import_summary = False

        # not implemented yet
        self.import_debug_notfications = False
        self.import_job_cfg = False
        self.import_job_desc = False

        self.server_uri: Optional[str] = None
        self.session_key: Optional[str] = None
        self.input_name: Optional[str] = None
        self.max_worker_threads = DEF_MAX_WORKER_THREADS

        self.failed_tasks: List[Dict[str, Any]] = []
        self.setup_logging()

    @staticmethod
    def setup_logging():
        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_handler.setFormatter(logging.Formatter("%(levelname)s VMRAY %(message)s"))

        requests_logger = logging.getLogger("requests")
        requests_logger.setLevel(DEFAULT_LOG_LEVEL)
        requests_logger.propagate = True

        urllib_logger = logging.getLogger("requests.packages.urllib3")
        urllib_logger.setLevel(DEFAULT_LOG_LEVEL)

        HTTPConnection.debuglevel = 1

        logging.root.setLevel(DEFAULT_LOG_LEVEL)
        logging.root.addHandler(stderr_handler)

        log_path = Path("/opt/splunk/var/log")

        try:
            exists = log_path.exists()
        except PermissionError:
            return

        if exists:
            file_handler = RotatingFileHandler(
                log_path / "vmray_platform.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=7,
            )
            file_formatter = UTCFormatter(
                "%(asctime)s - %(name)s [%(levelname)s] - %(pathname)s [line: %(lineno)s]: - %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
            file_handler.setFormatter(file_formatter)
            logging.root.addHandler(file_handler)
            requests_logger.addHandler(file_handler)
            urllib_logger.addHandler(file_handler)

    ############################################################################
    # Setup and validation functions
    ############################################################################

    def get_scheme(self):
        """specifies the setup dialog and required config values"""
        scheme = smi.Scheme(MODIN_NAME)
        scheme.title = "VMRay Platform"
        scheme.description = "Streams VMRay Platform analyses."
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        server_ip_argument = smi.Argument("server_ip")
        server_ip_argument.title = "Server IP Address"
        server_ip_argument.data_type = smi.Argument.data_type_string
        server_ip_argument.description = (
            "The IP address of the VMRay Platform Server.")
        server_ip_argument.required_on_create = True
        server_ip_argument.required_on_edit = True
        scheme.add_argument(server_ip_argument)

        api_key_argument = smi.Argument("api_key")
        api_key_argument.title = "API Key"
        api_key_argument.data_type = smi.Argument.data_type_string
        api_key_argument.description = "The REST API Key for the Server."
        api_key_argument.required_on_create = True
        api_key_argument.required_on_edit = True
        scheme.add_argument(api_key_argument)

        http_proxy_argument = smi.Argument("http_proxy")
        http_proxy_argument.title = "HTTP Proxy"
        http_proxy_argument.data_type = smi.Argument.data_type_string
        http_proxy_argument.description = (
            "Full URL schema of the HTTP Proxy (e.g. http://10.10.1.10:8888).")
        http_proxy_argument.required_on_create = False
        http_proxy_argument.required_on_edit = False
        scheme.add_argument(http_proxy_argument)

        disable_verify_argument = smi.Argument("disable_verify")
        disable_verify_argument.title = "Disable Certificate Verification"
        disable_verify_argument.data_type = smi.Argument.data_type_boolean
        disable_verify_argument.description = (
            "Disables the HTTPS certificate verification of the VMRay server.")
        scheme.add_argument(disable_verify_argument)

        start_submission_id_argument = smi.Argument("start_submission_id")
        start_submission_id_argument.title = "Start Submission ID"
        start_submission_id_argument.data_type = smi.Argument.data_type_number
        start_submission_id_argument.description = (
            "The starting submission_id. Only submissions which finished later"
            " will be imported into Splunk. . If not specified all submissions are "
            "imported.")
        start_submission_id_argument.required_on_create = False
        start_submission_id_argument.required_on_edit = False
        scheme.add_argument(start_submission_id_argument)

        max_items_argument = smi.Argument("max_items")
        max_items_argument.title = "Maximum Number of Items Requested"
        max_items_argument.data_type = smi.Argument.data_type_number
        max_items_argument.description = (
            ("The maximum number of itemes requested from the VMRay REST API"
             f" per interval (default = {DEF_MAX_ITEMS}). Zero defaults to the previously"
             " mentioned value."))
        max_items_argument.required_on_create = False
        max_items_argument.required_on_edit = False
        scheme.add_argument(max_items_argument)

        import_analysis_argument = smi.Argument("import_analysis")
        import_analysis_argument.title = "Enable Analysis import"
        import_analysis_argument.data_type = smi.Argument.data_type_boolean
        import_analysis_argument.description = "Enables the analysis import."
        scheme.add_argument(import_analysis_argument)

        import_submission_argument = smi.Argument("import_submission")
        import_submission_argument.title = "Enable Submission import"
        import_submission_argument.data_type = smi.Argument.data_type_boolean
        import_submission_argument.description = "Enables the submission import."
        scheme.add_argument(import_submission_argument)

        submission_max_timeout_argument = smi.Argument("submission_max_timeout")
        submission_max_timeout_argument.title = "Max time to wait for a submission to finish."
        submission_max_timeout_argument.data_type = smi.Argument.data_type_number
        submission_max_timeout_argument.description = (
            "Hours to wait before an unfinished submission is imported to Splunk"
            f" (default = {DEF_SUBMISSION_MAX_TIMEOUT}")
        submission_max_timeout_argument.required_on_create = False
        submission_max_timeout_argument.required_on_edit = False
        scheme.add_argument(submission_max_timeout_argument)

        import_sample_argument = smi.Argument("import_sample")
        import_sample_argument.title = "Enable Sample import"
        import_sample_argument.data_type = smi.Argument.data_type_boolean
        import_sample_argument.description = "Enables the sample import."
        scheme.add_argument(import_sample_argument)

        import_timing_argument = smi.Argument("import_timing")
        import_timing_argument.title = "Enable timing import"
        import_timing_argument.data_type = smi.Argument.data_type_boolean
        import_timing_argument.description = "Enables the timing json import."
        scheme.add_argument(import_timing_argument)

        import_size_argument = smi.Argument("import_size")
        import_size_argument.title = "Enable size import"
        import_size_argument.data_type = smi.Argument.data_type_boolean
        import_size_argument.description = "Enables the size json import."
        scheme.add_argument(import_size_argument)

        import_vti_match_argument = smi.Argument("import_vti_match")
        import_vti_match_argument.title = "Enable VTI match import"
        import_vti_match_argument.data_type = smi.Argument.data_type_boolean
        import_vti_match_argument.description = (
            "Enables the VTI match import.")
        scheme.add_argument(import_vti_match_argument)

        import_yara_match_argument = smi.Argument("import_yara_match")
        import_yara_match_argument.title = "Enable YARA import"
        import_yara_match_argument.data_type = smi.Argument.data_type_boolean
        import_yara_match_argument.description = (
            "Enables the YARA match import.")
        scheme.add_argument(import_yara_match_argument)

        restricted_mode_argument = smi.Argument("restricted_mode")
        restricted_mode_argument.title = "Internal Restricted Import Mode"
        restricted_mode_argument.data_type = smi.Argument.data_type_boolean
        restricted_mode_argument.description = (
            "Removes imported data for internal compliance.")
        scheme.add_argument(restricted_mode_argument)

        import_av_match_argument = smi.Argument("import_av_match")
        import_av_match_argument.title = "Enable AV match import"
        import_av_match_argument.data_type = smi.Argument.data_type_boolean
        import_av_match_argument.description = "Enables the AV match import"
        scheme.add_argument(import_av_match_argument)

        import_reputation_lookup_argument = smi.Argument("import_reputation_lookup")
        import_reputation_lookup_argument.title = "Enable reputation lookup import"
        import_reputation_lookup_argument.data_type = smi.Argument.data_type_boolean
        import_reputation_lookup_argument.description = "Enables the reputation lookup import"
        scheme.add_argument(import_reputation_lookup_argument)

        import_artifacts_argument = smi.Argument("import_artifacts")
        import_artifacts_argument.title = "Enable artifacts import"
        import_artifacts_argument.data_type = smi.Argument.data_type_boolean
        import_artifacts_argument.description = "Enables the artifacts import"
        scheme.add_argument(import_artifacts_argument)

        import_iocs_only_argument = smi.Argument("import_iocs_only")
        import_iocs_only_argument.title = "Only import artifacts that are IOCs"
        import_iocs_only_argument.data_type = smi.Argument.data_type_boolean
        import_iocs_only_argument.description = "Limit import to IOCs"
        scheme.add_argument(import_iocs_only_argument)

        import_extracted_strings_argument = smi.Argument("import_extracted_strings")
        import_extracted_strings_argument.title = "Extracted Strings"
        import_extracted_strings_argument.data_type = smi.Argument.data_type_boolean
        import_extracted_strings_argument.description = \
            "Information about the strings extracted from the dynamic behavior of the processes"
        scheme.add_argument(import_extracted_strings_argument)

        import_network_argument = smi.Argument("import_network")
        import_network_argument.title = "Enable network import"
        import_network_argument.data_type = smi.Argument.data_type_boolean
        import_network_argument.description = "Enables the network data import"
        scheme.add_argument(import_network_argument)

        import_malware_config_argument = smi.Argument("import_malware_config")
        import_malware_config_argument.title = "Enable malware configuration import"
        import_malware_config_argument.data_type = smi.Argument.data_type_boolean
        import_malware_config_argument.description = "Enables the malware configuration import"
        scheme.add_argument(import_malware_config_argument)

        import_analysis_details_argument = smi.Argument("import_analysis_details")
        import_analysis_details_argument.title = "Enable vm_and_analyzer import"
        import_analysis_details_argument.data_type = smi.Argument.data_type_boolean
        import_analysis_details_argument.description = "Enables the vm and analyzer import"
        scheme.add_argument(import_analysis_details_argument)

        import_remark_argument = smi.Argument("import_remark")
        import_remark_argument.title = "Enable remark import"
        import_remark_argument.data_type = smi.Argument.data_type_boolean
        import_remark_argument.description = "Enables the remark import"
        scheme.add_argument(import_remark_argument)

        import_static_data_argument = smi.Argument("import_static_data")
        import_static_data_argument.title = "Static Analysis Data"
        import_static_data_argument.data_type = smi.Argument.data_type_boolean
        import_static_data_argument.description = "The static data for file artifacts from the static engine"
        scheme.add_argument(import_static_data_argument)

        log_level_argument = smi.Argument("log_level")
        log_level_argument.title = "Log level"
        log_level_argument.data_type = smi.Argument.data_type_string
        log_level_argument.description = (
            "Sets the logging level of this input.")
        log_level_argument.required_on_create = False
        log_level_argument.required_on_edit = False
        scheme.add_argument(log_level_argument)

        return scheme

    def validate_input(self, definition):
        """Validates the input given to the input creation dialog"""
        try:
            self.server_uri = definition.metadata["server_uri"]
            self.session_key = definition.metadata["session_key"]
            VMRayModularInput._get_splunk_service(self.server_uri, self.session_key)
        except Exception as exc:
            raise ValueError("Could not establish connection with Splunk API") from exc

        try:
            server_ip = definition.parameters["server_ip"].lower()
        except KeyError:
            msg = "Could not read server IP "
            logging.exception(msg)
            raise ValueError(msg)  # pylint: disable=raise-missing-from

        if server_ip.startswith("http:"):
            msg = "VMRay Server IP Address must use HTTPS"
            logging.exception(msg)
            raise ValueError(msg)

        api_key = definition.parameters["api_key"]
        if api_key == self.MASK:
            name = definition.metadata["name"]
            api_key = self._load_api_key(name)

        if api_key in (self.MASK, None):
            msg = "Failed to load API key"
            logging.exception(msg)
            raise ValueError(msg)

        try:
            # check if we can reach the server and are able to make queries
            VMRay(server_ip,
                  api_key,
                  definition.parameters["disable_verify"] == "0",
                  definition.parameters.get("http_proxy", ""),
                  definition.parameters.get("restricted_mode", False))
        except ConnectionError:
            logging.exception("Could not connect to the VMRay server ")
            raise ValueError(  # pylint: disable=raise-missing-from
                "Could not connect to the VMRay server. Make sure the host is"
                " reachable and your proxy, if specified, is correct.")
        except Exception:
            logging.exception("Could not query the VMRay REST API ")
            raise ValueError(  # pylint: disable=raise-missing-from
                "Could not query the VMRay REST API make sure the API Key is"
                " valid and the corresponding user is enabled. Disable "
                "certificate verification if necessary.")

        if definition.parameters.get("start_submission_id", None) is not None:
            try:
                # the start anlysis must be larger than 0
                start_submission_id = int(definition.parameters["start_submission_id"])
                if start_submission_id <= 0:
                    raise ValueError("Start submission id is <= 0")
            except Exception:
                raise ValueError(  # pylint: disable=raise-missing-from
                    "Start Submission ID is not valid. The ID must be an "
                    "integer greater than 0.")

        if definition.parameters["max_items"] is not None:
            try:
                # must be positive int
                if int(definition.parameters["max_items"]) < 0:
                    raise ValueError("'max_items' is <= 0")
            except Exception:
                raise ValueError("Number of Requests is not an integer")  # pylint: disable=raise-missing-from

        if definition.parameters["submission_max_timeout"] is not None:
            try:
                # must be positive
                if float(definition.parameters["submission_max_timeout"]) < 0:
                    raise ValueError()
            except Exception:
                raise ValueError("Max timeout must be a float number")  # pylint: disable=raise-missing-from

        if definition.parameters.get("log_level", None) is not None:
            if (definition.parameters["log_level"] not in
                    ["Default", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]):
                raise ValueError(
                    "Log level is not valid. Level must be "
                    "\"DEBUG\", \"INFO\", \"WARNING\", \"ERROR\", "
                    "\"CRITICAL\", or \"Default\".")

    ############################################################################
    # Initialisation and housekeeping functions
    ###########################################################################
    @staticmethod
    def _get_splunk_service(server_uri, session_key):
        match = re.match(r"https?://(.*?):(\d*)", server_uri)
        host = match.group(1)
        port = int(match.group(2))
        return sc.connect(host=host, port=port, app=APP_FOLDER, sharing="app", token=session_key)

    def _get_input_stanza(self) -> "sc.Stanza":
        """Loads the stanza for the current modular input. Will be created if it does not exist.

        We create a config in $SPLUNK_HOME/etc/apps/TA_vmray_platform/local/MODIN_NAME and every
        input has its own stanza where we store the values."""
        service = self._get_splunk_service(self.server_uri, self.session_key)
        if MODIN_NAME not in service.confs:
            conf = service.confs.create(MODIN_NAME)
        else:
            conf = service.confs[MODIN_NAME]

        if self.input_name not in conf:
            stanza = conf.create(self.input_name)
        else:
            stanza = conf[self.input_name]

        return stanza

    def _encrypt_api_key(self, api_key, name):
        service = self._get_splunk_service(self.server_uri, self.session_key)

        try:
            # delete existing API key
            for secret in service.storage_passwords:
                if secret.username == "vmray" and secret.realm == name:
                    service.storage_passwords.delete(username="vmray", realm=name)

            # create new credential
            service.storage_passwords.create(api_key, username="vmray", realm=name)
        except Exception as err:
            raise ValueError(
                "An error occurred updating credentials. "
                "Please ensure your user account has admin_all_object and/or "
                f"list_storage_passwords capabilities. Details: {str(err)}"
            ) from err

    def _load_api_key(self, name):
        service = self._get_splunk_service(self.server_uri, self.session_key)
        for secret in service.storage_passwords:
            if secret.username == "vmray" and secret.realm == name:
                return secret.clear_password

        return None

    def _mask_config_api_key(self):
        service = self._get_splunk_service(self.server_uri, self.session_key)
        kind, input_name = self.input_name.split("://")
        input_conf = service.inputs.__getitem__((input_name, kind))
        content = input_conf.content

        # delete unwanted items
        del content["disabled"]
        del content["host"]
        del content["host_resolved"]
        del content["python.version"]
        del content["sourcetype"]
        del content["start_by_shell"]

        # overwrite API key and update input
        content["api_key"] = self.MASK

        try:
            new = input_conf.update(**content)
            new.refresh()
        except Exception as err:
            logging.exception("Error while updating inputs.")
            raise Exception(f"Error updating inputs.conf: {str(err)}") from err

    def _load_last_submission_id(self):
        """loads the last_submission_id from a config using the splunk rest api."""
        stanza = self._get_input_stanza()

        if "last_submission_id" in stanza.content:
            logging.debug("Stanza %s in %s last_submission_id %d",
                          self.input_name, MODIN_NAME,
                          int(stanza.content["last_submission_id"]))
            return int(stanza.content["last_submission_id"])
        return -1

    def _get_last_submission_id(self, start_submission_id: int) -> int:
        try:
            last_submission_id = self._load_last_submission_id()
        except Exception:  # pylint: disable=broad-except
            logging.critical("Could not load last_submission_id.", exc_info=True)
            sys.exit(1)
        logging.info("Loaded last_submission_id %d", last_submission_id)

        if start_submission_id in (-1, 0):
            # no start submission id was given
            last_submission_id = max(last_submission_id, 0)
        else:
            if last_submission_id <= 0:
                last_submission_id = start_submission_id - 1
            elif last_submission_id < start_submission_id:
                # we probably updated the start_submission_id field
                last_submission_id = start_submission_id - 1
        return last_submission_id

    def _save_last_submission_id(self, last_submission_id):
        """Saves the last_submission_id in a config file using the splunk rest API."""
        stanza = self._get_input_stanza()
        stanza.submit({"last_submission_id": last_submission_id})

    def _load_failed_tasks(self) -> List[Dict[str, Any]]:
        """Load previously failed tasks due network timeout from the input stanza."""
        stanza = self._get_input_stanza()
        failed_tasks = json.loads(stanza.content.get("failed_tasks", "[]"))
        logging.info("Loaded %d previously failed tasks", len(failed_tasks))
        return failed_tasks

    def _save_failed_tasks(self):
        """Saves failed task to input stanza. So we can try to execute them later again."""
        stanza = self._get_input_stanza()
        logging.info("Save %d failed tasks", len(self.failed_tasks))
        stanza.submit({"failed_tasks": json.dumps(self.failed_tasks)})

    def _add_failed_task(self, task):
        """Add failed task safely to self.failed_task list."""
        logging.info("Add task %d to failed tasks.", task["task_id"])
        existing_task = False

        for failed_task in self.failed_tasks:
            if failed_task["task_id"] == task["task_id"]:
                existing_task = True
                break
        if not existing_task:
            self.failed_tasks.append(task)

    def _remove_failed_task(self, task):
        """Remove failed task safely from self.failed_task list"""
        logging.info("Remove task %d from failed tasks.", task["task_id"])
        if task in self.failed_tasks:
            self.failed_tasks.remove(task)

    @staticmethod
    def get_analysis_tasks(vmray_api: VMRay, cur_submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Query the Analyzer to receive a list of X analyses from all submissions.
        X depends on the query limits. Returns empty list on error.
        """

        cur_analyses: List[Dict[str, Any]] = []

        try:
            for submission in cur_submissions:
                submission_id = submission["submission_id"]
                analyses = vmray_api.get_analyses_from_submission(submission_id)
                cur_analyses.extend(analyses)
        except Exception:  # pylint: disable=broad-except
            logging.exception("An exception occurred while retrieving "
                              "analyses. trying to continue anyway...")

        return cur_analyses

    @staticmethod
    def get_submission_tasks(vmray_api: VMRay, last_submission_id: int, max_timeout: float):
        """Like get_analysis_tasks but with submissions"""
        try:
            cur_submissions = vmray_api.get_submissions(last_submission_id=last_submission_id)
        except Exception:  # pylint: disable=broad-except
            logging.exception("An exception occurred while retrieving "
                              "submissions. trying to continue anyway...")
            cur_submissions = []

        # in contrast to analyses, an arbitrary number of consecutively numbered
        # submissions can include submissions that are not finished yet. Hence,
        # if we want to ingest them we have to wait until they are finished.
        # If the submission is younger than max_timeout we will try to continue
        # with already finished submissions and will retry to collect the submission
        # to a later point in time. If we are still not able to collect the
        # submission we will skip it.
        # this handling applies only to analyzer < 4.0.0. starting with that version
        # the _last_id mechanism was introduced which only returns finished submissions.
        cut_off = None
        for sub_idx, sub in enumerate(cur_submissions):
            if not sub["submission_finished"]:
                # check if the submission is too old
                submission_created = datetime.strptime(sub["submission_created"], "%Y-%m-%dT%H:%M:%S")
                if (
                    max_timeout >= 0
                    and submission_created < datetime.now() - timedelta(hours=max_timeout)
                ):
                    # the submission is older than our threshold
                    continue
                cut_off = sub_idx
                break
        if cut_off is not None:
            cur_submissions = cur_submissions[:cut_off]

        return cur_submissions

    ############################################################################
    # Main worker routine. Collects the required info for each task
    ############################################################################

    def worker_process_tasks(self, tasks_queue, processed_tasks_queue, vmray_api):
        """worker thread implementation. Processes tasks by collecting the info
        required by the resulting event using the aggregator functions. uses the
        queues (i.e. task_done) to signal that the jobs are processed."""
        logging.info("WORKER started")

        while True:
            try:
                my_task = tasks_queue.get_nowait()
            except queue.Empty:
                # all done. terminate the thread
                break

            task_type = None
            task_id = None
            if not my_task.get("failed_tries"):
                analysis_id = my_task.get("analysis_id")
                submission_id = my_task.get("submission_id")

                if analysis_id is not None:
                    task_type = "analysis"
                    task_id = analysis_id
                if submission_id is not None:
                    task_type = "submission"
                    task_id = submission_id
                assert sum((x is not None for x in [analysis_id, submission_id])) == 1
            else:
                task_type = my_task.get("task_type")
                analysis_id = my_task[task_type].get("analysis_id")
                submission_id = my_task[task_type].get("submission_id")
                task_id = my_task.get("task_id")

            my_results: Dict[str, Any] = {}
            try:
                my_results = self._worker_process_task(my_task, vmray_api, analysis_id, task_id, task_type)
            except Exception as exc:
                logging.exception("WORKER id=%d type=%s Exception in worker", task_id, task_type)
                raise exc
            finally:
                # write back to the result queue
                processed_tasks_queue.put(my_results)
                logging.debug("WORKER id=%d type=%s Worker task_done", task_id, task_type)
                # we mark the task so we do not end up in an infinte loop
                tasks_queue.task_done()
        logging.info("WORKER terminating")

    def _worker_process_task(self, my_task, vmray_api, analysis_id, task_id, task_type) -> Dict[str, Any]:
        # get the task info of the currently processed task

        logging.debug("WORKER id=%d type=%s Start processing", task_id, task_type)

        results: Dict[str, Any] = {"task_type": task_type, "task_id": task_id}
        imports: List[Tuple[List[str], bool, Callable[..., Dict[str, Any]], Dict[str, Any]]] = []
        # imports to fetch
        # is the current task created by a new analysis?
        if task_type == "analysis":

            # handler table for the different imports.
            # structure:
            # ([list of events provided by the entry],
            #  bool specifying whether or not the information should be gathered,
            #  function to be called to gather the information,
            #  {dict of arguments to function must have vmray_api and analysis_id})
            if not my_task.get("failed_tries"):
                analysis_task = my_task
            else:
                analysis_task = my_task["analysis"]

            # Get 'summary_v2' early in order to
            # reuse in other methods.
            # This reduces the number of 'summary_v2' downloads
            # to 1 instead of 4.
            logging.debug("WORKER id=%d type=%s fetching %s", task_id, task_type, repr(["summary_v2"]))
            # Call function using 'call_api_func()'
            # because of error handling.
            summary_v2 = self.call_api_func(
                api_func=aggregator_functions.download_summary_v2,
                api_func_args={
                    "vmray_api": vmray_api,
                    "analysis_id": analysis_id,
                },
                provides=["summary_v2"],
                task=my_task,
            )

            if summary_v2.get("summary_v2", {}) is None:
                logging.debug("No summary_v2 for analysis_id=%s (task_id=%d type=%s)", analysis_id, task_id, task_type)
                analysis_type = None
            else:
                score_type = summary_v2.get("summary_v2", {}).get("vti", {}).get("score_type", "")
                analysis_type = aggregator_functions.get_analysis_engine_type(score_type, analysis_id)

            imports.extend([
                (
                    ["analysis"],
                    True,
                    aggregator_functions.get_analysis,
                    {"vmray_api": vmray_api, "analysis": analysis_task}
                ),
                (
                    ["extended_analysis_info"],
                    True,
                    aggregator_functions.get_extended_analysis_info,
                    {"vmray_api": vmray_api, "analysis": analysis_task, "analysis_type": analysis_type}
                ),
                (
                    ["malware_configurations"],
                    self.import_malware_config,
                    aggregator_functions.get_malware_configuration,
                    {"vmray_api": vmray_api, "analysis_id": analysis_id, "summary_v2": summary_v2.get("summary_v2", {})}
                ),
                (
                    ["timing"],
                    self.import_timing,
                    aggregator_functions.get_timing,
                    {"vmray_api": vmray_api, "analysis_id": analysis_id}
                ),
                (
                    ["size"],
                    self.import_size,
                    aggregator_functions.get_size,
                    {"vmray_api": vmray_api, "analysis_id": analysis_id}
                ),
                (
                    ["extracted_strings"],
                    self.import_extracted_strings,
                    aggregator_functions.get_extracted_strings,
                    {"vmray_api": vmray_api, "analysis_id": analysis_id, "summary_v2": summary_v2.get("summary_v2", {})}
                ),
                (
                    ["summary_v2"],
                    self.should_import_summary,
                    aggregator_functions.get_summary_v2,
                    {
                        "summary_v2": summary_v2,
                    }
                ),
            ])
        elif task_type == "submission":
            # same as above but for tasks of type submission
            if not my_task.get("failed_tries"):
                submission_task = my_task
            else:
                submission_task = my_task["submission"]

            # Get 'sample' early in order to
            # reuse in other methods.
            # This reduces the number of 'sample' downloads
            # to 1 instead of 2.

            sample_id = submission_task.get("submission_sample_id", -1)

            logging.debug("WORKER id=%d type=%s fetching %s", task_id, task_type, repr(["sample"]))
            # Call function using 'call_api_func()'
            # because of error handling.
            sample = self.call_api_func(
                api_func=aggregator_functions.download_sample_info,
                api_func_args={
                    "vmray_api": vmray_api,
                    "sample_id": sample_id,
                },
                provides=["sample"],
                task=my_task,
            )

            sample_info = sample.get("sample", {})

            imports.extend([
                (
                    ["submission"],
                    True,
                    aggregator_functions.get_submission,
                    {
                        "submission": submission_task,
                        "sample_info": sample_info,
                    },
                ),
                (
                    ["sample"],
                    self.import_sample,
                    aggregator_functions.get_sample_info,
                    {
                        "sample": sample,
                    },
                ),
            ])

        # Iterate through the handler table, see if the according handler must be called to
        # gather information. If so call the handler function and give the args dict as
        # arguments.
        for imp_provides, do_imp, imp_func, imp_func_args in imports:
            if not do_imp:
                continue
            logging.debug("WORKER id=%d type=%s fetching %s", task_id, task_type, repr(imp_provides))

            imp_result = self.call_api_func(
                api_func=imp_func,
                api_func_args=imp_func_args,
                provides=imp_provides,
                task=my_task,
            )

            # Put the results in the results dict. This will be put in the output queue.
            for given_imp_name, given_imp_result in imp_result.items():
                results[given_imp_name] = given_imp_result

        return results

    def call_api_func(
        self,
        api_func: Callable[..., Dict[str, Any]],
        api_func_args: Dict[str, Any],
        provides: List[str],
        task: Dict[str, Any],
    ):
        """Call the VMRay API and import data, handle possible occuring errors. If network timeouts
        occur we will retry the data import for those analysis again next time the data import runs.
        If any other errors occur (json parsing errors for example) then we skip these analysis.
        """
        result: Dict[str, Any] = {p: None for p in provides}

        try:
            result = api_func(**api_func_args)

            # Check if this was a previously failed task which is now successful. Mark it so we
            # can later remove it from the failed task list.
            if task.get("failed_tries"):
                result["succeeded_previously_failed_task"] = True
        except (ReadTimeout, ValueError) as exc:
            err_type = "Error"
            if isinstance(exc, ReadTimeout):
                err_type = "Timeout"
            logging.warning(
                "WORKER %s occured while calling API '%s' (%s)",
                err_type,
                api_func.__name__,
                api_func_args,
                exc_info=False,
            )

            if task.get("failed_tries"):
                result = task
            else:
                result = {p: task for p in provides}
            result["failed_tries"] = task.get("failed_tries", 0) + 1
        except Exception:  # pylint: disable=broad-except
            # all errors occuring which are not network timeout errors get skipped
            logging.exception(
                "WORKER exception while calling '%s' (%s)", api_func.__name__, api_func_args,
            )
            # If a task which failed previously because of network problems, now fails for other
            # reasons like data retention, json parsing errors etc. Then we need to get it out of
            # the failed tasks list.
            if task.get("failed_tries"):
                with MUTEX:
                    self._remove_failed_task(task)

        return result

    ############################################################################
    # Main function. Called whenever new inputs should be gathered.
    ############################################################################

    def stream_events(self, inputs, event_writer: "EventWriter"):  # pylint: disable=arguments-renamed
        """The main processing function"""

        # get the config stanza. Remember: we are working in multi instance mode
        self.input_name, config = next(iter(inputs.inputs.items()))
        assert self.input_name is not None
        self.server_uri = inputs.metadata["server_uri"]
        self.session_key = inputs.metadata["session_key"]
        # setup logging
        log_level = config.get("log_level", DEFAULT_LOG_LEVEL)
        if log_level == "Default":
            log_level = DEFAULT_LOG_LEVEL

        logging.root.setLevel(log_level)
        for handler in logging.root.handlers:
            formatter = UTCFormatter(
                f"%(asctime)s - %(levelname)s VMRAY source=\"{self.input_name}\" %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
            handler.setFormatter(formatter)

        logging.debug("Fetching new analyses with options:")
        logging.debug("inputs %s", inputs.inputs)
        logging.debug("metadata %s", inputs.metadata)

        logging.debug("Getting new analyses from '%s'", self.input_name)

        if "server_ip" not in config:
            logging.critical("Server IP missing. Aborting...")
            sys.exit(1)
        server_ip = config["server_ip"]

        try:
            name = self.input_name.split("://", 1)[1]
            api_key = config["api_key"]
            if api_key != self.MASK:
                self._encrypt_api_key(api_key, name)
                self._mask_config_api_key()

            api_key = self._load_api_key(name)
        except Exception as err:  # pylint: disable=broad-except
            logging.critical("Error: %s", str(err))
            sys.exit(1)

        if api_key is None:
            logging.critical("API key not specified. Aborting")
            sys.exit(1)

        http_proxy = config.get("http_proxy", "")

        if config.get("max_items", None) is not None and int(config.get("max_items", None)) > 0:
            max_items = int(config["max_items"])
        else:
            max_items = DEF_MAX_ITEMS

        if config.get("submission_max_timeout", None) is not None:
            submission_max_timeout = float(config["submission_max_timeout"])
        else:
            submission_max_timeout = DEF_SUBMISSION_MAX_TIMEOUT

        if config.get("start_submission_id", None) is not None and int(config.get("start_submission_id")) > 0:
            start_submission_id = int(config["start_submission_id"])
        else:
            start_submission_id = -1

        if config.get("disable_verify", None) is None:
            disable_verify = False
        else:
            disable_verify = int(config["disable_verify"]) == 1

        self._load_settings(config)

        # check if we should get new analyses.
        need_analyses = any([
            self.import_analysis,
            self.import_yara_match,
            self.import_vti_match,
            self.import_artifacts,
            self.import_av_match,
            self.import_network,
            self.import_malware_config,
            self.import_reputation_lookup,
            self.import_extracted_strings,
            self.import_analysis_details,
            self.import_remark,
            self.import_static_data,
            self.import_submission,
            self.import_sample,
            self.import_timing,
            self.import_size,
            self.import_debug_notfications,
        ])
        # check if we should get new submissions.
        need_submissions = any([self.import_sample, self.import_submission])

        if not any([need_analyses, need_submissions]):
            logging.info("Nothing to import (no import enabled). Terminating...")
            return

        try:
            logging.debug("Creating connection to REST API %s", server_ip)
            vmray_api = VMRay(server_ip, api_key, not disable_verify,
                              http_proxy, self.restricted_mode)
        except ConnectionError:
            logging.critical("Could not connect to the VMRay server. Make "
                             "sure the host is reachable", exc_info=True)

            sys.exit(1)
        except Exception:  # pylint: disable=broad-except
            logging.critical(
                "Could not instantiate VMRay API. Make sure the server is "
                "running, the API key is correct, and disable the certificate "
                "verification if necessary. Aborting...", exc_info=True)
            sys.exit(1)

        # setup our input queues which will feed the workers
        tasks_queue: queue.Queue = queue.Queue(maxsize=max_items)
        # setup our output queue which will be filled by the workers
        processed_tasks_queue: queue.Queue = queue.Queue(maxsize=max_items)

        # get the last_submission_id we saved in an earlier iteration of this
        # script
        last_submission_id = -1
        if need_submissions:
            last_submission_id = self._get_last_submission_id(start_submission_id)

        # we need to store the analysis and submission IDs separately in the order we received them
        # from the API. this is because since 4.0.0 with the _last_id parameter, analyses and submissions
        # are not returned in the order of their IDs but in the order in which they finished. therefore
        # we cannot store the highest ID as last_id but we need to store the last ID returned by the API.
        analysis_ids: List[int] = []
        submission_ids: List[int] = []

        # fill the input queue. max_items can be much higher than the number of results
        # from the Analyzer. Hence, we remember last_submission_id
        # on every iteration so we can continue from there on.
        self.failed_tasks = self._load_failed_tasks()

        while not tasks_queue.full():
            cur_analyses = []
            cur_submissions = []

            # get analyses and submissions
            if need_submissions:
                cur_submissions = self.get_submission_tasks(vmray_api,
                                                            last_submission_id,
                                                            submission_max_timeout)
            if need_analyses and cur_submissions:
                cur_analyses = self.get_analysis_tasks(vmray_api, cur_submissions)

            logging.debug(
                "VMRAY got %d analysis tasks and %d submission tasks, %d previously failed tasks",
                len(cur_analyses), len(cur_submissions), len(self.failed_tasks))

            # merge lists
            tasks = list(roundrobin(cur_analyses, cur_submissions, self.failed_tasks))

            if not tasks:
                # no more new tasks found. Queue, is not full start processing anyway
                break

            for task in tasks:
                try:
                    # put them one by one into the queue and remember the last_analysis_id /
                    # last_submission_id
                    if "analysis_id" in task:
                        tasks_queue.put_nowait(task)
                        last_analysis_id = task["analysis_id"]
                        analysis_ids.append(last_analysis_id)
                        logging.debug("VMRAY analysis_id %s added to queue", last_analysis_id)
                    elif "submission_id" in task:
                        tasks_queue.put_nowait(task)
                        last_submission_id = task["submission_id"]
                        submission_ids.append(last_submission_id)
                        logging.debug("VMRAY submission_id %s added to queue", last_submission_id)
                    elif "failed_tries" in task:
                        # Treat failed tasks separately we don't want to consider there id's as "last id".
                        tasks_queue.put_nowait(task)
                        self.failed_tasks.remove(task)
                    else:
                        logging.error("Unknown task found: %s", task)
                except queue.Full:
                    # queue is full. we can start processing.
                    logging.info("queue full, stop looking for tasks")
                    break

        if tasks_queue.empty():
            logging.info("Queue empty, no new analysis to process.")
            return

        nr_tasks = tasks_queue.qsize()
        workers: List[threading.Thread] = []

        logging.info("Starting worker threads")
        for _ in range(min(nr_tasks, self.max_worker_threads)):
            # start the workers to process the elements in the queue
            vmray_api_worker = None
            try:
                # every worker gets its own VMRay api instance, so we can download
                # data more effectively.
                vmray_api_worker = VMRay(
                    server_ip,
                    api_key,
                    not disable_verify,
                    http_proxy,
                    self.restricted_mode,
                )
            except ReadTimeout:
                logging.exception(
                    "Connection timed out while creating the VMRay REST API. "
                    "Trying to continue anyway."
                )
                continue
            except ConnectionError:
                logging.exception(
                    "Could not connect to the VMRay server. Make sure the host is reachable. "
                    "Trying to continue anyway.",
                )
                continue
            except Exception:  # pylint: disable=broad-except
                logging.exception("Could not instantiate VMRay API worker. Trying to continue anyway.")
                continue
            # start the worker
            worker = threading.Thread(
                target=self.worker_process_tasks,
                args=(tasks_queue, processed_tasks_queue, vmray_api_worker),
            )
            worker.setDaemon(True)
            worker.start()
            workers.append(worker)

        # wait until the workers return
        for worker in workers:
            worker.join()

        if not tasks_queue.empty():
            msg = ("All threads terminated but the input queue is not completely processed. Hence,"
                   " something went wrong, continueing anyway...")
            logging.error(msg)

        if processed_tasks_queue.qsize() != nr_tasks:
            msg = ("Not all task items were processed. Maybe some analysis is missing or corrupted. "
                   "Continueing anyway...")
            logging.error(msg)

        logging.info("All Threads finished")

        if processed_tasks_queue.empty():
            logging.error("No task was processed. This is not good, maybe some analyses are corrupted")

        # sort the tasks by the order in which we received them from the API. this is necessary so
        # that we are able to store the correct last_id (see comment above).
        def sort_fn(task):
            task_type = task.get("task_type", "UNKNOWN")
            task_id = task.get("task_id", -1)
            if task_type == "analysis" and task_id in analysis_ids:
                return analysis_ids.index(task_id)
            if task_type == "submission" and task_id in submission_ids:
                return submission_ids.index(task_id)
            # Don't use previously failed tasks as "last_id", they are handled separatly.
            if not task.get("failed_tries") and not task.get("succeeded_previously_failed_task"):
                # should not happen
                logging.warning("Invalid task type or id: type=%s id=%d", task_type, task_id)
            return 0

        sorted_processed_tasks: List[Dict[str, Any]] = sorted(
            processed_tasks_queue.queue, key=sort_fn, reverse=True,
        )

        # write the results to splunk
        num_analyses_added = 0
        num_submissions_added = 0
        num_previously_failed_tasks_succeeded = 0
        logging.info("Evaluate task results")
        while sorted_processed_tasks:
            is_previously_failed_task = False
            processed_task = sorted_processed_tasks.pop()

            if processed_task.get("succeeded_previously_failed_task"):
                # This task failed previously but succeeded this time. Remove it from the failed
                # task list.
                self._remove_failed_task(processed_task)
                # del processed_task["failed_tries"]
                # del processed_task["succeeded_previously_failed_task"]
                num_previously_failed_tasks_succeeded += 1
                is_previously_failed_task = True

            elif processed_task.get("failed_tries"):
                if processed_task["failed_tries"] >= MAX_TRIES:
                    logging.error(
                        "Tried import task id %d, %d times without success, skip it now.",
                        processed_task["task_id"],
                        MAX_TRIES,
                    )
                    self._remove_failed_task(processed_task)
                # Remember this task so we can try this later again.
                self._add_failed_task(processed_task)
                continue

            # get all the info needed to write the event
            task_id = processed_task.get("task_id", -1)
            task_type = processed_task.get("task_type", "UNKNOWN")
            try:
                # we explicitly give the time via the eventwriter because this
                # seems much easier than to let splunk parse the event and get the
                # correct date
                if task_type == "analysis":
                    creation_time = calendar.timegm(datetime.strptime(
                        processed_task["analysis"]["analysis_created"], "%Y-%m-%dT%H:%M:%S").timetuple())
                elif task_type == "submission":
                    creation_time = calendar.timegm(datetime.strptime(
                        processed_task["submission"]["submission_created"], "%Y-%m-%dT%H:%M:%S").timetuple())
                else:
                    raise ValueError(f"Unknown task type {task_type}")
            except Exception:  # pylint: disable=broad-except
                logging.exception("Error extracting time. Setting time to 0")
                creation_time = 0

            # handler table which calls the right write back function for the currently processed task
            # structure:
            # {name of the event: (
            #    bool specifying if the write back should occur,
            #    function which implements the write back,
            #    {arguments to write back function}
            # )}
            default_arguments = {
                "ev_writer": event_writer,
                "stanza": self.input_name,
                "_time": creation_time,
                "index": config["index"]
            }
            event_handlers: Dict[str, Tuple[bool, Callable[..., Any], Dict[str, Any]]] = {
                "analysis": (
                    self.import_analysis,
                    writeback_generic.write_analysis_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:analysis"
                    }
                ),
                "timing": (
                    True,
                    writeback_generic.write_timing_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:timing"
                    }
                ),
                "summary_v2": (
                    self.should_import_summary,
                    SummaryV2EventWriter(
                        import_vti_match=self.import_vti_match,
                        import_yara_match=self.import_yara_match,
                        import_av_match=self.import_av_match,
                        import_network=self.import_network,
                        import_reputation_lookup=self.import_reputation_lookup,
                        import_artifacts=self.import_artifacts,
                        import_iocs_only=self.import_iocs_only,
                        import_analysis_details=self.import_analysis_details,
                        import_remark=self.import_remark,
                        import_static_data=self.import_static_data
                    ),
                    {
                        **default_arguments,
                        # sourcetype is set in write_summary_event
                        "sourcetype": None
                    }
                ),
                "size": (
                    True,
                    writeback_generic.write_size_event,
                    {
                        **default_arguments,
                        "index": config["index"],
                        "sourcetype": "vmray:size"
                    }
                ),
                "submission": (
                    self.import_submission,
                    writeback_generic.write_submission_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:submission"
                    }
                ),
                "sample": (
                    True,
                    writeback_generic.write_sample_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:sample"
                    }
                ),
                "extracted_strings": (
                    self.import_extracted_strings,
                    writeback_generic.write_extracted_strings_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:extracted_strings"
                    }
                ),
                "malware_configurations": (
                    self.import_malware_config,
                    writeback_generic.write_malware_configuration_event,
                    {
                        **default_arguments,
                        "sourcetype": "vmray:malware_config"
                    }
                ),
            }

            # iterate through the handlers and see if a matching event is in the current task and see
            # if the event should actually be written to splunk.
            for evnt, (cond, ev_write_func, args) in event_handlers.items():
                if evnt not in processed_task or not cond:
                    continue

                # put the data into the arguments dict which will be given to the write back function
                args["data"] = processed_task
                try:
                    logging.debug("Writing event '%s' of task '%s' with id %d",
                                  evnt, task_type, task_id)
                    # call the handler function
                    ev_write_func(**args)
                except Exception:  # pylint: disable=broad-except
                    logging.exception("Error writing %s event of task %s %d "
                                      "(%s)", evnt, task_type, task_id, str(args))

            # save the last_submission_id so we know where we left off
            try:
                if task_type == "analysis" and not is_previously_failed_task:
                    num_analyses_added += 1
                elif task_type == "submission" and not is_previously_failed_task:
                    num_submissions_added += 1
                    self._save_last_submission_id(task_id)
                elif not is_previously_failed_task:
                    raise ValueError("Could not save id of unknown task type")
            except Exception:  # pylint: disable=broad-except
                logging.critical("Could not save last_submission_id", exc_info=True)
                sys.exit(1)
        self._save_failed_tasks()

        logging.info(
            "%d analyses and %d submissions added, %d previously failed tasks succeeded this time",
            num_analyses_added,
            num_submissions_added,
            num_previously_failed_tasks_succeeded,
        )

    def _load_settings(self, config):
        self.restricted_mode = int(config.get("restricted_mode", "0")) == 1
        self.import_analysis = int(config.get("import_analysis", "0")) == 1
        self.import_yara_match = int(config.get("import_yara_match", "0")) == 1
        self.import_vti_match = int(config.get("import_vti_match", "0")) == 1
        self.import_artifacts = int(config.get("import_artifacts", "0")) == 1
        self.import_iocs_only = int(config.get("import_iocs_only", "0")) == 1
        self.import_av_match = int(config.get("import_av_match", "0")) == 1
        self.import_network = int(config.get("import_network", "0")) == 1
        self.import_malware_config = int(config.get("import_malware_config", "0")) == 1
        self.import_reputation_lookup = int(config.get("import_reputation_lookup", "0")) == 1
        self.import_extracted_strings = int(config.get("import_extracted_strings", "0")) == 1
        self.import_analysis_details = int(config.get("import_analysis_details", "0")) == 1
        self.import_remark = int(config.get("import_remark", "0")) == 1
        self.import_static_data = int(config.get("import_static_data", "0")) == 1

        # Submission/Sample related
        self.import_submission = int(config.get("import_submission", "0")) == 1
        self.import_sample = int(config.get("import_sample", "0")) == 1

        # More settings
        self.import_timing = int(config.get("import_timing", "0")) == 1
        self.import_size = int(config.get("import_size", "0")) == 1
        self.import_debug_notfications = int(config.get("import_debug_notfications", "0")) == 1

        # all events for which we need the summary_v2.json
        self.should_import_summary = any([
            self.import_yara_match, self.import_vti_match, self.import_artifacts,
            self.import_av_match, self.import_network, self.import_reputation_lookup,
            self.import_analysis_details, self.import_remark, self.import_static_data,
            self.import_remark, self.import_extracted_strings, self.import_malware_config,
        ])


if __name__ == "__main__":
    logging.info("RUN VMRayModularInput")
    EXIT_CODE = VMRayModularInput().run(sys.argv)
    logging.info("Exiting VMRayModularInput with exit code: %s", EXIT_CODE)
    sys.exit(EXIT_CODE)
