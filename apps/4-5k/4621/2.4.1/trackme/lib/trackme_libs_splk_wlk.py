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

import os
import sys
import json
import hashlib
from collections import OrderedDict
import time
import logging
from logging.handlers import RotatingFileHandler
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import TrackMe libs
from trackme_libs import JSONFormatter

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_ingest_version(index, source, sourcetype, event):
    try:
        # Create a dedicated logger for version events
        version_logger = logging.getLogger("trackme.wlk.version")
        version_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not version_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_wlk_version.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            version_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            version_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in version_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_wlk_version.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                version_logger.addHandler(filehandler)

        version_logger.info(
            "TrackMe State Events",
            extra={
                "target_index": index,
                "target_sourcetype": sourcetype,
                "target_source": source,
                "event": event,
            },
        )

    except Exception as e:
        raise Exception(str(e))


def trackme_wlk_gen_metrics(
    tenant_id,
    overgroup,
    group,
    app,
    user,
    account,
    savedsearch_name,
    object_value,
    object_id,
    version_id,
    metric_index,
    metrics_event,
):
    try:
        # Create a dedicated logger for WLK metrics
        wlk_logger = logging.getLogger("trackme.wlk.metrics")
        wlk_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not wlk_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_wlk_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            filehandler.setFormatter(formatter)
            wlk_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            wlk_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in wlk_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_wlk_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                filehandler.setFormatter(formatter)
                wlk_logger.addHandler(filehandler)

        wlk_logger.info(
            "Metrics - group=wlk_metrics",
            extra={
                "target_index": metric_index,
                "tenant_id": tenant_id,
                "overgroup": overgroup,
                "group": group,
                "app": app,
                "user": user,
                "account": account,
                "savedsearch_name": savedsearch_name,
                "object": object_value,
                "object_id": object_id,
                "object_category": "splk-wlk",
                "version_id": version_id,
                "metrics_event": json.dumps(metrics_event),
            },
        )

    except Exception as e:
        raise Exception(str(e))


# return main searches logics for that entity
def splk_wlk_return_searches(tenant_id, entity_info, tenant_trackme_metric_idx="trackme_metrics"):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_wlk_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_wlk_mctalog_search = None
    splk_wlk_metrics_report = None
    splk_wlk_mpreview = None
    splk_wlk_metrics_populate_search = None
    splk_wlk_scheduler_skipping_search = None
    splk_wlk_scheduler_errors_search = None
    splk_wlk_scheduler_skipping_search_sample = None
    splk_wlk_scheduler_errors_search_sample = None
    splk_wlk_check_orphan = None
    splk_wlk_get_metadata = None

    # get the object_id
    object_id = hashlib.sha256(entity_info["object"].encode("utf-8")).hexdigest()
    object_name = entity_info["object"]

    try:
        ########
        # mstats
        ########

        # mcatalog
        splk_wlk_mctalog_search = f"| mcatalog values(metric_name) as metrics, values(_dims) as dims where index=\"{tenant_trackme_metric_idx}\" tenant_id=\"{tenant_id}\" object_category=\"splk-wlk\" object_id=\"{entity_info['object_id']}\" metric_name=* by index"

        # metrics report
        splk_wlk_metrics_report = remove_leading_spaces(
            f"""\
            | mstats latest(_value) as latest_value, avg(_value) as avg_value, max(_value) as max_value, perc95(_value) as perc95_value, stdev(_value) as stdev_value where index="{tenant_trackme_metric_idx}" metric_name=* tenant_id=\"{tenant_id}\" object_category=\"splk-wlk\" object_id=\"{entity_info['object_id']}\" by index, object, object_id, metric_name
            | foreach *_value [ eval <<FIELD>> = if(match(metric_name, \".status\"), round('<<FIELD>>', 0), round('<<FIELD>>', 3)) ]
            """
        )

        # mpreview
        splk_wlk_mpreview = f"| mpreview index=\"{tenant_trackme_metric_idx}\" filter=\"tenant_id={tenant_id} object_category=\"splk-wlk\" object_id=\\\"{entity_info['object_id']}\\\"\""

        # metrics popuating search
        splk_wlk_metrics_populate_search = remove_leading_spaces(
            f"""
            | mcatalog values(metric_name) as metrics where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-wlk" object_id="{entity_info["object_id"]}" metric_name=*
            | mvexpand metrics
            | rename metrics as metric_name
            | rex field=metric_name "^trackme\\.splk.wlk\\.(?<label>.*)"
            | eval order=if(metric_name=="trackme.splk.wlk.status", 0, 1)
            | sort 0 order
            | fields - order
        """
        )

        # skipping & errors searches
        scheduler_base_search = remove_leading_spaces(
            f"""\
            (index=_internal sourcetype=scheduler host=* splunk_server=*)
            | eval orig_time=_time | bucket _time span=5m
            | eval alert_actions=if((isnull(alert_actions) OR (alert_actions == "")), "none", alert_actions)
            ``` in some error cases, we need to manage extractions and status ```
            | rex field=savedsearch_id "^(?<user_alt>[^\\;]*)\\;(?<app_alt>[^\\;]*)\\;(?<savedsearch_name_alt>.*)"
            | eval user=coalesce(user, user_alt), app=coalesce(app, app_alt), savedsearch_name=coalesce(savedsearch_name, savedsearch_name_alt)
            | search savedsearch_name="{entity_info["savedsearch_name"]}"
            | eval errmsg=case(len(errmsg)>0, errmsg, match(log_level, "(?i)error") AND len(message)>0, message)
            | eval status=case(((status == "success") OR (status == "completed")),"completed",(status == "skipped"),"skipped",(status == "continued"),"deferred",len(errmsg)>0 OR status == "delegated_remote_error","error")
        """
        )

        # skipping
        splk_wlk_scheduler_skipping_search = (
            scheduler_base_search + '\n| where status="skipped"'
        )
        splk_wlk_scheduler_skipping_search_sample = (
            splk_wlk_scheduler_skipping_search + "\n| head 10"
        )

        if entity_info["account"] != "local":
            splk_wlk_scheduler_skipping_search = (
                splk_wlk_scheduler_skipping_search.replace('"', '\\"')
            )
            splk_wlk_scheduler_skipping_search = f'| splunkremotesearch account="{entity_info["account"]}" search="{splk_wlk_scheduler_skipping_search}"'
            splk_wlk_scheduler_skipping_search_sample = (
                splk_wlk_scheduler_skipping_search_sample.replace('"', '\\"')
            )
            splk_wlk_scheduler_skipping_search_sample = f'| splunkremotesearch account="{entity_info["account"]}" search="{splk_wlk_scheduler_skipping_search_sample}"'
        else:
            splk_wlk_scheduler_skipping_search_sample = f"search {splk_wlk_scheduler_skipping_search_sample}"  # explicit `search` prefix required for execution as a raw SPL

        # errors count
        splk_wlk_scheduler_errors_search = (
            scheduler_base_search + '\n| where status="error"'
        )
        splk_wlk_scheduler_errors_search_sample = (
            splk_wlk_scheduler_errors_search + "\n| head 10"
        )

        if entity_info["account"] != "local":
            splk_wlk_scheduler_errors_search = splk_wlk_scheduler_errors_search.replace(
                '"', '\\"'
            )
            splk_wlk_scheduler_errors_search = f'| splunkremotesearch account="{entity_info["account"]}" search="{splk_wlk_scheduler_errors_search}"'
            splk_wlk_scheduler_errors_search_sample = (
                splk_wlk_scheduler_errors_search_sample.replace('"', '\\"')
            )
            splk_wlk_scheduler_errors_search_sample = f'| splunkremotesearch account="{entity_info["account"]}" search="{splk_wlk_scheduler_errors_search_sample}"'
        else:
            splk_wlk_scheduler_errors_search_sample = f"search {splk_wlk_scheduler_errors_search_sample}"  # explicit `search` prefix required for execution as a raw SPL

        # orphan check
        splk_wlk_check_orphan = remove_leading_spaces(
            f"""
            | rest timeout=1800 splunk_server=local /servicesNS/-/-/saved/searches add_orphan_field=yes count=0
            | rename title as object, eai:acl.owner AS user, eai:acl.app AS app
            | fields object, user, app, orphan
            | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
            | eval object = app . ":" . user . ":" . object, key=md5(object)
            | search object="{object_name}"
            | table key, object, app, user, orphan
            """
        )

        if entity_info["account"] != "local":
            splk_wlk_check_orphan = splk_wlk_check_orphan.replace('"', '\\"')
            splk_wlk_check_orphan = f'| splunkremotesearch account="{entity_info["account"]}" search="{splk_wlk_check_orphan}"'

        # metadata
        splk_wlk_get_metadata = remove_leading_spaces(
            f"""
            | trackmesplkwlkgetreportsdefgen tenant_id="{tenant_id}" object_name="{object_name}" | sort - limit=1 _time
            | table app, owner, sharing, savedsearch_name, object cron_schedule, cron_exec_sequence_sec, disabled, is_scheduled, schedule_window, earliest_time, latest_time, description, search
            | join type=outer [ | mstats latest(_value) as value where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" earliest="-30d" latest="now" object_category="splk-wlk" object="{object_name}" metric_name=trackme.splk.wlk.count_execution by object span=5m | eval last_detected_execution=strftime(_time, "%c") | rename _time as last_time | head 1 | fields object, last_time, last_detected_execution ]
            | eval last_detected_execution=if(isnull(last_detected_execution), "No execution in the past 30 days", last_detected_execution)
            | eval last_duration_since_last_execution=if(isnull(last_detected_execution), "N/A", tostring(round(now() - last_time, 0), "duration"))
            """
        )

        # return
        return {
            "splk_wlk_mctalog_search": f"search?q={urllib.parse.quote(splk_wlk_mctalog_search)}",
            "splk_wlk_mctalog_search_litsearch": splk_wlk_mctalog_search,
            "splk_wlk_metrics_report": f"search?q={urllib.parse.quote(splk_wlk_metrics_report)}",
            "splk_wlk_metrics_report_litsearch": splk_wlk_metrics_report,
            "splk_wlk_mpreview": f"search?q={urllib.parse.quote(splk_wlk_mpreview)}",
            "splk_wlk_mpreview_litsearch": splk_wlk_mpreview,
            "splk_wlk_metrics_populate_search": splk_wlk_metrics_populate_search,
            "splk_wlk_scheduler_skipping_search": f"search?q={urllib.parse.quote(splk_wlk_scheduler_skipping_search)}",
            "splk_wlk_scheduler_skipping_search_sample": splk_wlk_scheduler_skipping_search_sample,
            "splk_wlk_scheduler_errors_search": f"search?q={urllib.parse.quote(splk_wlk_scheduler_errors_search)}",
            "splk_wlk_scheduler_errors_search_sample": splk_wlk_scheduler_errors_search_sample,
            "splk_wlk_check_orphan": splk_wlk_check_orphan,
            "splk_wlk_get_metadata": splk_wlk_get_metadata,
        }

    except Exception as e:
        get_effective_logger().error(
            f'function splk_wlk_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)
