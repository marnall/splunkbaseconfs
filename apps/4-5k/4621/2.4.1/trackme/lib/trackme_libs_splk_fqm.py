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
from collections import OrderedDict
import time
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlencode
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
from trackme_libs_utils import (
    escape_backslash,
    replace_encoded_doublebackslashes,
    remove_leading_spaces,
)

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves

def trackme_fqm_gen_metrics(
    timestamp, tenant_id, object_value, object_id, metric_index, metrics_event
):
    try:
        if not isinstance(metrics_event, dict):
            metrics_event = json.loads(metrics_event)

        # Create a dedicated logger for FLX metrics
        fqm_logger = logging.getLogger("trackme.fqm.metrics")
        fqm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not fqm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_fqm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter(timestamp=timestamp)
            filehandler.setFormatter(formatter)
            fqm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            fqm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in fqm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_fqm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                fqm_logger.addHandler(filehandler)
            
            # Update formatter with current timestamp
            formatter = JSONFormatter(timestamp=timestamp)
            filehandler.setFormatter(formatter)

        fqm_logger.info(
            "Metrics - group=fqm_metrics",
            extra={
                "target_index": metric_index,
                "tenant_id": tenant_id,
                "object": object_value,
                "object_id": object_id,
                "object_category": "splk-fqm",
                "metrics_event": json.dumps(metrics_event),
            },
        )

    except Exception as e:
        raise Exception(str(e))


def trackme_fqm_gen_metrics_from_list(
    tenant_id, metric_index, metrics_list
):
    try:
        if not isinstance(metrics_list, list):
            metrics_list = json.loads(metrics_list)

        # Create a dedicated logger for FQM metrics
        fqm_logger = logging.getLogger("trackme.fqm.metrics")
        fqm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not fqm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_fqm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            fqm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            fqm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in fqm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_fqm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                fqm_logger.addHandler(filehandler)

        for metrics_item in metrics_list:
            timestamp = float(metrics_item.get("time"))
            metrics_item.pop("time")  # Remove time field

            # Update formatter with new timestamp
            formatter = JSONFormatter(timestamp=timestamp)
            filehandler.setFormatter(formatter)

            # Build metrics_event dynamically from fields starting with "fields_quality."
            metrics_event = {}
            metrics_data = metrics_item.get("metrics", {})
            for key, value in metrics_data.items():
                if key.startswith("fields_quality."):
                    metrics_event[key] = value if value is not None else 0

            fqm_logger.info(
                "Metrics - group=fqm_metrics",
                extra={
                    "target_index": metric_index,
                    "tenant_id": tenant_id,
                    "object": metrics_item.get("object"),
                    "object_id": metrics_item.get("object_id"),
                    "object_category": "splk-fqm",
                    "metrics_event": json.dumps(metrics_event),
                },
            )

    except Exception as e:
        raise Exception(str(e))


# return main searches logics for that entity
def splk_fqm_return_searches(tenant_id, fqm_type, entity_info, tenant_trackme_metric_idx="trackme_metrics"):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_fqm_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_fqm_mctalog_search = None
    splk_fqm_metrics_report = None
    splk_fqm_mpreview = None
    splk_fqm_metrics_populate_search = None
    splk_fqm_chart_values_search = None
    splk_fqm_chart_description_search = None
    splk_fqm_chart_status_search = None
    splk_fqm_table_summary_search = None
    splk_fqm_table_summary_formated_search = None
    splk_fqm_metrics_success_overtime = None
    splk_fqm_search_sample_events = None

    # metadata search constraint (set to * by default to avoid prevent results in case of no metadata fields)
    metadata_search_constraint = "*"

    # Extract metadata fields from fields_quality_summary to build search constraint
    try:
        if "fields_quality_summary" in entity_info and entity_info["fields_quality_summary"]:
            # Parse the JSON string if it's a string, otherwise use as-is if it's already a dict
            if isinstance(entity_info["fields_quality_summary"], str):
                fields_quality_data = json.loads(entity_info["fields_quality_summary"])
            else:
                fields_quality_data = entity_info["fields_quality_summary"]
            
            # Extract metadata fields and build constraint
            metadata_constraints = []
            for key, value in fields_quality_data.items():
                if key.startswith("metadata."):
                    # Format as "metadata.fieldname"="value"
                    constraint = f'"{key}"="{value}"'
                    metadata_constraints.append(constraint)
            
            # Join all constraints with spaces
            if metadata_constraints:
                metadata_search_constraint = " ".join(metadata_constraints)
                
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        get_effective_logger().warning(f"Failed to extract metadata constraints from fields_quality_summary: {str(e)}")
        pass

    try:
        ########
        # mstats
        ########

        # mcatalog
        splk_fqm_mctalog_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics, values(_dims) as dims where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-fqm" object_id="{entity_info["_key"]}" metric_name=* by index                        
            """
        )

        # metrics report
        splk_fqm_metrics_report = remove_leading_spaces(
            f"""\
                | mstats latest(_value) as latest_value, avg(_value) as avg_value, max(_value) as max_value, perc95(_value) as perc95_value, stdev(_value) as stdev_value where index="{tenant_trackme_metric_idx}" metric_name=* tenant_id="{tenant_id}" object_category="splk-fqm" object_id="{entity_info["_key"]}" by index, object, metric_name
                | foreach *_value [ eval <<FIELD>> = if(match(metric_name, "\\.status"), round('<<FIELD>>', 0), round('<<FIELD>>', 3)) ]
            """
        )

        # mpreview
        splk_fqm_mpreview = remove_leading_spaces(
            f"""\
                | mpreview index="{tenant_trackme_metric_idx}" filter="tenant_id={tenant_id} object_category="splk-fqm" object_id={entity_info["_key"]}"
            """
        )

        # metrics popuating search
        splk_fqm_metrics_populate_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-fqm" object_id="{entity_info["_key"]}" metric_name=*
                | mvexpand metrics
                | rename metrics as metric_name
                | rex field=metric_name "^trackme\\.splk\\.fqm\\.(?<label>.*)"
                | eval order=if(metric_name=="trackme.splk.fqm.status", 0, 1)
                | sort 0 order
                | fields - order
            """
        )

        # charts successes and failures
        splk_fqm_chart_values_search = remove_leading_spaces(
            f"""\
                index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                | trackmefieldsqualityextract
                | where fieldname="{entity_info.get("fieldname")}"
                | fillnull value="null" value
                | top limit=15 value
            """
        )

        # charts description
        splk_fqm_chart_description_search = remove_leading_spaces(
            f"""\
                index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                | trackmefieldsqualityextract
                | where fieldname="{entity_info.get("fieldname")}"
                | top limit=15 description
            """
        )

        # chart status
        splk_fqm_chart_status_search = remove_leading_spaces(
            f"""\
                index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                | trackmefieldsqualityextract
                | where fieldname="{entity_info.get("fieldname")}"
                | top status
            """
        )        

        # table summary
        if fqm_type == "global":
            splk_fqm_table_summary_search = remove_leading_spaces(
                f"""\
                    | inputlookup trackme_fqm_tenant_{tenant_id} where _key="{entity_info["_key"]}" | eval keyid=_key | fields fields_quality_summary *
                    | spath input=fields_quality_summary
                    | fields @fieldname, @fieldstatus, percent_success, success_fields, failed_fields, total_fields_checked, total_fields_failed, total_fields_passed, metadata.datamodel, metadata.index, metadata.sourcetype, count_total, count_success, count_failure
                    | rename "@*" as "*"
                    | foreach fieldstatus, percent_success, count* [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                    | foreach success_fields, failed_fields [ eval <<FIELD>> = mvsort(split('<<FIELD>>', ",")) ]
                """
            )
        else:
            splk_fqm_table_summary_search = remove_leading_spaces(
                f"""\
                    | inputlookup trackme_fqm_tenant_{tenant_id} where _key="{entity_info["_key"]}" | eval keyid=_key | fields fields_quality_summary *
                    | spath input=fields_quality_summary
                    | eval quality_results_description=coalesce('quality_results_description{{}}', quality_results_description)
                    | fields - "quality_results_description{{}}"
                    | fields @fieldname, recommended, @fieldstatus, percent_coverage, percent_success, metadata.index, metadata.sourcetype, count_total, count_success, count_failure, distinct_value_count, quality_results_description, field_values, regex_expression
                    | eval field_values=split(field_values, ",")
                    | rename "@*" as "*"
                    | foreach fieldstatus, percent_coverage, percent_success, count*, distinct_value_count [ eval <<FIELD>> = mvindex('<<FIELD>>', 0) ]
                """
            )

        # table summary formatted
        if fqm_type == "global":
            splk_fqm_table_summary_formated_search = remove_leading_spaces(
                f"""\
                    {splk_fqm_table_summary_search}                
                    | eval fieldstatus=if(fieldstatus=="success", fieldstatus . " 🟢", fieldstatus . " 🔴")
                    | foreach percent_success [ eval <<FIELD>> = case('<<FIELD>>'==0, 0, '<<FIELD>>'==100, 100, 1=1, '<<FIELD>>') ]
                """
            )
        else:
            splk_fqm_table_summary_formated_search = remove_leading_spaces(
                f"""\
                    {splk_fqm_table_summary_search}                
                    | lookup trackme_cim_recommended_fields field as fieldname OUTPUT is_recommended
                    | eval recommended=json_extract(w,"comment.recommended"), recommended=if(is_recommended=="true" OR match(recommended, "(?i)true|1"), "true", "false")
                    | eval fieldstatus=if(fieldstatus=="success", fieldstatus . " 🟢", fieldstatus . " 🔴"), recommended=if(recommended=="true", recommended . " ⭐", recommended)
                    | fields - is_recommended
                    | foreach percent_coverage, percent_success [ eval <<FIELD>> = case('<<FIELD>>'==0, 0, '<<FIELD>>'==100, 100, 1=1, '<<FIELD>>') ]
                """
            )            

        # metrics success overtime
        splk_fqm_metrics_success_overtime = remove_leading_spaces(
            f"""\
                | mstats min(_value) as value where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-fqm" object_id={entity_info["_key"]} metric_name=trackme.splk.fqm.fields_quality.percent_success by object, metric_name span=5m
                | rex field=metric_name "^trackme.splk.fqm.(?<metric_name>.*)"
            """
        )

        # search sample events
        if fqm_type == "global":
            splk_fqm_search_sample_events_raw = remove_leading_spaces(
                f"""\
                    index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                    | trackmefieldsqualityextract
                """
            )
        else:
            splk_fqm_search_sample_events_raw = remove_leading_spaces(
                f"""\
                    index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                    | trackmefieldsqualityextract
                    | where fieldname="{entity_info.get("fieldname")}"
                """
            )

        splk_fqm_search_sample_events = "search?q=" + urllib.parse.quote(
            replace_encoded_doublebackslashes(splk_fqm_search_sample_events_raw)
        )

        # search sample not matching regex
        if fqm_type == "global":
            splk_fqm_search_sample_not_matching_regex_events_raw = remove_leading_spaces(
                f"""\
                    index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint}| sort 0 _time
                    | trackmefieldsqualityextract
                    | where description="Field exists but value does not match the required pattern."
                    | table _time, metadata.index, metadata.sourcetype, metadata.datamodel, metadata.nodename, fieldname, value, regex_expression
                    ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                    | sort 0 _time
                    | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    | fields metadata.index, metadata.sourcetype, metadata.datamodel, metadata.nodename, fieldname, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw                    
                """
            )
        else:
            splk_fqm_search_sample_not_matching_regex_events_raw = remove_leading_spaces(
                f"""\
                    index={entity_info.get("tracker_index")} sourcetype=trackme:fields_quality source="trackme:quality:{entity_info.get("tracker_name")}" {metadata_search_constraint} | sort 0 _time
                    | trackmefieldsqualityextract
                    | where fieldname="{entity_info.get("fieldname")}"
                    | where description="Field exists but value does not match the required pattern."
                    | table _time, metadata.index, metadata.sourcetype, metadata.datamodel, metadata.nodename, fieldname, value, regex_expression
                    ``` sort is mandatory to force all records to be retrieved before we call the gen summary command ```
                    | sort 0 _time
                    | trackmefieldsqualitygensummary maxvals=15 fieldvalues_format=csv groupby_metadata_fields="metadata.datamodel,metadata.nodename,metadata.index,metadata.sourcetype,fieldname"
                    | fields metadata.index, metadata.sourcetype, metadata.datamodel, metadata.nodename, fieldname, total_events, distinct_value_count, percent_coverage, field_values, regex_expression | fields - _time, _raw                    
                """
            )

        splk_fqm_search_sample_not_matching_regex_events = "search?q=" + urllib.parse.quote(
            replace_encoded_doublebackslashes(splk_fqm_search_sample_not_matching_regex_events_raw)
        )

        response = {
            "splk_fqm_mctalog_search": f"search?q={urllib.parse.quote(splk_fqm_mctalog_search)}",
            "splk_fqm_mctalog_search_litsearch": splk_fqm_mctalog_search,
            "splk_fqm_metrics_report": f"search?q={urllib.parse.quote(splk_fqm_metrics_report)}",
            "splk_fqm_metrics_report_litsearch": splk_fqm_metrics_report,
            "splk_fqm_mpreview": f"search?q={urllib.parse.quote(splk_fqm_mpreview)}",
            "splk_fqm_mpreview_litsearch": splk_fqm_mpreview,
            "splk_fqm_metrics_populate_search": splk_fqm_metrics_populate_search,
            "splk_fqm_chart_values_search": splk_fqm_chart_values_search,
            "splk_fqm_chart_description_search": splk_fqm_chart_description_search,
            "splk_fqm_chart_status_search": splk_fqm_chart_status_search,
            "splk_fqm_table_summary_search": splk_fqm_table_summary_search,
            "splk_fqm_table_summary_formated_search": splk_fqm_table_summary_formated_search,
            "splk_fqm_metrics_success_overtime": splk_fqm_metrics_success_overtime,
            "splk_fqm_search_sample_events": splk_fqm_search_sample_events,
            "splk_fqm_search_sample_events_raw": splk_fqm_search_sample_events_raw,
            "splk_fqm_search_sample_not_matching_regex_events": splk_fqm_search_sample_not_matching_regex_events,
            "splk_fqm_search_sample_not_matching_regex_events_raw": splk_fqm_search_sample_not_matching_regex_events_raw,
            "metadata_search_constraint": metadata_search_constraint,
        }

        # return
        return response

    except Exception as e:
        get_effective_logger().error(
            f'function splk_fqm_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)
