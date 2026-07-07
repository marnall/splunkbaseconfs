#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_restricted_searches.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import re

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.restricted_searches", "trackme_rest_api_restricted_searches.log"
)

# import test handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import Splunk libs
import splunklib.client as client


# Validation helpers
_TENANT_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')
_ALERT_NAME_RE = re.compile(r'^[a-zA-Z0-9_ :.\-/\[\]()"]+$')
_SPAN_RE = re.compile(r'^(?:\d+[smhd]|auto)$')
_EARLIEST_RE = re.compile(r'^-\d+[smhdw](?:@[smhdw])?$')
_LATEST_RE = re.compile(r'^(?:now|-\d+[smhdw](?:@[smhdw])?|\+\d+[smhdw](?:@[smhdw])?)$')


def _validate_tenant_id(tenant_id):
    """Validate tenant_id is alphanumeric with underscores/hyphens only."""
    if not tenant_id or not _TENANT_ID_RE.match(str(tenant_id)):
        raise ValueError(f'Invalid tenant_id: "{tenant_id}"')
    return str(tenant_id)


def _validate_alert_name(alert_name):
    """Validate alert_name contains only safe characters."""
    if not alert_name or not _ALERT_NAME_RE.match(str(alert_name)):
        raise ValueError(f'Invalid alert_name: "{alert_name}"')
    return str(alert_name)


def _validate_span(span):
    """Validate span is a valid Splunk time span."""
    if not span:
        return '5m'
    span = str(span)
    if not _SPAN_RE.match(span):
        raise ValueError(f'Invalid span: "{span}"')
    return span


def _validate_earliest(earliest):
    """Validate earliest time is a valid relative time string."""
    if not earliest:
        return '-24h'
    earliest = str(earliest)
    if not _EARLIEST_RE.match(earliest):
        raise ValueError(f'Invalid earliest_time: "{earliest}"')
    return earliest


def _validate_latest(latest):
    """Validate latest time is a valid relative time string."""
    if not latest:
        return 'now'
    latest = str(latest)
    if not _LATEST_RE.match(latest):
        raise ValueError(f'Invalid latest_time: "{latest}"')
    return latest


def _validate_report_name(report_name):
    """Validate report/savedsearch name."""
    if not report_name or not _ALERT_NAME_RE.match(str(report_name)):
        raise ValueError(f'Invalid report_name: "{report_name}"')
    return str(report_name)


def _get_system_service(request_info):
    """Create a Splunk service using the system auth token for privileged searches."""
    return client.connect(
        owner="nobody",
        app="trackme",
        port=request_info.server_rest_port,
        token=request_info.system_authtoken,
        timeout=600,
    )


def _run_search(service, searchquery, earliest='-24h', latest='now'):
    """Run a search and return results as a list of dicts."""
    kwargs_search = {
        "app": "trackme",
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    query_results = []
    reader = run_splunk_search(
        service,
        searchquery,
        kwargs_search,
        24,
        5,
    )
    for item in reader:
        if isinstance(item, dict):
            query_results.append(item)
    return query_results


class TrackMeHandlerRestrictedSearches_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerRestrictedSearches_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_restricted_searches(self, request_info, **kwargs):
        response = {
            "resource_group_name": "restricted_searches",
            "resource_group_desc": "These endpoints proxy specific searches that require access to restricted indexes (_internal, _audit). They execute server-side with system-level privileges to ensure results are available regardless of the calling user's index access. All search templates are hardcoded — no arbitrary SPL execution is allowed.",
        }
        return {"payload": response, "status": 200}

    # ──────────────────────────────────────────────────────────
    # SCHEDULER ENDPOINTS
    # ──────────────────────────────────────────────────────────

    def get_scheduler_status(self, request_info, **kwargs):
        """
        | trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_status"

        Returns scheduler completion status per tenant and report (past 24h).
        Uses system auth token to access _internal index.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": "This endpoint retrieves the scheduler completion status for all TrackMe tenants. It uses system-level authentication to access the _internal index, ensuring results are available even when the calling user lacks _internal access. It requires a GET call.",
                "resource_desc": "Get scheduler completion status for all TrackMe tenants",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_status"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            service = _get_system_service(request_info)

            searchquery = remove_leading_spaces(
                r"""
                search (index=_internal sourcetype=scheduler app="trackme")
                | rex field=savedsearch_name "_tenant_(?<tenant_id>.*)$"
                | rex field=savedsearch_name "tenant_id:(?<tenant_id>[^\s]*)"
                | lookup trackme_virtual_tenants tenant_id OUTPUT tenant_id as found | where isnotnull(found) | fields - found
                | eval alert_actions=if((isnull(alert_actions) OR (alert_actions == "")),"none",alert_actions)
                | eval is_alert=if(alert_actions!="none", 1, 0)
                | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred")
                | search (status="completed" OR status="deferred" OR status="skipped")
                | stats count(eval(status=="completed")) as count_completed, count(eval(status=="skipped")) as count_skipped, count, max(is_alert) as is_alert by tenant_id, savedsearch_name
                | eval "pct_completed"=round(((count_completed / count) * 100),2)
                | eval status=if('pct_completed'==100, "completed", "skipped")
                | eval "pct_completed_icon"=if('pct_completed'==100, "✅", "❌")
                | rename savedsearch_name as report
                | sort 0 tenant_id, report
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery)
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def get_scheduler_completeness(self, request_info, **kwargs):
        """
        | trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_completeness"

        Returns scheduler completeness percentage (completed/skipped/deferred) for the KPI donut.
        Uses system auth token to access _internal index.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": "This endpoint retrieves the scheduler completeness percentage (completed/skipped/deferred) for TrackMe tenants. It uses system-level authentication to access the _internal index. It requires a GET call.",
                "resource_desc": "Get scheduler completeness percentage for KPI donut",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_completeness"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            service = _get_system_service(request_info)

            searchquery = remove_leading_spaces(
                r"""
                search (index=_internal sourcetype=scheduler app="trackme")
                | rex field=savedsearch_name "_tenant_(?<tenant_id>.*)$"
                | rex field=savedsearch_name "tenant_id:(?<tenant_id>[^\s]*)"
                | lookup trackme_virtual_tenants tenant_id OUTPUT tenant_id as found | where isnotnull(found) | fields - found
                | eval status=case(status=="success" OR status=="completed", "completed", status=="skipped", "skipped", status=="continued", "deferred")
                | search (status="completed" OR status="deferred" OR status="skipped") | stats count by status | sort - count | eventstats sum(count) AS total
                | eval percent=(round(((count / total) * 100),2)) | fields - total
                | fields status percent
                | eval status=upper(status)
                | eval color=case(
                    status=="COMPLETED", "#45D4BA",
                    status=="SKIPPED", "#FBC02D",
                    status=="DEFERRED", "#e85b79"
                )
                | appendpipe [ stats count | where count==0 | eval status="NO ACTIVITY YET!", percent="100.00", color="#3c444d" | fields - count ]
                """
            )

            results = _run_search(service, searchquery, earliest='-15m', latest='now')

            return {"payload": results, "status": 200}

        except Exception as e:
            response = {
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def post_scheduler_status_overtime(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/restricted_searches/scheduler_status_overtime" body='{"report": "<report_name>"}'

        Returns scheduler status timechart for a specific report.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the scheduler status overtime for a specific report. It requires a POST call with the following options:",
                "resource_desc": "Get scheduler status overtime for a specific report",
                "options": [
                    {
                        "report": "The savedsearch/report name to query scheduler status for. (required)",
                        "earliest_time": "The earliest time for the search, default: -24h (optional)",
                        "latest_time": "The latest time for the search, default: now (optional)",
                    }
                ],
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/restricted_searches/scheduler_status_overtime" body="{\\"report\\": \\"<report_name>\\"}"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            report = _validate_report_name(resp_dict.get("report"))
            earliest = _validate_earliest(resp_dict.get("earliest_time", "-24h"))
            latest = _validate_latest(resp_dict.get("latest_time", "now"))

            service = _get_system_service(request_info)

            # For hybrid trackers, the scheduler logs reference the _tracker
            # saved search, not the _wrapper. Convert accordingly.
            if "_wrapper_tenant_" in report:
                report = report.replace("_wrapper_tenant_", "_tracker_tenant_")

            # Escape double quotes in report name for SPL
            safe_report = report.replace('"', '\\"')

            searchquery = remove_leading_spaces(
                rf"""
                search (index=_internal sourcetype=scheduler app="trackme")
                | rex field=savedsearch_name "_tenant_(?<tenant_id>.*)$"
                | rex field=savedsearch_name "tenant_id:(?<tenant_id>[^\s]*)"
                | where savedsearch_name="{safe_report}"
                | eval status=case(status=="success" OR status=="completed", "completed", status=="skipped", "skipped", status=="continued", "deferred")
                | search (status="completed" OR status="deferred" OR status="skipped")
                | timechart bins=1000 minspan=30m limit=0 count by status
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery, earliest, latest)
            return {"payload": query_results, "status": 200}

        except ValueError as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 400}
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def get_scheduler_completeness_overtime(self, request_info, **kwargs):
        """
        | trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_completeness_overtime"

        Returns the global scheduler completeness overtime chart data (same as saved search trackme_scheduler_completness_overtime).
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": "This endpoint retrieves the global scheduler completeness overtime data. It uses system-level authentication to access the _internal index. It requires a GET call.",
                "resource_desc": "Get global scheduler completeness overtime",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/restricted_searches/scheduler_completeness_overtime"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            service = _get_system_service(request_info)

            searchquery = remove_leading_spaces(
                r"""
                search (index=_internal sourcetype=scheduler app="trackme")
                | rex field=savedsearch_name "_tenant_(?<tenant_id>.*)$"
                | rex field=savedsearch_name "tenant_id:(?<tenant_id>[^\s]*)"
                | lookup trackme_virtual_tenants tenant_id OUTPUT tenant_id as found | where isnotnull(found) | fields - found
                | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred")
                | search (status="completed" OR status="deferred" OR status="skipped")
                | timechart minspan=30m limit=0 count by status
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery)
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # ──────────────────────────────────────────────────────────
    # ALERT AUDIT ENDPOINTS
    # ──────────────────────────────────────────────────────────

    def post_alert_trigger_count(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_count" body='{"tenant_id": "<tenant_id>"}'

        Returns alert trigger counts by alert name for a tenant.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves alert trigger counts by alert name for a tenant. It uses system-level authentication to access the _audit index. It requires a POST call with the following options:",
                "resource_desc": "Get alert trigger counts for a tenant",
                "options": [
                    {
                        "tenant_id": "The tenant ID to query alerts for. (required)",
                    }
                ],
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_count" body="{\\"tenant_id\\": \\"<tenant_id>\\"}"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            tenant_id = _validate_tenant_id(resp_dict.get("tenant_id"))

            service = _get_system_service(request_info)

            searchquery = remove_leading_spaces(
                f"""
                search index=_audit action="alert_fired" ss_app="trackme"
                [ | inputlookup trackme_virtual_tenants where tenant_id="{tenant_id}"
                  | table tenant_alert_objects
                  | spath input=tenant_alert_objects
                  | rename "alerts{{}}" as ss_name
                  | mvexpand ss_name
                  | fields ss_name
                  | format
                  | fields search ]
                | stats count by ss_name
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery)
            return {"payload": query_results, "status": 200}

        except ValueError as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 400}
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def post_alert_trigger_overtime(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_overtime" body='{"tenant_id": "<tenant_id>"}'

        Returns alert trigger timechart for a tenant.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves alert trigger overtime data for a tenant. It uses system-level authentication to access the _audit index. It requires a POST call with the following options:",
                "resource_desc": "Get alert trigger overtime for a tenant",
                "options": [
                    {
                        "tenant_id": "The tenant ID to query alerts for. (required)",
                    }
                ],
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_overtime" body="{\\"tenant_id\\": \\"<tenant_id>\\"}"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            tenant_id = _validate_tenant_id(resp_dict.get("tenant_id"))

            service = _get_system_service(request_info)

            searchquery = remove_leading_spaces(
                f"""
                search index=_audit action="alert_fired" ss_app="trackme"
                [ | inputlookup trackme_virtual_tenants where tenant_id="{tenant_id}"
                  | table tenant_alert_objects
                  | spath input=tenant_alert_objects
                  | rename "alerts{{}}" as ss_name
                  | mvexpand ss_name
                  | fields ss_name
                  | format
                  | fields search ]
                | timechart minspan=5m bins=1000 count by ss_name
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery)
            return {"payload": query_results, "status": 200}

        except ValueError as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 400}
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def post_alert_trigger_per_alert(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_per_alert" body='{"alert_name": "<alert_name>"}'

        Returns alert trigger timechart for a specific alert.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves alert trigger overtime data for a specific alert. It uses system-level authentication to access the _audit index. It requires a POST call with the following options:",
                "resource_desc": "Get alert trigger overtime for a specific alert",
                "options": [
                    {
                        "alert_name": "The alert name (title) to query triggers for. (required)",
                        "earliest_time": "The earliest time for the search, default: -24h (optional)",
                        "latest_time": "The latest time for the search, default: now (optional)",
                        "span": "The time span for the timechart, default: 5m (optional)",
                    }
                ],
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/restricted_searches/alert_trigger_per_alert" body="{\\"alert_name\\": \\"<alert_name>\\"}"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            alert_name = _validate_alert_name(resp_dict.get("alert_name"))
            span = _validate_span(resp_dict.get("span", "5m"))
            earliest = _validate_earliest(resp_dict.get("earliest_time", "-24h"))
            latest = _validate_latest(resp_dict.get("latest_time", "now"))

            service = _get_system_service(request_info)

            # Escape double quotes in alert_name for SPL
            safe_alert_name = alert_name.replace('"', '\\"')

            searchquery = remove_leading_spaces(
                f"""
                search index=_audit action="alert_fired" ss_app="trackme" ss_name="{safe_alert_name}"
                | timechart span={span} count
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery, earliest, latest)
            return {"payload": query_results, "status": 200}

        except ValueError as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 400}
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    def post_alert_actions_overtime(self, request_info, **kwargs):
        """
        | trackme mode=post url="/services/trackme/v2/restricted_searches/alert_actions_overtime" body='{"alert_name": "<alert_name>"}'

        Returns modular alert actions timechart for a specific alert.
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves modular alert actions overtime data for a specific alert. It uses system-level authentication to access the _internal and cim_modactions indexes. It requires a POST call with the following options:",
                "resource_desc": "Get alert actions overtime for a specific alert",
                "options": [
                    {
                        "alert_name": "The alert name (title) to query actions for. (required)",
                        "earliest_time": "The earliest time for the search, default: -24h (optional)",
                        "latest_time": "The latest time for the search, default: now (optional)",
                        "span": "The time span for the timechart, default: 5m (optional)",
                    }
                ],
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/restricted_searches/alert_actions_overtime" body="{\\"alert_name\\": \\"<alert_name>\\"}"',
            }
            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            alert_name = _validate_alert_name(resp_dict.get("alert_name"))
            span = _validate_span(resp_dict.get("span", "5m"))
            earliest = _validate_earliest(resp_dict.get("earliest_time", "-24h"))
            latest = _validate_latest(resp_dict.get("latest_time", "now"))

            service = _get_system_service(request_info)

            # Escape double quotes in alert_name for SPL
            safe_alert_name = alert_name.replace('"', '\\"')

            searchquery = remove_leading_spaces(
                f"""
                search (index="_internal" OR index="cim_modactions") sourcetype="modular_alerts:*" search_name="{safe_alert_name}"
                | timechart span={span} count by sourcetype
            """
            )

            logger.debug(f'searchquery="{searchquery}"')
            query_results = _run_search(service, searchquery, earliest, latest)
            return {"payload": query_results, "status": 200}

        except ValueError as e:
            return {"payload": {"action": "failure", "response": str(e)}, "status": 400}
        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
