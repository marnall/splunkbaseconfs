import calendar
import datetime
import itertools
import logging
try:
    import queue as Queue
except ImportError:
    import Queue
import re
import sys
import threading
import traceback

# pylint: disable=wrong-import-order
from lib.rest_cmds import VMRay
from requests import ConnectionError  # pylint: disable=redefined-builtin


import splunklib.client as sc  # pylint: disable=no-name-in-module
import splunklib.modularinput as smi
import splunklib.six as six

import aggregator_functions
import writeback_functions


# setup logging. this will land in ExecProcessor (which defaults to INFO)
DEFAULT_LOG_LEVEL = logging.WARNING
logging.root.setLevel(DEFAULT_LOG_LEVEL)
LOG_FORMAT = "%(levelname)s VMRAY %(message)s"
FORMATTER = logging.Formatter(LOG_FORMAT)
HANDLER = logging.StreamHandler(stream=sys.stderr)
HANDLER.setFormatter(FORMATTER)
logging.root.addHandler(HANDLER)

# disable info logging of imported modules
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# this will be shown in the source and is the name of our modinput
MODIN_NAME = "vmray_analyzer"
APP_FOLDER = "TA-vmray-analyzer"
DEF_MAX_ITEMS = 500
DEF_SUBMISSION_MAX_TIMEOUT = 4.0
DEF_FILE_INTEL_EXPORT_THRESHOLD = 75
DEBUG_TIMING = True


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

    def __init__(self):
        super(VMRayModularInput, self).__init__()
        self.import_analysis = False
        self.import_timing = False
        self.import_vti_result = False
        self.import_glog = False
        self.import_stix = False
        self.import_yara = False
        self.import_summary = False
        self.restricted_mode = False
        self.import_size = False
        self.import_submission = False
        self.import_sample = False

        self.import_local_av = False
        self.import_mitre_attack = False
        self.import_network = False
        self.import_reputation = False
        self.import_whois = False

        self.import_artifacts = False
        self.import_artifact_operations = False
        self.import_extracted_files = False
        self.import_processes = False
        self.import_vm_and_analyzer = False
        self.import_remarks = False
        self.import_static_data = False

        self.import_extracted_strings = False

        # @TODO: add argument and aggregator/writer
        self.import_debug_notfications = False
        self.import_job_cfg = False
        self.import_job_desc = False

        self.server_uri = None
        self.session_key = None
        self.input_name = None
    ############################################################################
    # Setup and validation functions
    ############################################################################

    def get_scheme(self):
        """specifies the setup dialog and required config values"""
        scheme = smi.Scheme(MODIN_NAME)
        scheme.title = "VMRay Analyzer"
        scheme.description = "Streams VMRay Analyzer analyses."
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        server_ip_argument = smi.Argument("server_ip")
        server_ip_argument.title = "Server IP Address"
        server_ip_argument.data_type = smi.Argument.data_type_string
        server_ip_argument.description = (
            "The IP address of the VMRay Analyzer Server.")
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

        start_analysis_id_argument = smi.Argument("start_analysis_id")
        start_analysis_id_argument.title = "Start Analysis ID"
        start_analysis_id_argument.data_type = smi.Argument.data_type_number
        start_analysis_id_argument.description = (
            "The starting analysis_id. Analyses with a lower id will not be"
            " imported into Splunk. If not specified all analyses are "
            "imported.")
        start_analysis_id_argument.required_on_create = False
        start_analysis_id_argument.required_on_edit = False
        scheme.add_argument(start_analysis_id_argument)

        start_submission_id_argument = smi.Argument("start_submission_id")
        start_submission_id_argument.title = "Start Submission ID"
        start_submission_id_argument.data_type = smi.Argument.data_type_number
        start_submission_id_argument.description = (
            "The starting submission_id. Submission with a lower id will not be"
            " imported into Splunk. If not specified all submissions are "
            "imported.")
        start_submission_id_argument.required_on_create = False
        start_submission_id_argument.required_on_edit = False
        scheme.add_argument(start_submission_id_argument)

        max_items_argument = smi.Argument("max_items")
        max_items_argument.title = "Maximum Number of Items Requested"
        max_items_argument.data_type = smi.Argument.data_type_number
        max_items_argument.description = (
            ("The maximum number of itemes requested from the VMRay REST API"
             " per interval (default = %d). Zero defaults to the previously"
             " mentioned value.") % (DEF_MAX_ITEMS))
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
            ("Hours to wait before an unfinished submission is imported to Splunk (default = %f") % (
                DEF_SUBMISSION_MAX_TIMEOUT))
        submission_max_timeout_argument.required_on_create = False
        submission_max_timeout_argument.required_on_edit = False
        scheme.add_argument(submission_max_timeout_argument)

        import_sample_argument = smi.Argument("import_sample")
        import_sample_argument.title = "Enable Sample import"
        import_sample_argument.data_type = smi.Argument.data_type_boolean
        import_sample_argument.description = "Enables the sample import."
        scheme.add_argument(import_sample_argument)

        import_stix_argument = smi.Argument("import_stix")
        import_stix_argument.title = "Enable Stix import"
        import_stix_argument.data_type = smi.Argument.data_type_boolean
        import_stix_argument.description = "Enables the stix report import."
        scheme.add_argument(import_stix_argument)

        import_glog_argument = smi.Argument("import_glog")
        import_glog_argument.title = "Enable Glog import"
        import_glog_argument.data_type = smi.Argument.data_type_boolean
        import_glog_argument.description = (
            "Enables the glog report import. WARNING: The Glog log files can"
            " be quite big. Make sure to set quotas to not exeed any data"
            " limits.")
        scheme.add_argument(import_glog_argument)

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

        import_vti_result_argument = smi.Argument("import_vti_result")
        import_vti_result_argument.title = "Enable vti_result import"
        import_vti_result_argument.data_type = smi.Argument.data_type_boolean
        import_vti_result_argument.description = (
            "Enables the vti_result json import.")
        scheme.add_argument(import_vti_result_argument)

        import_yara_argument = smi.Argument("import_yara")
        import_yara_argument.title = "Enable yara import"
        import_yara_argument.data_type = smi.Argument.data_type_boolean
        import_yara_argument.description = (
            "Enables the yara json import.")
        scheme.add_argument(import_yara_argument)

        import_summary_argument = smi.Argument("import_summary")
        import_summary_argument.title = "Enable summary import"
        import_summary_argument.data_type = smi.Argument.data_type_boolean
        import_summary_argument.description = (
            "Enables the summary json import.")
        scheme.add_argument(import_summary_argument)

        restricted_mode_argument = smi.Argument("restricted_mode")
        restricted_mode_argument.title = "Internal Restricted Import Mode"
        restricted_mode_argument.data_type = smi.Argument.data_type_boolean
        restricted_mode_argument.description = (
            "Removes imported data for internal compliance.")
        scheme.add_argument(restricted_mode_argument)

        import_local_av_argument = smi.Argument("import_local_av")
        import_local_av_argument.title = "Enable local AV import"
        import_local_av_argument.data_type = smi.Argument.data_type_boolean
        import_local_av_argument.description = "Enables the local AV import"
        scheme.add_argument(import_local_av_argument)

        import_mitre_attack_argument = smi.Argument("import_mitre_attack")
        import_mitre_attack_argument.title = "Enable MITRE ATT&CK import"
        import_mitre_attack_argument.data_type = smi.Argument.data_type_boolean
        import_mitre_attack_argument.description = "Enables the MITRE ATT&CK import"
        scheme.add_argument(import_mitre_attack_argument)

        import_reputation_argument = smi.Argument("import_reputation")
        import_reputation_argument.title = "Enable reputation lookup import"
        import_reputation_argument.data_type = smi.Argument.data_type_boolean
        import_reputation_argument.description = "Enables the reputation lookup import"
        scheme.add_argument(import_reputation_argument)

        import_whois_argument = smi.Argument("import_whois")
        import_whois_argument.title = "Enable WHOIS import"
        import_whois_argument.data_type = smi.Argument.data_type_boolean
        import_whois_argument.description = "Enables the WHOIS data import"
        scheme.add_argument(import_whois_argument)

        import_artifacts_argument = smi.Argument("import_artifacts")
        import_artifacts_argument.title = "Enable artifacts import"
        import_artifacts_argument.data_type = smi.Argument.data_type_boolean
        import_artifacts_argument.description = "Enables the artifacts import"
        scheme.add_argument(import_artifacts_argument)

        import_artifact_operations_argument = smi.Argument("import_artifact_operations")
        import_artifact_operations_argument.title = "Enable artifact operations import"
        import_artifact_operations_argument.data_type = smi.Argument.data_type_boolean
        import_artifact_operations_argument.description = "Enables the artifact operations import"
        scheme.add_argument(import_artifact_operations_argument)

        import_extracted_files_argument = smi.Argument("import_extracted_files")
        import_extracted_files_argument.title = "Enable extracted_files import"
        import_extracted_files_argument.data_type = smi.Argument.data_type_boolean
        import_extracted_files_argument.description = "Enables the extracted files import"
        scheme.add_argument(import_extracted_files_argument)

        import_extracted_strings_argument = smi.Argument("import_extracted_strings")
        import_extracted_strings_argument.title = "Extracted Strings"
        import_extracted_strings_argument.data_type = smi.Argument.data_type_boolean
        import_extracted_strings_argument.description = \
            "Information about the strings extracted from the dynamic behavior of the processes"
        scheme.add_argument(import_extracted_strings_argument)

        import_processes_argument = smi.Argument("import_processes")
        import_processes_argument.title = "Enable processes import"
        import_processes_argument.data_type = smi.Argument.data_type_boolean
        import_processes_argument.description = "Enables the processes import"
        scheme.add_argument(import_processes_argument)

        import_network_argument = smi.Argument("import_network")
        import_network_argument.title = "Enable network import"
        import_network_argument.data_type = smi.Argument.data_type_boolean
        import_network_argument.description = "Enables the network data import"
        scheme.add_argument(import_network_argument)

        import_vm_and_analyzer_argument = smi.Argument("import_vm_and_analyzer")
        import_vm_and_analyzer_argument.title = "Enable vm_and_analyzer import"
        import_vm_and_analyzer_argument.data_type = smi.Argument.data_type_boolean
        import_vm_and_analyzer_argument.description = "Enables the vm and analyzer import"
        scheme.add_argument(import_vm_and_analyzer_argument)

        import_remarks_argument = smi.Argument("import_remarks")
        import_remarks_argument.title = "Enable remarks import"
        import_remarks_argument.data_type = smi.Argument.data_type_boolean
        import_remarks_argument.description = "Enables the remarks import"
        scheme.add_argument(import_remarks_argument)

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
            VMRayModularInput._get_splunk_service(
                definition.metadata["server_uri"],
                definition.metadata["session_key"])
        except Exception:
            raise ValueError("Could not establish connection with Splunk API")

        try:
            # check if we can reach the server and are able to make queries
            VMRay(definition.parameters["server_ip"],
                  definition.parameters["api_key"],
                  definition.parameters["disable_verify"] == "0",
                  definition.parameters.get("http_proxy", ""),
                  definition.parameters.get("restricted_mode", False))
        except ConnectionError:
            logging.exception("Could not connect to the VMRay server ")
            raise ValueError(
                "Could not connect to the VMRay server. Make sure the host is"
                " reachable and your proxy, if specified, is correct.")
        except Exception:
            logging.exception("Could not query the VMRay REST API ")
            raise ValueError(
                "Could not query the VMRay REST API make sure the API Key is"
                " valid and the corresponding user is enabled. Disable "
                "certificate verification if necessary.")
        if (definition.parameters.get("start_analysis_id", None) is
                not None):
            try:
                # the start anlysis must be larger than 0
                start_analysis_id = int(
                    definition.parameters["start_analysis_id"])
                if start_analysis_id <= 0:
                    raise ValueError()
            except Exception:
                raise ValueError(
                    "Start Analysis ID is not valid. The ID must be an "
                    "integer greater than 0.")

        if (definition.parameters.get("start_submission_id", None) is
                not None):
            try:
                # the start anlysis must be larger than 0
                start_submission_id = int(
                    definition.parameters["start_submission_id"])
                if start_submission_id <= 0:
                    raise ValueError()
            except Exception:
                raise ValueError(
                    "Start Submission ID is not valid. The ID must be an "
                    "integer greater than 0.")

        if definition.parameters["max_items"] is not None:
            try:
                # must be positive int
                if int(definition.parameters["max_items"]) < 0:
                    raise ValueError()
            except Exception:
                raise ValueError("Number of Requests is not an integer")

        if definition.parameters["submission_max_timeout"] is not None:
            try:
                # must be positive
                if float(definition.parameters["submission_max_timeout"]) < 0:
                    raise ValueError()
            except Exception:
                raise ValueError("Max timeout must be a float number")

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
        return sc.connect(host=host, port=port,
                          app=APP_FOLDER, sharing="app", token=session_key)

    def _load_last_analysis_id(self):
        """loads the last_analysis_id from a config using the splunk rest api.
        see _save_last_analysis_id
        """

        service = self._get_splunk_service(self.server_uri, self.session_key)
        if MODIN_NAME not in service.confs:
            conf = service.confs.create(MODIN_NAME)
        else:
            conf = service.confs[MODIN_NAME]

        if self.input_name not in conf:
            stanza = conf.create(self.input_name)
        else:
            stanza = conf[self.input_name]

        if "last_analysis_id" in stanza.content:
            logging.debug("Stanza %s in %s last_analysis_id %d",
                          self.input_name, MODIN_NAME,
                          int(stanza.content["last_analysis_id"]))
            return int(stanza.content["last_analysis_id"])
        return -1

    def _get_last_analysis_id(self, start_analysis_id):
        """get the last analysis id and compute the actual analysis id to start with."""
        try:
            last_analysis_id = self._load_last_analysis_id()
        except Exception:  # pylint: disable=broad-except
            logging.critical("Could not load last_analysis_id.", exc_info=True)
            sys.exit(-1)
        logging.info("Loaded last_analysis_id %d", last_analysis_id)

        if start_analysis_id == -1:
            # no start analysis id was given
            if last_analysis_id <= 0:
                last_analysis_id = 1
            # else use last_analysis_id
        else:
            if last_analysis_id <= 0:
                # no last_analysis_id was given
                last_analysis_id = start_analysis_id - 1
            elif last_analysis_id < start_analysis_id:
                # we probably updated the start_anlysis_id field
                last_analysis_id = start_analysis_id - 1
            # else use last_analysis_id

        return last_analysis_id

    def _save_last_analysis_id(self, last_analysis_id):
        """saves the last_analysis_id in a config file using the splunk rest
        api. We create a config in
        $SPLUNK_HOME/etc/apps/<my_app>/local/MODIN_NAME and every input has
        its own stanza where we write the value. the value is loaded with
        _load_last_analysis_id"""

        service = self._get_splunk_service(self.server_uri, self.session_key)
        # create or get the config
        if MODIN_NAME not in service.confs:
            conf = service.confs.create(MODIN_NAME)
        else:
            conf = service.confs[MODIN_NAME]

        # create or get the appropriate stanza from the config
        if self.input_name not in conf:
            stanza = conf.create(self.input_name)
        else:
            stanza = conf[self.input_name]
        # update the value
        stanza.submit({"last_analysis_id": last_analysis_id})

    def _load_last_submission_id(self):
        """loads the last_submission_id from a config using the splunk rest api.
        see _save_last_analysis_id
        """

        service = self._get_splunk_service(self.server_uri, self.session_key)
        if MODIN_NAME not in service.confs:
            conf = service.confs.create(MODIN_NAME)
        else:
            conf = service.confs[MODIN_NAME]

        if self.input_name not in conf:
            stanza = conf.create(self.input_name)
        else:
            stanza = conf[self.input_name]

        if "last_submission_id" in stanza.content:
            logging.debug("Stanza %s in %s last_submission_id %d",
                          self.input_name, MODIN_NAME,
                          int(stanza.content["last_submission_id"]))
            return int(stanza.content["last_submission_id"])
        return -1

    def _get_last_submission_id(self, start_submission_id):
        try:
            last_submission_id = self._load_last_submission_id()
        except Exception:  # pylint: disable=broad-except
            logging.critical("Could not load last_submission_id.",
                             exc_info=True)
            sys.exit(-1)
        logging.info("Loaded last_submission_id %d", last_submission_id)

        if start_submission_id == -1:
            # no start submission id was given
            if last_submission_id <= 0:
                last_submission_id = 1
        else:
            if last_submission_id <= 0:
                last_submission_id = start_submission_id - 1
            elif last_submission_id < start_submission_id:
                # we probably updated the start_submission_id field
                last_submission_id = start_submission_id - 1

        return last_submission_id

    def _save_last_submission_id(self, last_submission_id):
        """saves the last_submission_id in a config file using the splunk rest
        api. We create a config in
        $SPLUNK_HOME/etc/apps/<my_app>/local/MODIN_NAME and every input has
        its own stanza where we write the value. the value is loaded with
        _load_last_submission_id"""

        service = self._get_splunk_service(self.server_uri, self.session_key)
        if MODIN_NAME not in service.confs:
            conf = service.confs.create(MODIN_NAME)
        else:
            conf = service.confs[MODIN_NAME]

        if self.input_name not in conf:
            stanza = conf.create(self.input_name)
        else:
            stanza = conf[self.input_name]
        stanza.submit({"last_submission_id": last_submission_id})

    @staticmethod
    def get_analysis_tasks(vmray_api, last_analysis_id):
        """Query the Analyzer to receive a list of X analyses with analysis_id
        >= last_analysis_id. X depends on the query limits. Returns empty list
        on error.
        """
        try:
            cur_analyses = vmray_api.get_analyses(last_analysis_id=last_analysis_id)
        except Exception:  # pylint: disable=broad-except
            logging.exception("An exception occured while retrieving "
                              "analyses. trying to continue anyway...")
            cur_analyses = []

        return cur_analyses

    @staticmethod
    def get_submission_tasks(vmray_api, last_submission_id, max_timeout):
        """Like get_analysis_tasks but with submissions"""
        try:
            # in contrast to analyses, an arbitrary number of consecutively numbered
            # submissions can include submissions that are not finished yet. Hence,
            # if we want to ingest them we have to wait until they are finished.
            # If the submission is younger than max_timeout we will try to continue
            # with already finished submissions and will retry to collect the submission
            # to a later point in time. If we are still not able to collect the
            # submission we will skip it.
            # this handling applies only to analyzer < 4.0.0. starting with that version
            # the _last_id mechanism was introduced which only returns finished submissions.
            cur_submissions = vmray_api.get_submissions(last_submission_id=last_submission_id)
            cut_off = None
            for sub_idx, sub in enumerate(cur_submissions):
                if not sub["submission_finished"]:
                    # check if the submission is too old
                    if (max_timeout >= 0
                            and datetime.datetime.strptime(sub["submission_created"], "%Y-%m-%dT%H:%M:%S")
                            < datetime.datetime.now() - datetime.timedelta(hours=max_timeout)):
                        # the submission is older than our threshold
                        continue
                    cut_off = sub_idx
                    break
            if cut_off is not None:
                cur_submissions = cur_submissions[:cut_off]

        except Exception:  # pylint: disable=broad-except
            logging.exception("An exception occured while retrieving "
                              "submissions. trying to continue anyway...")
            cur_submissions = []

        return cur_submissions

    ############################################################################
    # Main worker routine. Collects the required info for each task
    ############################################################################

    def worker_process_tasks(self, tasks_queue, processed_tasks_queue, vmray_api):
        """worker thread implementation. Processes tasks by collecting the info
        required by the resulting event using the aggregator functions. uses the
        queues (i.e. task_done) to signal that the jobs are processed."""
        logging.info("Worker started")
        while True:
            try:
                my_task = tasks_queue.get_nowait()
            except Queue.Empty:
                # all done. terminate the thread
                break
            try:
                # get the task info of the currently processed task
                task_type = None
                task_id = None
                analysis_id = my_task.get("analysis_id", None)
                submission_id = my_task.get("submission_id", None)

                if analysis_id is not None:
                    task_type = "analysis"
                    task_id = analysis_id
                if submission_id is not None:
                    task_type = "submission"
                    task_id = submission_id

                assert sum([x is not None for x in [analysis_id, submission_id]]) == 1

                logging.debug("WORKER id=%d type=%s Start processing",
                              task_id, task_type)

                my_results = {"task_type": task_type, "task_id": task_id}

                # Do version filtering
                # 3.2 and newer
                self.import_static_data = self.import_static_data if (vmray_api.version_major >= 3
                                                                      and vmray_api.version_minor >= 2)\
                    else False

                self.import_extracted_strings = self.import_extracted_strings if (vmray_api.version_major >= 3
                                                                                  and vmray_api.version_minor >= 2) \
                    else False

                # imports to fetch
                # is the current task created by a new analysis?
                if task_type == "analysis":

                    # handler table for the different imports.
                    # structure:
                    # ([list of events provided by the entry],
                    #  bool specifying whether or not the information should be gathered,
                    #  function to be called to gather the information,
                    #  {dict of arguments to function must have vmray_api and analysis_id})
                    imports = [
                        (
                            ["analysis"],
                            True,
                            aggregator_functions.get_analysis,
                            {"data": my_task}
                        ),
                        (
                            ["timing"],
                            self.import_timing,
                            aggregator_functions.get_timing,
                            {"vmray_api": vmray_api, "analysis_id": analysis_id}
                        ),
                        (
                            ["stix"],
                            self.import_stix,
                            aggregator_functions.get_stix,
                            {"vmray_api": vmray_api, "analysis_id": analysis_id}
                        ),
                        (
                            ["glog"], self.import_glog,
                            aggregator_functions.get_glog,
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
                            {"vmray_api": vmray_api, "analysis_id": analysis_id}
                        )
                    ]

                    # for version < 2.0.X we get vti_result and yara from their files from the additional folder
                    if (vmray_api.version_major < 2) or (vmray_api.version_major == 2 and vmray_api.version_minor < 1):
                        imports.append(
                            (
                                ["yara"],
                                self.import_yara,
                                aggregator_functions.get_yara,
                                {
                                    "vmray_api": vmray_api,
                                    "analysis_id": analysis_id
                                }
                            )
                        )
                        imports.append(
                            (
                                ["vti_result"],
                                self.import_vti_result,
                                aggregator_functions.get_vti_result,
                                {
                                    "vmray_api": vmray_api,
                                    "analysis_id": analysis_id
                                }
                            )
                        )

                    # version >= 2.1.X: get all the info from the summary.json.
                    else:
                        imports.append(
                            (
                                ["summary"],
                                any([
                                    self.import_yara,
                                    self.import_vti_result,
                                    self.import_artifacts,
                                    self.import_local_av,
                                    self.import_mitre_attack,
                                    self.import_network,
                                    self.import_reputation,
                                    self.import_whois,
                                    self.import_extracted_files,
                                    self.import_artifact_operations,
                                    self.import_processes,
                                    self.import_vm_and_analyzer,
                                    self.import_remarks,
                                    self.import_static_data
                                ]),
                                aggregator_functions.get_summary,
                                {
                                    "vmray_api": vmray_api,
                                    "analysis_id": analysis_id
                                }
                            )
                        )

                elif task_type == "submission":
                    # sampe as above but for tasks of type submission
                    imports = [
                        (
                            ["submission"],
                            True,
                            aggregator_functions.get_submission,
                            {
                                "submission": my_task
                            }
                        ),
                        (
                            ["sample"],
                            self.import_sample,
                            aggregator_functions.get_sample,
                            {
                                "vmray_api": vmray_api,
                                "sample_id": my_task.get("submission_sample_id", -1)
                            }
                        ),
                    ]

                # iterate through the handler table, see if the according handler must be called to gather information.
                # if so call the handler function and give the args dict as arguments.
                for imp_provides, do_imp, imp_func, imp_func_args in imports:
                    if do_imp:
                        logging.debug("WORKER id=%d type=%s fetching %s",
                                      task_id, task_type, repr(imp_provides))
                        imp_result = imp_func(**imp_func_args)
                        # legacy wise the handler functions returned None on error. Here, we fix up this behavior.
                        # because we anticipate that the resulting dict holds entry for all "promised" resulting events
                        if imp_result is None:
                            imp_result = {x: None for x in imp_provides}
                        else:
                            assert isinstance(imp_result, dict)
                            # fill up missing event keys in the dict with none. similar to above code
                            for missimg_imp in set(imp_provides) - set(imp_result.keys()):
                                imp_result[missimg_imp] = None
                            assert set(imp_provides) == set(imp_result.keys())

                        # put the results in the my_results dict. this will be put in the output queue
                        for given_imp_name, given_imp_result in imp_result.items():
                            my_results[given_imp_name] = given_imp_result

            except Exception as exc:
                logging.exception("WORKER id=%d type=%s Exception in worker",
                                  task_id, task_type)
                traceback.print_exc()
                raise exc
            finally:
                # write back to the result queue
                processed_tasks_queue.put(my_results)
                logging.debug("WORKER id=%d type=%s Worker task_done",
                              task_id, task_type)
                # we mark the task so we do not end up in an infinte loop
                tasks_queue.task_done()
        logging.info("WORKER Worker terminating")

    ############################################################################
    # Main function. Called whenever new inputs should be gathered.
    ############################################################################

    def stream_events(self, inputs, ew):
        """The main processing function"""

        # get the config stanza. Remember: we are working in multi instance
        # mode
        self.input_name, config = next(six.iteritems(inputs.inputs))
        self.server_uri = inputs.metadata["server_uri"]
        self.session_key = inputs.metadata["session_key"]

        # setup logging
        global LOG_FORMAT  # pylint: disable=global-statement
        global FORMATTER  # pylint: disable=global-statement
        LOG_FORMAT = ("%(levelname)s"
                      + (" VMRAY source=\"%s\" " % (self.input_name))
                      + "%(message)s")
        FORMATTER = logging.Formatter(LOG_FORMAT)
        HANDLER.setFormatter(FORMATTER)

        log_lvls = {
            "Default": DEFAULT_LOG_LEVEL,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = config.get(
            "log_level",
            {v: k for k, v in log_lvls.items()}[DEFAULT_LOG_LEVEL])
        logging.root.setLevel(log_lvls[log_level])

        logging.info("Setting log level to %s", log_level)

        logging.debug("Fetching new analyses with options:")
        logging.debug("inputs %s", inputs.inputs)
        logging.debug("metadata %s", inputs.metadata)

        logging.info("Getting new analyses from '%s'", self.input_name)
        # get necessary settings from the config

        server_ip = None
        if "server_ip" not in config:
            logging.critical("Server IP missing. Aborting...")
            sys.exit(-1)
        server_ip = config["server_ip"]

        api_key = config.get("api_key", None)
        if api_key is None:
            logging.critical("API not specified. Aborting")
            sys.exit(-1)

        http_proxy = config.get("http_proxy", "")

        if (config.get("max_items", None) is not None
                and int(config.get("max_items", None)) > 0):
            max_items = int(config["max_items"])
        else:
            max_items = DEF_MAX_ITEMS

        if config.get("submission_max_timeout", None) is not None:
            submission_max_timeout = float(config["submission_max_timeout"])
        else:
            submission_max_timeout = DEF_SUBMISSION_MAX_TIMEOUT

        if (config.get("start_analysis_id", None) is not None
                and int(config.get("start_analysis_id")) > 0):
            start_analysis_id = int(config["start_analysis_id"])
        else:
            start_analysis_id = -1

        if (config.get("start_submission_id", None) is not None
                and int(config.get("start_submission_id")) > 0):
            start_submission_id = int(config["start_submission_id"])
        else:
            start_submission_id = -1

        if config.get("disable_verify", None) is None:
            disable_verify = False
        else:
            disable_verify = int(config["disable_verify"]) == 1

        # we'll need those later in the worker threads. Hence, we save them as
        # object attributes

        # Legacy settings
        self.import_summary = int(config.get("import_summary", "0")) == 1

        # Settings
        self.restricted_mode = int(config.get("restricted_mode", "0")) == 1
        self.import_analysis = int(config.get("import_analysis", "0")) == 1
        self.import_yara = int(config.get("import_yara", "0")) == 1
        self.import_vti_result = int(config.get("import_vti_result", "0")) == 1
        self.import_artifacts = (int(config.get("import_artifacts", "0")) == 1) or self.import_summary
        self.import_local_av = int(config.get("import_local_av", "0")) == 1
        self.import_mitre_attack = int(config.get("import_mitre_attack", "0")) == 1
        self.import_network = int(config.get("import_network", "0")) == 1
        self.import_reputation = int(config.get("import_reputation", "0")) == 1
        self.import_whois = int(config.get("import_whois", "0")) == 1
        self.import_extracted_files = (
            (int(config.get("import_extracted_files", "0")) == 1) or self.import_summary)
        self.import_extracted_strings = int(config.get("import_extracted_strings", "0")) == 1
        self.import_artifact_operations = int(config.get("import_artifact_operations", "0")) == 1
        self.import_processes = int(config.get("import_processes", "0")) == 1
        self.import_vm_and_analyzer = int(config.get("import_vm_and_analyzer", "0")) == 1
        self.import_remarks = int(config.get("import_remarks", "0")) == 1
        self.import_static_data = int(config.get("import_static_data", "0")) == 1

        # Submission/Sample related
        self.import_submission = int(config.get("import_submission", "0")) == 1
        self.import_sample = int(config.get("import_sample", "0")) == 1

        # More settings
        self.import_stix = int(config.get("import_stix", "0")) == 1
        self.import_glog = int(config.get("import_glog", "0")) == 1
        self.import_timing = int(config.get("import_timing", "0")) == 1
        self.import_size = int(config.get("import_size", "0")) == 1
        self.import_debug_notfications = int(config.get("import_debug_notfications", "0")) == 1

        # check if we should get new analyses.
        need_analyses = any([
            self.import_analysis,
            self.import_yara,
            self.import_vti_result,
            self.import_artifacts,
            self.import_local_av,
            self.import_mitre_attack,
            self.import_network,
            self.import_reputation,
            self.import_whois,
            self.import_extracted_files,
            self.import_extracted_strings,
            self.import_artifact_operations,
            self.import_processes,
            self.import_vm_and_analyzer,
            self.import_remarks,
            self.import_static_data,
            self.import_submission,
            self.import_sample,
            self.import_stix,
            self.import_glog,
            self.import_timing,
            self.import_size,
            self.import_debug_notfications
        ])
        # check if we should get new submissions.
        need_submissions = any([self.import_sample, self.import_submission])

        if not any([need_analyses, need_submissions]):
            logging.info("Nothing to import (no import enabled). Terminating...")
            return

        try:
            logging.debug("Creating connection to REST API %s %s %d",
                          server_ip, api_key, int(not disable_verify))
            vmray_api = VMRay(server_ip, api_key, not disable_verify,
                              http_proxy, self.restricted_mode)
        except ConnectionError:
            logging.critical("Could not connect to the VMRay server. Make "
                             "sure the host is reachable", exc_info=True)
            sys.exit(-1)
        except Exception:  # pylint: disable=broad-except
            logging.critical(
                "Could not instantiate VMRay API. Make sure the server is "
                "running, the API key is corect, and disable the certificate "
                "verification if necessary. Aborting...", exc_info=True)
            sys.exit(-1)

        # setup our input queues which will feed the workers
        tasks_queue = Queue.Queue(maxsize=max_items)
        # setup our output queue which will be filled by the workers
        processed_tasks_queue = Queue.Queue(maxsize=max_items)

        # get the last_analysis_id we saved in an earlier iteration of this
        # script
        last_analysis_id = None
        last_submission_id = None
        if need_analyses:
            last_analysis_id = self._get_last_analysis_id(start_analysis_id)
        if need_submissions:
            last_submission_id = self._get_last_submission_id(start_submission_id)

        # we need to store the analysis and submission IDs separately in the order we received them
        # from the API. this is because since 4.0.0 with the _last_id parameter, analyses and submissions
        # are not returned in the order of their IDs but in the order in which they finished. therefore
        # we cannot store the highest ID as last_id but we need to store the last ID returned by the API.
        analysis_ids = []
        submission_ids = []

        # fill the input queue. max_items can be much higher than the number of results
        # from the Analyzer. Hence, we remember last_analysis_id last_submission_id
        # on every iteration so we can continue from there on.
        while not tasks_queue.full():
            cur_analyses = []
            cur_submissions = []

            # get analyses and submissions
            if need_analyses:
                cur_analyses = self.get_analysis_tasks(vmray_api,
                                                       last_analysis_id)
            if need_submissions:
                cur_submissions = self.get_submission_tasks(vmray_api,
                                                            last_submission_id,
                                                            submission_max_timeout)

            logging.debug("VMRAY got %d analysis tasks and %d submission tasks",
                          len(cur_analyses), len(cur_submissions))

            # merge lists
            tasks = list(roundrobin(cur_analyses, cur_submissions))

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
                        logging.debug("VMRAY analysis_id %d added to queue",
                                      last_analysis_id)
                    elif "submission_id" in task:
                        tasks_queue.put_nowait(task)
                        last_submission_id = task["submission_id"]
                        submission_ids.append(last_submission_id)
                        logging.debug("VMRAY submission_id %d added to queue",
                                      last_submission_id)
                    else:
                        logging.error("Unknown task found: %s", str(task))
                except Queue.Full:
                    # queue is full. we can start processing.
                    break

        if tasks_queue.empty():
            logging.info("No new analysis to process.")
            return

        nr_tasks = tasks_queue.qsize()
        workers = []

        logging.info("Starting worker threads")
        for _ in range(min(nr_tasks, 8)):
            # start the workers to process the elements in the queue
            vmray_api_worker = None
            try:
                # every worker gets its own VMRay api instance, so we can download
                # data more effectively.
                vmray_api_worker = VMRay(server_ip, api_key,
                                         not disable_verify, http_proxy,
                                         self.restricted_mode)
            except ConnectionError:
                logging.exception("Could not connect to the VMRay server. "
                                  "Make sure the host is reachable. "
                                  "Trying to continue anyway")
                continue
            except Exception:  # pylint: disable=broad-except
                logging.exception("Could not instantiate VMRay api for"
                                  " worker. Trying to continue anyway...")
                continue
            # start the worker
            worker = threading.Thread(
                target=self.worker_process_tasks, args=(
                    tasks_queue, processed_tasks_queue,
                    vmray_api_worker))
            worker.setDaemon(True)
            worker.start()
            workers.append(worker)

        # wait until the workers return
        for worker in workers:
            worker.join()

        if not tasks_queue.empty():
            err = ("All threads terminated but the input "
                   "queue is not completely processed. Hence, something went"
                   " wrong, continueing anyway...")
            logging.error(err)

        if processed_tasks_queue.qsize() != nr_tasks:
            err = ("Not all task items were processed. Maybe some analysis is"
                   " missing or corrupted. Continueing anyway...")
            logging.error(err)

        logging.info("All Threads finished")

        if processed_tasks_queue.empty():
            logging.error("No task was processed. This is not good,"
                          " maybe some analyses are corrupted")

        # sort the tasks by the order in which we received them from the API. this is necessary so
        # that we are able to store the correct last_id (see comment above).
        def sort_fn(task):
            task_type = task.get("task_type", "UNKNOWN")
            task_id = task.get("task_id", -1)
            if task_type == "analysis" and task_id in analysis_ids:
                return analysis_ids.index(task_id)
            if task_type == "submission" and task_id in submission_ids:
                return submission_ids.index(task_id)
            # should not happen
            logging.warn("Invalid task type or id: type=%s id=%d", task_type, task_id)
            return 0

        sorted_tasks = sorted(processed_tasks_queue.queue, key=sort_fn, reverse=True)

        # write the results to splunk
        num_analyses_added = 0
        num_submissions_added = 0
        while sorted_tasks:
            data = sorted_tasks.pop()

            # get all the info needed to write the event
            task_id = data.get("task_id", -1)
            task_type = data.get("task_type", "UNKNOWN")
            try:
                # we explicitly give the time via the eventwriter because this
                # seems much easier than to let splunk parse the event and get the
                # correct date
                if task_type == "analysis":
                    creation_time = calendar.timegm(datetime.datetime.strptime(
                        data["analysis"]["analysis_created"], "%Y-%m-%dT%H:%M:%S").timetuple())
                elif task_type == "submission":
                    creation_time = calendar.timegm(datetime.datetime.strptime(
                        data["submission"]["submission_created"], "%Y-%m-%dT%H:%M:%S").timetuple())
                else:
                    raise Exception
            except Exception:  # pylint: disable=broad-except
                logging.exception("Error extracting time. Setting time to 0")
                creation_time = 0

            # handler table which calls the right write back function for the currently processed task
            # structure:
            # {name of the event: (bool specifieing if the write back should occur,
            #                      function which implements the write back, {arguments to write back function})}
            event_handlers = {
                "analysis": (
                    self.import_analysis,
                    writeback_functions.write_analysis_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:analysis"
                    }
                ),
                "stix": (
                    True,
                    writeback_functions.write_stix_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:stix"
                    }
                ),
                "glog": (
                    True,
                    writeback_functions.write_glog_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:glog"
                    }
                ),
                "timing": (
                    True,
                    writeback_functions.write_timing_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:timing"
                    }
                ),
                "vti_result": (
                    self.import_vti_result,
                    writeback_functions.write_vti_result_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:vti_result"
                    }
                ),
                "yara": (
                    self.import_yara,
                    writeback_functions.write_yara_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:yara"
                    }
                ),
                "summary": (
                    any([
                        self.import_yara,
                        self.import_vti_result,
                        self.import_artifacts,
                        self.import_local_av,
                        self.import_mitre_attack,
                        self.import_network,
                        self.import_reputation,
                        self.import_whois,
                        self.import_extracted_files,
                        self.import_artifact_operations,
                        self.import_processes,
                        self.import_vm_and_analyzer,
                        self.import_remarks,
                        self.import_static_data
                    ]),
                    writeback_functions.SummaryEventWriter(
                        import_vti=self.import_vti_result,
                        import_yara=self.import_yara,
                        import_local_av=self.import_local_av,
                        import_mitre_attack=self.import_mitre_attack,
                        import_network=self.import_network,
                        import_reputation=self.import_reputation,
                        import_whois=self.import_whois,
                        import_artifacts=self.import_artifacts,
                        import_artifact_operations=self.import_artifact_operations,
                        import_extracted_files=self.import_extracted_files,
                        import_processes=self.import_processes,
                        import_vm_and_analyzer=self.import_vm_and_analyzer,
                        import_remarks=self.import_remarks,
                        import_static_data=self.import_static_data
                    ),
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        # sourcetype is set in write_summary_event
                        "sourcetype": None
                    }),
                "size": (
                    True,
                    writeback_functions.write_size_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:size"
                    }
                ),
                "submission": (
                    self.import_submission,
                    writeback_functions.write_submission_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:submission"
                    }
                ),
                "sample": (
                    True,
                    writeback_functions.write_sample_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:sample"
                    }
                ),
                "extracted_strings": (
                    self.import_extracted_strings,
                    writeback_functions.write_extracted_strings_event,
                    {
                        "ev_writer": ew,
                        "stanza": self.input_name,
                        "_time": creation_time,
                        "index": config["index"],
                        "sourcetype": "vmray:extracted_strings"
                    }
                ),
            }

            # iterate through the handlers and see if a matching event is in the current task and see if the event
            # should actually be written to splunk.
            for evnt in event_handlers:
                if evnt not in data:
                    continue
                cond, ev_write_func, args = event_handlers[evnt]
                if not cond:
                    continue

                # but the data into the arguments dict which will be given to the write back func
                args["data"] = data
                try:
                    logging.debug("Writing event '%s' of task '%s' with id %d",
                                  evnt, task_type, task_id)
                    # call the handler function
                    ev_write_func(**args)
                except Exception:  # pylint: disable=broad-except
                    logging.exception("Error writing %s event of task %s %d "
                                      "(%s)", evnt, task_type, task_id, str(args))


            # save the last_analysis_id so we know where we left off
            try:
                if task_type == "analysis":
                    num_analyses_added += 1
                    self._save_last_analysis_id(task_id)
                elif task_type == "submission":
                    num_submissions_added += 1
                    self._save_last_submission_id(task_id)
                else:
                    raise Exception("Could not save id of unknown task type")
            except Exception:  # pylint: disable=broad-except
                logging.critical("Could not save last_analysis_id", exc_info=True)
                sys.exit(-1)
        logging.info("%d analyses and %d submissions added", num_analyses_added, num_submissions_added)


if __name__ == "__main__":
    sys.exit(VMRayModularInput().run(sys.argv))
