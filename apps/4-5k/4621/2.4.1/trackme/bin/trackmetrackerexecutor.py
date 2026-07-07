#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json
import hashlib

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_tracker_executor.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_vtenant_component_info,
    trackme_register_tenant_object_summary,
    trackme_return_tenant_object_summary,
    run_splunk_search,
    trackme_register_tenant_component_summary,
    trackme_handler_events,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license


@Configuration(distributed=False)
class TrackMeTrackerExecutor(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The tracker component name to be executed.""",
        require=True,
        default=None,
        validate=validators.Match(
            "mode", r"^(?:splk-dsm|splk-dhm|splk-mhm|splk-flx|splk-wlk|splk-fqm)$"
        ),
    )

    report = Option(
        doc="""
        **Syntax:** **report=****
        **Description:** The tracker report to be executed.""",
        require=True,
        default=None,
    )

    args = Option(
        doc="""
        **Syntax:** **args=****
        **Description:** optional arguments to the report.""",
        require=False,
        default=None,
    )

    force_savedsearch_execmode = Option(
        doc="""
        **Syntax:** **force_savedsearch_execmode=****
        **Description:** force execution mode to be savedsearch.""",
        require=False,
        default=False,
    )    

    earliest = Option(
        doc="""
        **Syntax:** **earliest=****
        **Description:** The earliest time quantifier.""",
        require=False,
        default=None,
    )

    latest = Option(
        doc="""
        **Syntax:** **latest=****
        **Description:** The latest time quantifier.""",
        require=False,
        default=None,
    )

    alert_no_results = Option(
        doc="""
        **Syntax:** **alert_no_results=****
        **Description:** Alert if the tracker does not return any results, leading to a degraded Virtual Tenant Operation status.""",
        require=False,
        default=True,
        validate=validators.Boolean(),
    )

    def refresh_shadow(self, session_key, splunkd_uri, tenant_id, component, report=None):
        """
        Call the refresh_shadow admin endpoint to update the shadow copy.
        Called synchronously from generate() because Splunk's dispatch()
        terminates the process after the generator is consumed, killing
        any background threads regardless of daemon status.
        Bounded by the (5, 120) connect/read timeout.
        """
        # short component label for logging only (callers pass the long splk-<comp> form)
        component_short = (component or "").replace("splk-", "")
        try:
            import requests as req

            # Strip the splk- prefix if present (component in executor uses splk-dsm format)
            comp = component.replace("splk-", "")

            url = f"{splunkd_uri}/services/trackme/v2/component/admin/refresh_shadow"
            header = {
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            }
            body = {
                "tenant_id": tenant_id,
                "component": comp,
                "requester": report or "hybrid_tracker_executor",
            }

            response = req.post(
                url,
                headers=header,
                json=body,
                verify=False,
                timeout=(5, 120),
            )

            if response.status_code in (200, 201, 204):
                logging.info(
                    f'tenant_id="{tenant_id}", component="{component_short}", '
                    f'refresh_shadow completed successfully'
                )
            else:
                logging.warning(
                    f'tenant_id="{tenant_id}", component="{component_short}", '
                    f'refresh_shadow returned status={response.status_code}, '
                    f'response="{response.text[:500]}"'
                )

        except Exception as e:
            logging.warning(
                f'tenant_id="{tenant_id}", component="{component_short}", '
                f'refresh_shadow failed: {e}'
            )

    def register_component_summary(self, session_key, splunkd_uri, tenant_id, component):
        """
        Register the component summary. Called synchronously because Splunk's
        dispatch() terminates the process after the generator is consumed,
        killing any background threads regardless of daemon status.
        """
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logging.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logging.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    def generate(self, **kwargs):
        # performance counter
        start = time.time()

        # short component label for logging only: the component Option carries the
        # long "splk-<comp>" form (regex-validated, required for functional routing),
        # but logs emit the short form for cross-log consistency.
        component_short = self.component.replace("splk-", "")

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # set earliest and latest
        if not self.earliest:
            earliest = self._metadata.searchinfo.earliest_time
        else:
            earliest = self.earliest

        if not self.latest:
            latest = self._metadata.searchinfo.latest_time
        else:
            latest = self.latest

        # set bool
        detected_failure_register = False

        # A list to store any exceptions encountered during the execution
        exceptions = []

        # check license state
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"], session_key
            )
            license_is_valid = check_license.get("license_is_valid")
            license_subscription_class = check_license.get(
                "license_subscription_class"
            )
            logging.debug(
                f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
            )

        except Exception as e:
            license_is_valid = 0
            license_subscription_class = None
            logging.error(f'function check_license exception="{str(e)}"')

        # check restricted components
        # Block FLX, FQM, WLK components if:
        # - license is not valid (license_is_valid != 1), OR
        # - license is valid but subscription class is "foundation" (Foundation Edition
        #   does not include restricted components)
        if self.component in (
            "splk-flx",
            "splk-wlk",
            "splk-fqm",
        ) and (
            license_is_valid != 1
            or license_subscription_class == "foundation"
        ):

            error_msg = (
                "The requested component is restricted and requires an Enterprise or Unlimited license, "
                "its execution cannot be accepted in the current licensing mode"
            )
            logging.error(error_msg)
            exceptions.append(error_msg)

            # Call the component register
            trackme_register_tenant_object_summary(
                session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                self.component,
                self.report,
                "failure",
                time.time(),
                round((time.time() - start), 3),
                error_msg,
                earliest,
                latest,
            )

            raise Exception(error_msg)

        # logging
        logging.info(
            f'tenant_id="{self.tenant_id}", component="{component_short}", Starting tracker, report="{self.report}"'
        )

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        # check schema version migration state
        try:
            schema_version = int(vtenant_component_info["schema_version"])
            schema_version_upgrade_in_progress = bool(
                int(vtenant_component_info["schema_version_upgrade_in_progress"])
            )
            logging.debug(
                f'schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"'
            )
        except Exception as e:
            schema_version = 0
            schema_version_upgrade_in_progress = False
            logging.error(
                f'failed to retrieve schema_version_upgrade_in_progress=, exception="{str(e)}"'
            )

        # Do not proceed if the schema version upgrade is in progress
        if schema_version_upgrade_in_progress:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "component": self.component,
                "response": f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, we will wait until the process is completed before proceeding, the schema upgrade is handled by the health_tracker of the tenant and is completed once the schema_version field of the Virtual Tenants KVstore (trackme_virtual_tenants) matches TrackMe\'s version, schema_version="{schema_version}", schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"',
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(json.dumps(yield_json, indent=2))
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        else:

            # retrieve the savedsearch definition
            savedsearch_definition = None
            try:
                savedsearch = self.service.saved_searches[self.report]
                savedsearch_definition = savedsearch.content["search"]
                savedsearch_content = savedsearch.content
            except Exception as e:
                savedsearch_definition = None
                savedsearch_content = {}

            # check if the search uses sampling, for splk-fqm only
            try:
                savedsearch_sample_ratio = savedsearch_content.get("dispatch.sample_ratio")
            except Exception as e:
                savedsearch_sample_ratio = None

            # raise an exception if the savedsearch definition is not found
            if not savedsearch_definition:
                raise Exception(f'tenant_id="{self.tenant_id}", component="{component_short}", report="{self.report}", savedsearch definition not found, this means that this tracker is corrupted and the wrapper was deleted, execution cannot be completed.')

            # if we have args, we will execute the report through the savedsearch command
            # otherwise execute the search directly unless force_savedsearch_execmode is True
            if self.args:
                search = f'| savedsearch "{self.report}" {self.args}'
            elif self.force_savedsearch_execmode:
                logging.info(f'tenant_id="{self.tenant_id}", component="{component_short}", report="{self.report}", force_savedsearch_execmode is True, executing the search directly through the savedsearch command')
                search = f'| savedsearch "{self.report}"'
            else:
                search = savedsearch_definition
                # if the search does not start with a generating command, which means with a |, add "search" before the search definition
                if not search.lstrip().startswith("|"):
                    search = f"search {search}"

            # init kwargs
            kwargs_search = {
                "earliest_time": earliest,
                "latest_time": latest,
                "output_mode": "json",
                "count": 0,
            }

            if savedsearch_sample_ratio:
                kwargs_search["sample_ratio"] = savedsearch_sample_ratio

            logging.debug(f'tenant_id="{self.tenant_id}", component="{component_short}", executing search=\"{search}\", kwargs_search="{json.dumps(kwargs_search, indent=2)}"')

            # this simple result counter is used to detect silent failures
            report_results_count = 0

            # the list of objects processed by the tracker
            report_objects_list = []

            # run search
            try:
                reader = run_splunk_search(
                    self.service,
                    search,
                    kwargs_search,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):

                        logging.debug(f'dict="{json.dumps(item, indent=0)}"')

                        # increment the report_results_count
                        report_results_count += 1

                        # get report_objects_list (used internally for handler events, not included in output to avoid huge records at scale)
                        report_objects_list = item.pop("report_objects_list", [])

                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{component_short}", report="{self.report}", earliest="{earliest}", latest="{latest}", status="success", run_time="{round((time.time() - start), 3)}", results="{json.dumps(item, indent=0)}"'
                        )
                        results_dict = {
                            "tenant_id": self.tenant_id,
                            "component": self.component,
                            "report": self.report,
                            "earliest": earliest,
                            "latest": latest,
                            "status": "success",
                            "run_time": round((time.time() - start), 3),
                            "results": item,
                        }
                        yield {"_time": time.time(), "_raw": results_dict}

            except Exception as e:

                # add exception to the list
                exceptions.append(str(e))

                # Call the component register
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    self.component,
                    self.report,
                    "failure",
                    time.time(),
                    round((time.time() - start), 3),
                    str(e),
                    earliest,
                    latest,
                )
                msg = f'tenant_id="{self.tenant_id}", component="{component_short}", report="{self.report}", earliest="{earliest}", latest="{latest}", main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            # Ensure to detect silent failures
            if self.alert_no_results:
                if report_results_count == 0:
                    error_msg = f'tenant_id="{self.tenant_id}", report="{self.report}", The tracker did not return any results, this likely indicates an exception during its execution, please review manually the execution of the tracker to identify the root cause'
                    logging.error(error_msg)
                    exceptions.append(error_msg)

            # handler event
            if report_objects_list:

                # if report_objects_list is a string (a single object was reported), convert it to a list
                if isinstance(report_objects_list, str):
                    report_objects_list = [report_objects_list]

                handler_events_records = []
                for object_name in report_objects_list:
                    handler_events_records.append(
                        {
                            "object": object_name,
                            "object_id": hashlib.sha256(
                                object_name.encode("utf-8")
                            ).hexdigest(),
                            "object_category": f"{self.component}",
                            "handler": self.report,
                            "handler_message": "Entity was inspected by an hybrid tracker.",
                            "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackmetrackerexecutor tenant_id={self.tenant_id} report={self.report}",
                            "handler_time": time.time(),
                        }
                    )

                # notification event
                try:
                    trackme_handler_events(
                        session_key=self._metadata.searchinfo.session_key,
                        splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                        tenant_id=self.tenant_id,
                        sourcetype="trackme:handler",
                        source=f"trackme:handler:{self.tenant_id}",
                        handler_events=handler_events_records,
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{component_short}", could not send notification event, exception="{e}"'
                    )

            # Register the component summary synchronously.
            # Must be a direct call (not a background thread) because Splunk's
            # dispatch() calls os._exit() after consuming the generator.
            self.register_component_summary(
                session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                self.component,
            )

            if detected_failure_register:
                # it is not required to update the summary record, as it is already updated, but raise the exception now
                raise Exception(
                    "TrackMe has detected a failure in the search execution, consult the component register status or the logs for more information"
                )

            else:

                if len(exceptions) > 0:
                    # Call the component register
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        self.component,
                        self.report,
                        "failure",
                        time.time(),
                        round((time.time() - start), 3),
                        "|".join(exceptions),
                        earliest,
                        latest,
                    )

                else:
                    # Call the component register
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        self.component,
                        self.report,
                        "success",
                        time.time(),
                        round((time.time() - start), 3),
                        "The report was executed successfully",
                        earliest,
                        latest,
                    )

                    # Refresh shadow copy synchronously after successful tracker execution.
                    # This MUST be a direct call, not a background thread, because
                    # Splunk's dispatch() framework terminates the process (os._exit)
                    # after consuming the generator — killing any background threads
                    # regardless of their daemon status.
                    # The actual shadow write adds ~1-4s which is negligible compared
                    # to the tracker execution time (20-35s typically).
                    self.refresh_shadow(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        self.component,
                        self.report,
                    )


dispatch(TrackMeTrackerExecutor, sys.argv, sys.stdin, sys.stdout, __name__)
