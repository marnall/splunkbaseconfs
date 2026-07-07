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
import re
import json
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

# import Splunk libs
import splunklib.client as client

# import trackme libs utils
from trackme_libs_utils import (
    decode_unicode,
    replace_encoded_doublebackslashes,
    replace_encoded_fourbackslashes,
    remove_leading_spaces,
    sanitize_spl_quoted_arg,
)

# import TrackMe libs
from trackme_libs import JSONFormatter

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


# process and return main entity info
def splk_dsm_return_entity_info(object_dict):
    # empty response
    response = {}

    #
    # extract the account
    #

    # check and extract
    if re.search(r"^(?:remote|remoteraw)\|", object_dict.get("object")):
        # extract the account
        match = re.search(
            r"^(?:remote|remoteraw)\|account:(\w*)\|", object_dict.get("object")
        )
        if match:
            response["account"] = match.group(1)

    # local
    else:
        response["account"] = "local"

    #
    # get and add the search_mode
    #

    response["search_mode"] = object_dict.get("search_mode")

    #
    # extract the break by statement and special key, if any
    #

    # check and extract
    if re.search(r"\|(?:key|rawkey|cribl)\:", object_dict.get("object")):
        # tstats special key
        if re.search(r"\|(?:key)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(r"\|(?:key)\:([^\|]*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # raw special key
        elif re.search(r"\|(?:rawkey)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(
                r"\|(?:rawkey)\:([^\|]*)\|(.*)", object_dict.get("object")
            )
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # cribl special key
        elif re.search(r"\|(?:cribl)\:", object_dict.get("object")):
            # extract cribl_pipe value
            match = re.search(r"\|(?:rawkey)\:[^\|*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = "cribl_pipe"
                response["breakby_value"] = match.group(1)

        # no match, fallback
        else:
            response["breakby_key"] = "none"
            response["breakby_value"] = "none"
            response["breakby_statement"] = "index, sourcetype"

    # no special key
    else:
        response["breakby_key"] = "none"
        response["breakby_value"] = "none"
        response["breakby_statement"] = "index, sourcetype"

    # return
    return response


# return if the entity is an Elastic Source, and return information
def splk_dsm_return_elastic_info(session_key, splunkd_port, tenant_id, object_value):
    # Get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=splunkd_port,
        token=session_key,
        timeout=600,
    )

    # Define the KV query
    query_string = {"object": object_value}

    # check for shared Elastic
    try:
        # Data collection
        collection_name = "kv_trackme_dsm_elastic_shared_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        shared_records = collection.data.query(query=json.dumps(query_string))
        shared_record = shared_records[0]
        shared_key = shared_record.get("_key")

        # set info
        if re.match(r"^remote_", shared_record.get("search_mode")):
            # extract account and constraint
            match = re.match(
                r"account=\\{0,1}\"{0,1}(\w+)\\{0,1}\"{0,1}\s{0,1}\|\s{0,1}(.*)",
                shared_record.get("search_constraint"),
            )
            if match:
                shared_record["account"] = match.group(1)
                shared_record["search_constraint"] = match.group(2)
        else:
            shared_record["account"] = "local"
            shared_record["search_constraint"] = shared_record.get("search_constraint")

    except Exception as e:
        shared_key = None

    # check for dedicated Elastic
    try:
        # Data collection
        collection_name = "kv_trackme_dsm_elastic_dedicated_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        dedicated_records = collection.data.query(query=json.dumps(query_string))
        dedicated_record = dedicated_records[0]
        dedicated_key = dedicated_record.get("_key")

        # set info
        if re.match(r"^remote_", dedicated_record.get("search_mode")):
            # extract account and constraint
            match = re.match(
                r"account=\\{0,1}\"{0,1}(\w+)\\{0,1}\"{0,1}\s{0,1}\|\s{0,1}(.*)",
                dedicated_record.get("search_constraint"),
            )
            if match:
                dedicated_record["account"] = match.group(1)
                dedicated_record["search_constraint"] = match.group(2)
        else:
            dedicated_record["account"] = "local"
            dedicated_record["search_constraint"] = dedicated_record.get(
                "search_constraint"
            )

    except Exception as e:
        dedicated_key = None

    # return
    if shared_key:
        # set the search_mode
        search_mode = None
        elastic_info = {}
        if shared_record.get("search_mode") in ("tstats", "remote_tstats"):
            search_mode = "tstats"
        elif shared_record.get("search_mode") in ("raw", "remote_raw"):
            search_mode = "raw"
        elif shared_record.get("search_mode") in ("from", "remote_from"):
            search_mode = "from"
        elif shared_record.get("search_mode") in ("mstats", "remote_mstats"):
            search_mode = "mstats"
        elif shared_record.get("search_mode") in ("mpreview", "remote_mpreview"):
            search_mode = "mpreview"

        elastic_info = {
            "is_elastic": 1,
            "type_elastic": "shared",
            "account": shared_record.get("account"),
            "search_mode": search_mode,
            "elastic_search_mode": shared_record.get("search_mode"),
            "search_constraint": shared_record.get("search_constraint"),
        }

        get_effective_logger().debug(
            f'function=splk_dsm_return_elastic_info, elastic_type="shared", elastic_info="{json.dumps(elastic_info, indent=2)}"'
        )
        return elastic_info

    elif dedicated_key:
        # set the search_mode
        search_mode = None
        elastic_info = {}
        if dedicated_record.get("search_mode") in ("tstats", "remote_tstats"):
            search_mode = "tstats"
        elif dedicated_record.get("search_mode") in ("raw", "remote_raw"):
            search_mode = "raw"
        elif dedicated_record.get("search_mode") in ("from", "remote_from"):
            search_mode = "from"
        elif dedicated_record.get("search_mode") in ("mstats", "remote_mstats"):
            search_mode = "mstats"
        elif dedicated_record.get("search_mode") in ("mpreview", "remote_mpreview"):
            search_mode = "mpreview"

        elastic_info = {
            "is_elastic": 1,
            "type_elastic": "dedicated",
            "account": dedicated_record.get("account"),
            "search_mode": search_mode,
            "elastic_search_mode": dedicated_record.get("search_mode"),
            "search_constraint": dedicated_record.get("search_constraint"),
        }

        get_effective_logger().debug(
            f'function=splk_dsm_return_elastic_info, elastic_type="dedicated", elastic_info="{json.dumps(elastic_info, indent=2)}"'
        )
        return elastic_info

    else:
        return {"is_elastic": 0}


# return main searches logics for that entity
def splk_dsm_return_searches(tenant_id, object_value, entity_info, tenant_trackme_metric_idx="trackme_metrics"):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_dsm_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_dsm_overview_root_search = None
    splk_dsm_overview_single_stats = None
    splk_dsm_overview_timechart = None
    splk_dsm_raw_search = None
    splk_dsm_sampling_search = None

    try:
        ########
        # tstats
        ########

        if entity_info["search_mode"] == "tstats":
            splk_dsm_overview_root_search = (
                "| tstats dc(host) as dcount_host count latest(_indextime) as indextime max(_time) as maxtime where "
                + entity_info["search_constraint"]
                + " by _time, index, sourcetype, host, splunk_server span=1s | eval ingest_latency=(indextime-_time), event_delay=(now() - maxtime)"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` sum(count) as events_count, avg(ingest_latency) as avg_latency, max(dcount_host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    replace_encoded_doublebackslashes(entity_info["search_constraint"])
                )
                splk_dsm_sampling_search = (
                    "search "
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                )
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )

        #####
        # raw
        #####

        elif entity_info["search_mode"] == "raw":
            splk_dsm_overview_root_search = (
                entity_info["search_constraint"]
                + " | eventstats max(_time) as maxtime | eval ingest_latency=(_indextime-_time), event_delay=(now() - maxtime)"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` count as events_count, avg(ingest_latency) as avg_latency, dc(host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    replace_encoded_doublebackslashes(entity_info["search_constraint"])
                )
                splk_dsm_sampling_search = (
                    "search "
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                )
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )

        ######
        # from
        ######

        # from datamodel
        elif entity_info["search_mode"] == "from" and re.search(
            r"datamodel\:\"{0,1}", entity_info["search_constraint"]
        ):
            splk_dsm_overview_root_search = (
                "| from "
                + entity_info["search_constraint"]
                + "\n| eventstats max(_time) as maxtime"
                + "\n| eval ingest_latency=(_indextime-_time), event_delay=(now() - maxtime)"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` count as events_count, avg(ingest_latency) as avg_latency, dc(host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    "| from "
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                )
                splk_dsm_sampling_search = "N/A"
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search=" from '
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"

        # from lookup
        elif entity_info["search_mode"] == "from" and re.search(
            r"lookup\:\"{0,1}", entity_info["search_constraint"]
        ):
            splk_dsm_overview_root_search = (
                '| mstats latest(_value) as value where index="'
                + tenant_trackme_metric_idx
                + '" (metric_name=trackme.splk.feeds.eventcount_4h OR metric_name=trackme.splk.feeds.lag_event_sec OR metric_name=trackme.splk.feeds.hostcount_4h) object_category="splk-dsm" object="'
                + object_value
                + '" by metric_name `auto_span` | eval {metric_name}=value'
                + "| stats first(trackme.splk.feeds.eventcount_4h) as count, first(trackme.splk.feeds.lag_event_sec) as ingest_latency, max(trackme.splk.feeds.hostcount_4h) as dcount_host by _time | eval event_delay=ingest_latency"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` latest(count) as events_count, avg(ingest_latency) as avg_latency, max(dcount_host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    "| from "
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                    + " | head 1000"
                )
                splk_dsm_sampling_search = "N/A"
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search=" from '
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"

        ########
        # mstats
        ########

        elif entity_info["search_mode"] == "mstats":
            splk_dsm_overview_root_search = (
                '| mstats latest(_value) as value where index="'
                + tenant_trackme_metric_idx
                + '" (metric_name=trackme.splk.feeds.eventcount_4h OR metric_name=trackme.splk.feeds.lag_event_sec OR metric_name=trackme.splk.feeds.hostcount_4h) object_category="splk-dsm" object="'
                + object_value
                + '" by metric_name `auto_span` | eval {metric_name}=value'
                + "| stats first(trackme.splk.feeds.eventcount_4h) as count, first(trackme.splk.feeds.lag_event_sec) as ingest_latency, max(trackme.splk.feeds.hostcount_4h) as dcount_host by _time | eval event_delay=ingest_latency"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` latest(count) as events_count, avg(ingest_latency) as avg_latency, max(dcount_host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| mpreview index=* filter=" '
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                    + '" earliest="-15m" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search=" | mpreview index=* filter=" '
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '" earliest="-15m" latest="now" | head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"

        #####
        # mpreview
        #####

        elif entity_info["search_mode"] == "mpreview":
            splk_dsm_overview_root_search = (
                entity_info["search_constraint"]
                + " | eventstats max(_time) as maxtime | eval ingest_latency=(_indextime-_time), event_delay=(now() - maxtime)"
            )

            splk_dsm_overview_single_stats = (
                splk_dsm_overview_root_search
                + " | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dsm_overview_timechart = (
                splk_dsm_overview_root_search
                + " | timechart `auto_span` count as events_count, avg(ingest_latency) as avg_latency, dc(host) as dcount_host"
            )

            if entity_info.get("account") == "local":
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    "| mpreview "
                    + replace_encoded_doublebackslashes(
                        entity_info["search_constraint"]
                    )
                    + ' earliest="-15m" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"
            else:
                splk_dsm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search=" | mpreview '
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + ' earliest="-15m" latest="now" | head 1000" earliest="-24h" latest="now"'
                )
                splk_dsm_sampling_search = "N/A"

        ###########
        # if remote
        ###########

        # for all searches except the raw event search definition

        if entity_info.get("account") != "local":
            if not (entity_info["search_mode"] in ("mstats")) and not (
                entity_info["search_mode"] in ("from")
                and re.search(r"lookup\:\"{0,1}", entity_info["search_constraint"])
            ):
                splk_dsm_overview_root_search = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dsm_overview_root_search.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                )

                splk_dsm_overview_single_stats = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dsm_overview_single_stats.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                )

                splk_dsm_overview_timechart = (
                    splk_dsm_overview_timechart + " | where isnotnull(events_count)"
                )

                splk_dsm_overview_timechart = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dsm_overview_timechart.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                    + " | timechart `auto_span` first(events_count) as events_count, first(avg_latency) as avg_latency, first(dcount_host) as dcount_host"
                )

        # metrics populating search
        splk_dsm_metrics_populate_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dsm" object="{object_value}" metric_name=*
                | mvexpand metrics
                | rename metrics as metric_name
                | rex field=metric_name "^trackme\\.splk\\.feeds\\.(?<label>.*)"
                | eval order=if(metric_name=="trackme.splk.feeds.status", 0, 1)
                | sort 0 order
                | fields - order
            """
        )

        # return
        response = {
            "splk_dsm_overview_root_search": splk_dsm_overview_root_search,
            "splk_dsm_overview_single_stats": splk_dsm_overview_single_stats,
            "splk_dsm_overview_timechart": splk_dsm_overview_timechart,
            "splk_dsm_raw_search": splk_dsm_raw_search,
            "splk_dsm_sampling_search": splk_dsm_sampling_search,
            "splk_dsm_metrics_populate_search": splk_dsm_metrics_populate_search,
        }

        get_effective_logger().debug(
            f'function=splk_dsm_return_searches, response="{json.dumps(response, indent=2)}"'
        )
        return response

    except Exception as e:
        get_effective_logger().error(
            f'function=splk_dsm_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)


# process and return main entity info
def splk_dhm_return_entity_info(object_dict):
    # empty response
    response = {}

    #
    # extract the account
    #

    # check and extract
    if re.search(r"^(?:remote|remoteraw)\|", object_dict.get("object")):
        # extract the account
        match = re.search(
            r"^(?:remote|remoteraw)\|account:(\w*)\|", object_dict.get("object")
        )
        if match:
            response["account"] = match.group(1)

    # local
    else:
        response["account"] = "local"

    #
    # get and add the search_mode
    #

    response["search_mode"] = object_dict.get("search_mode")

    #
    # extract the break by statement and special key, if any
    #

    # check and extract
    if re.search(r"(?:key)\:", object_dict.get("object")):
        # tstats special key
        if re.search(r"(?:key)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(r"(?:key)\:([^\|]*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # raw special key
        elif re.search(r"(?:rawkey)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(r"(?:rawkey)\:([^\|]*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # no match, fallback
        else:
            response["breakby_key"] = "none"
            response["breakby_value"] = "none"
            response["breakby_statement"] = "index, sourcetype"

    # no special key
    else:
        response["breakby_key"] = "none"
        response["breakby_value"] = "none"
        response["breakby_statement"] = "index, sourcetype"

    # return
    return response


# return main searches logics for that entity
def splk_dhm_return_searches(tenant_id, object_value, entity_info, tenant_trackme_metric_idx="trackme_metrics"):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_dhm_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_dhm_overview_root_search = None
    splk_dhm_overview_timechart = None
    splk_dhm_overview_pie_root_search = None
    splk_dhm_raw_search = None

    try:
        ########
        # tstats
        ########

        if entity_info["search_mode"] == "tstats":
            splk_dhm_overview_root_search = (
                "| tstats count, max(_indextime) as indextime, max(_time) as maxtime where "
                + replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " by _time, index, sourcetype, splunk_server span=1s | eval ingest_latency=(indextime-_time), event_delay=(now() - maxtime) | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dhm_overview_timechart = (
                "| tstats count, max(_indextime) as indextime, max(_time) as maxtime where "
                + replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " by _time, index, sourcetype, splunk_server span=1s | eval ingest_latency=(indextime-_time), event_delay=(now() - maxtime) | timechart `auto_span` sum(count) as events_count, avg(ingest_latency) as avg_latency"
            )

            splk_dhm_overview_pie_root_search = (
                "| tstats count where "
                + replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " by index, sourcetype"
            )

            if entity_info.get("account") == "local":
                splk_dhm_raw_search = "search?q=" + urllib.parse.quote(
                    replace_encoded_doublebackslashes(entity_info["search_constraint"])
                )
            else:
                splk_dhm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )

        #####
        # raw
        #####

        elif entity_info["search_mode"] == "raw":
            splk_dhm_overview_root_search = (
                replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " | eventstats max(_time) as maxtime | eval ingest_latency=(_indextime-_time), event_delay=now()-maxtime | stats perc95(ingest_latency) as perc95_latency, avg(ingest_latency) as avg_latency, latest(event_delay) as event_delay"
            )

            splk_dhm_overview_timechart = (
                replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " | eventstats max(_time) as maxtime | eval ingest_latency=(_indextime-_time), event_delay=now()-maxtime | timechart `auto_span` count as events_count, avg(ingest_latency) as avg_latency"
            )

            splk_dhm_overview_pie_root_search = (
                replace_encoded_doublebackslashes(entity_info["search_constraint"])
                + " | stats count by index, sourcetype"
            )

            if entity_info.get("account") == "local":
                splk_dhm_raw_search = "search?q=" + urllib.parse.quote(
                    replace_encoded_doublebackslashes(entity_info["search_constraint"])
                )
            else:
                splk_dhm_raw_search = "search?q=" + urllib.parse.quote(
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + replace_encoded_fourbackslashes(
                        entity_info["search_constraint"]
                    ).replace('"', '\\"')
                    + '| head 1000" earliest="-24h" latest="now"'
                )

        ###########
        # if remote
        ###########

        # for all searches except the raw event search definition

        if entity_info.get("account") != "local":
            if not entity_info["search_mode"] in ("from", "mstats"):
                splk_dhm_overview_root_search = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dhm_overview_root_search.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                )

                splk_dhm_overview_timechart = (
                    splk_dhm_overview_timechart + " | where isnotnull(events_count)"
                )

                splk_dhm_overview_timechart = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dhm_overview_timechart.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                    + " | timechart `auto_span` first(events_count) as events_count, first(avg_latency) as avg_latency"
                )

                splk_dhm_overview_pie_root_search = (
                    '| splunkremotesearch account="'
                    + entity_info.get("account")
                    + '" search="'
                    + splk_dhm_overview_pie_root_search.replace('"', '\\"')
                    + '" earliest="-24h" latest="now"'
                )

        # metrics populating search
        splk_dhm_metrics_populate_search = remove_leading_spaces(
            f"""\
                | mcatalog values(metric_name) as metrics where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-dhm" object="{object_value}" metric_name=*
                | mvexpand metrics
                | rename metrics as metric_name
                | rex field=metric_name "^trackme\\.splk\\.feeds\\.(?<label>.*)"
                | eval order=if(metric_name=="trackme.splk.feeds.status", 0, 1)
                | sort 0 order
                | fields - order
            """
        )

        # return
        return {
            "splk_dhm_overview_root_search": splk_dhm_overview_root_search,
            "splk_dhm_overview_timechart": splk_dhm_overview_timechart,
            "splk_dhm_overview_pie_root_search": splk_dhm_overview_pie_root_search,
            "splk_dhm_raw_search": splk_dhm_raw_search,
            "splk_dhm_metrics_populate_search": splk_dhm_metrics_populate_search,
        }

    except Exception as e:
        get_effective_logger().error(
            f'function splk_dhm_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)


# process and return main entity info
def splk_mhm_return_entity_info(object_dict):
    # empty response
    response = {}

    #
    # extract the account
    #

    # check and extract
    if re.search(r"^(?:remote|remoteraw)\|", object_dict.get("object")):
        # extract the account
        match = re.search(
            r"^(?:remote|remoteraw)\|account:(\w*)\|", object_dict.get("object")
        )
        if match:
            response["account"] = match.group(1)

    # local
    else:
        response["account"] = "local"

    #
    # get and add the search_mode
    #

    response["search_mode"] = "mstats"

    #
    # extract the break by statement and special key, if any
    #

    # check and extract
    if re.search(r"(?:key)\:", object_dict.get("object")):
        # tstats special key
        if re.search(r"(?:key)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(r"(?:key)\:([^\|]*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # raw special key
        elif re.search(r"(?:rawkey)\:", object_dict.get("object")):
            # extract key and value
            match = re.search(r"(?:rawkey)\:([^\|]*)\|(.*)", object_dict.get("object"))
            if match:
                response["breakby_key"] = match.group(1)
                response["breakby_value"] = match.group(2)

        # no match, fallback
        else:
            response["breakby_key"] = "none"
            response["breakby_value"] = "none"
            response["breakby_statement"] = "index, sourcetype"

    # no special key
    else:
        response["breakby_key"] = "none"
        response["breakby_value"] = "none"
        response["breakby_statement"] = "index, sourcetype"

    # return
    return response


# return main searches logics for that entity
def splk_mhm_return_searches(tenant_id, object_value, entity_info):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_mhm_return_searches with entity_info="{json.dumps(entity_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    splk_mhm_mctalog_search = None
    splk_mhn_metrics_report = None
    splk_mhn_mpreview = None

    try:
        ########
        # mstats
        ########

        # get the breakby_key
        breakby_key = entity_info["breakby_key"]
        if breakby_key == "none":
            breakby_key = "host"

        # mcatalog
        splk_mhm_mctalog_search = (
            "| mcatalog values(metric_name) as metrics, values(_dims) as dims where metric_name=* "
            + replace_encoded_doublebackslashes(entity_info["search_constraint"])
            + " by index"
        )

        if entity_info.get("account") == "local":
            splk_mhm_mctalog_search = "search?q=" + urllib.parse.quote(
                splk_mhm_mctalog_search
            )
        else:
            splk_mhm_mctalog_search = "search?q=" + urllib.parse.quote(
                '| splunkremotesearch account="'
                + entity_info.get("account")
                + '" search="'
                + splk_mhm_mctalog_search.replace('"', '\\"')
                + '| head 1000" earliest="-24h" latest="now"'
            )

        # metrics report
        splk_mhn_metrics_report = (
            "| mstats latest(_value) as value where metric_name=* "
            + replace_encoded_doublebackslashes(entity_info["search_constraint"])
            + " by metric_name, index, "
            + breakby_key
            + " span=1m"
            + " | stats max(_time) as _time by metric_name, index, "
            + breakby_key
            + r' | rex field=metric_name "(?<metric_category>[^\.]*)\.{0,1}"'
            + " | stats values(metric_name) as metric_name, max(_time) as _time by metric_category, index, "
            + breakby_key
            + " | eval metric_current_lag_sec=(now() - _time)"
        )

        if entity_info.get("account") == "local":
            splk_mhn_metrics_report = "search?q=" + urllib.parse.quote(
                splk_mhn_metrics_report
            )
        else:
            splk_mhn_metrics_report = "search?q=" + urllib.parse.quote(
                '| splunkremotesearch account="'
                + entity_info.get("account")
                + '" search="'
                + splk_mhn_metrics_report.replace('"', '\\"')
                + '" earliest="-24h" latest="now"'
            )

        # mpreview
        if entity_info["search_constraint"] != "none":
            splk_mhn_mpreview = (
                '| mpreview index=* filter="'
                + entity_info["breakby_key"]
                + "="
                + entity_info["breakby_value"]
                + '"'
            )
        else:
            splk_mhn_mpreview = (
                '| mpreview index=* filter="host=' + entity_info["breakby_value"] + '"'
            )

        if entity_info.get("account") == "local":
            splk_mhn_mpreview = "search?q=" + urllib.parse.quote(splk_mhn_mpreview)
        else:
            splk_mhn_mpreview = "search?q=" + urllib.parse.quote(
                '| splunkremotesearch account="'
                + entity_info.get("account")
                + '" search="'
                + splk_mhn_mpreview.replace('"', '\\"')
                + '" earliest="-15m" latest="now"'
            )

        # return
        return {
            "splk_mhm_mctalog_search": splk_mhm_mctalog_search,
            "splk_mhm_mctalog_search_litsearch": urllib.parse.unquote(
                splk_mhm_mctalog_search.replace("search?q=", "")
            ),
            "splk_mhn_metrics_report": splk_mhn_metrics_report,
            "splk_mhn_metrics_report_litsearch": urllib.parse.unquote(
                splk_mhn_metrics_report.replace("search?q=", "")
            ),
            "splk_mhn_mpreview": splk_mhn_mpreview,
            "splk_mhn_mpreview_litsearch": urllib.parse.unquote(
                splk_mhn_mpreview.replace("search?q=", "")
            ),
        }

    except Exception as e:
        get_effective_logger().error(
            f'function splk_mhm_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)


# return simulation search for splk-dsm hybrid trackers
def splk_dsm_hybrid_tracker_simulation_return_searches(simulation_info):
    # log debug
    get_effective_logger().debug(
        f'Starting function=splk_dsm_hybrid_tracker_simulation_return_searches with simulation_info="{json.dumps(simulation_info, indent=2)}"'
    )

    # define required searches dynamically based on the upstream entity information
    tracker_simulation_search = None

    try:
        ####################
        # component splk-dsm
        ####################

        if simulation_info["component"] in ("dsm"):

            # breakby statement
            breakby_statement = None
            breakby_field_include_sourcetype = simulation_info.get(
                "breakby_field_include_sourcetype", True
            )

            if simulation_info["breakby_field"] in ("none", "split"):
                breakby_statement = "index, sourcetype"
            elif simulation_info["breakby_field"] in ("merged"):
                breakby_statement = "index"
            else:
                if not breakby_field_include_sourcetype:
                    breakby_statement = "index, " + simulation_info["breakby_field"]
                else:
                    breakby_statement = (
                        "index, sourcetype, " + simulation_info["breakby_field"]
                    )

            # object definition statement
            object_definition = None
            if simulation_info["breakby_field"] in ("none", "split"):
                object_definition = 'data_index . ":" . data_sourcetype'
            elif simulation_info["breakby_field"] in ("merged"):
                object_definition = 'data_index . ":" . "@all"'
            else:
                # support multiple fields
                break_by_field = simulation_info["breakby_field"].split(",")

                if len(break_by_field) == 1:

                    # sourcetype to any with a custom breakby
                    if not breakby_field_include_sourcetype:
                        object_definition = (
                            'data_index . ":" . "any" . "|key:" . "'
                            + simulation_info["breakby_field"]
                            + '" . "|" . '
                            + simulation_info["breakby_field"]
                        )

                    # otherwise
                    else:
                        object_definition = (
                            'data_index . ":" . data_sourcetype . "|key:" . "'
                            + simulation_info["breakby_field"]
                            + '" . "|" . '
                            + simulation_info["breakby_field"]
                        )

                else:

                    # sourcetype to any with a custom breakby
                    if not breakby_field_include_sourcetype:
                        object_definition = (
                            'data_index . ":" . "any" . "|key:" . "'
                            + simulation_info["breakby_field"].replace(",", ";")
                            + '" . "|"'
                        )

                    # otherwise
                    else:
                        object_definition = (
                            'data_index . ":" . data_sourcetype . "|key:" . "'
                            + simulation_info["breakby_field"].replace(",", ";")
                            + '" . "|"'
                        )

                    append_count = 0
                    for subbreak_by_field in break_by_field:
                        if append_count == 0:
                            object_definition = (
                                object_definition + " . " + subbreak_by_field
                            )
                        else:
                            object_definition = (
                                object_definition
                                + " . "
                                + '";"'
                                + " . "
                                + subbreak_by_field
                            )
                        append_count += 1

            # depends on account
            if simulation_info["account"] != "local":
                object_definition = (
                    "object = "
                    + '"remote|account:'
                    + simulation_info["account"]
                    + '|" . '
                    + object_definition
                )
            else:
                object_definition = "object = " + object_definition

            ########
            # tstats
            ########

            if simulation_info["search_mode"] == "tstats":
                get_effective_logger().info("Processing with search_mode=tstats")
                tracker_simulation_search = (
                    "| tstats count, dc(host) as dcount_host where (index=* OR index=_*) "
                    + simulation_info["search_constraint"]
                    + " _index_earliest="
                    + simulation_info["index_earliest_time"]
                    + " _index_latest="
                    + simulation_info["index_latest_time"]
                    + " by "
                    + breakby_statement
                    + "\n| rename index as data_index, sourcetype as data_sourcetype"
                    + "\n| eval "
                    + object_definition
                    + "\n| stats values(data_index) as indexes, dc(object) as dcount_entities, values(object) as entities"
                    + "\n| mvexpand entities | head 100 | stats values(indexes) as indexes, first(dcount_entities) as dcount_entities, values(entities) as entities_sample\n"
                )

            ########
            # raw
            ########

            elif simulation_info["search_mode"] == "raw":
                get_effective_logger().info("Processing with search_mode=raw")
                tracker_simulation_search = (
                    "(index=* OR index=_*) "
                    + simulation_info["search_constraint"]
                    + " _index_earliest="
                    + simulation_info["index_earliest_time"]
                    + " _index_latest="
                    + simulation_info["index_latest_time"]
                    + "\n| stats count, dc(host) as dcount_host by "
                    + breakby_statement
                    + "\n| rename index as data_index, sourcetype as data_sourcetype"
                    + "\n| eval "
                    + object_definition
                    + "\n| stats values(data_index) as indexes, dc(object) as dcount_entities, values(object) as entities"
                    + "\n| mvexpand entities | head 100 | stats values(indexes) as indexes, first(dcount_entities) as dcount_entities, values(entities) as entities_sample\n"
                )

        ####################
        # component splk-dhm
        ####################

        elif simulation_info["component"] in ("dhm"):
            # breakby statement
            breakby_statement = None
            dhm_breakby_field = simulation_info["breakby_field"]
            dhm_is_merged = dhm_breakby_field == "merged"
            # Extras: optional list of additional per-host metadata
            # dimensions appended to the combo grain. Mutually exclusive
            # with merged mode. Filter falsy / empty entries.
            dhm_raw_extras = simulation_info.get("breakby_extra_fields") or []
            if isinstance(dhm_raw_extras, str):
                dhm_raw_extras = [
                    x.strip() for x in dhm_raw_extras.split(",") if x.strip()
                ]
            dhm_extras = (
                []
                if dhm_is_merged
                else [str(f).strip() for f in dhm_raw_extras if f and str(f).strip()]
            )
            extras_suffix = (", " + ", ".join(dhm_extras)) if dhm_extras else ""
            if dhm_breakby_field in ("host", "none"):
                breakby_statement = "index, sourcetype, host" + extras_suffix
            elif dhm_is_merged:
                # In merged mode, drop sourcetype from the root tstats split-by;
                # the entity is still keyed by host, sourcetype is treated as @all.
                breakby_statement = "index, host"
            else:
                breakby_statement = (
                    "index, sourcetype, " + dhm_breakby_field + extras_suffix
                )

            # object definition statement
            # In merged mode the entity is still keyed by host (DHM is host-centric),
            # only the per-sourcetype dimension is collapsed.
            object_definition = None
            if dhm_breakby_field in ("host", "none") or dhm_is_merged:
                object_definition = "host"
            else:
                object_definition = dhm_breakby_field

            # depends on account
            if simulation_info["account"] != "local":
                object_definition = (
                    "object = "
                    + '"remote|account:'
                    + simulation_info["account"]
                    + '|" . '
                    + object_definition
                )
            else:
                object_definition = "object = " + object_definition

            ########
            # tstats
            ########

            if simulation_info["search_mode"] == "tstats":
                get_effective_logger().info("Processing with search_mode=tstats")
                tracker_simulation_search = (
                    '| tstats count, dc(host) as dcount_host where (index=* OR index=_*) (host=* host!="") '
                    + simulation_info["search_constraint"]
                    + " _index_earliest="
                    + simulation_info["index_earliest_time"]
                    + " _index_latest="
                    + simulation_info["index_latest_time"]
                    + " by "
                    + breakby_statement
                    + "\n| rename index as data_index, sourcetype as data_sourcetype"
                    + "\n| eval "
                    + object_definition
                    + "\n| stats values(data_index) as indexes, dc(object) as dcount_entities, values(object) as entities"
                    + "\n| mvexpand entities | head 100 | stats values(indexes) as indexes, first(dcount_entities) as dcount_entities, values(entities) as entities_sample\n"
                )

            ########
            # raw
            ########

            elif simulation_info["search_mode"] == "raw":
                get_effective_logger().info("Processing with search_mode=raw")
                tracker_simulation_search = (
                    '(index=* OR index=_*) (host=* host!="") '
                    + simulation_info["search_constraint"]
                    + " _index_earliest="
                    + simulation_info["index_earliest_time"]
                    + " _index_latest="
                    + simulation_info["index_latest_time"]
                    + "\n| stats count, dc(host) as dcount_host by "
                    + breakby_statement
                    + "\n| rename index as data_index, sourcetype as data_sourcetype"
                    + "\n| eval "
                    + object_definition
                    + "\n| stats values(data_index) as indexes, dc(object) as dcount_entities, values(object) as entities"
                    + "\n| mvexpand entities | head 100 | stats values(indexes) as indexes, first(dcount_entities) as dcount_entities, values(entities) as entities_sample\n"
                )

        ####################
        # component splk-mhm
        ####################

        elif simulation_info["component"] in ("mhm"):
            # breakby statement
            breakby_statement = None
            if simulation_info["breakby_field"] in ("host", "none"):
                breakby_statement = "index, metric_name, host"
            else:
                breakby_statement = (
                    "index, metric_name, " + simulation_info["breakby_field"]
                )

            # object definition statement
            object_definition = None
            if simulation_info["breakby_field"] in ("host", "none"):
                object_definition = "host"
            else:
                object_definition = simulation_info["breakby_field"]

            # depends on account
            if simulation_info["account"] != "local":
                object_definition = (
                    "object = "
                    + '"remote|account:'
                    + simulation_info["account"]
                    + '|" . '
                    + object_definition
                )
            else:
                object_definition = "object = " + object_definition

            ########
            # mstats
            ########

            # splk-mhm only supports mstats
            get_effective_logger().info("Processing with search_mode=mstats")
            tracker_simulation_search = (
                "| mstats latest(_value) as value where (index=* OR index=_*) (metric_name=*) "
                + simulation_info["search_constraint"]
                + " by "
                + breakby_statement
                + "\n| rename index as metric_index"
                + "\n| eval "
                + object_definition
                + "\n| stats values(metric_index) as indexes, dc(object) as dcount_entities, values(object) as entities"
                + "\n| mvexpand entities | head 100 | stats values(indexes) as indexes, first(dcount_entities) as dcount_entities, values(entities) as entities_sample\n"
            )

        ###########
        # if remote
        ###########

        # for all searches except the raw event search definition

        if simulation_info.get("account") != "local":
            tracker_simulation_search = (
                '| splunkremotesearch account="'
                + simulation_info.get("account")
                + '" search="'
                + tracker_simulation_search.replace('"', '\\"')
                + '" earliest="'
                + simulation_info.get("earliest_time")
                + '" latest="'
                + simulation_info.get("latest_time")
                + '" | fields - _raw'
            )

        # log debug
        get_effective_logger().debug(f'tracker_simulation_search="{tracker_simulation_search}"')

        # return
        return {
            "tracker_simulation_search": tracker_simulation_search,
        }

    except Exception as e:
        get_effective_logger().error(
            f'function splk_dsm_hybrid_tracker_simulation_return_searches, an exception was encountered, exception="{str(e)}"'
        )
        raise Exception(e)


def _build_dhm_extras_eval_fragments(effective_extras):
    """Build the SPL eval fragments that emit `_trackme_combo_extras_str`
    for extras-aware DHM trackers.

    The trackme_dhm_tracker_abstract macro picks up
    `_trackme_combo_extras_str` via coalesce() and folds it into both
    the combo_id sha256 input AND the per-combo `current_summary`
    (the latter is a single-quoted pseudo-JSON literal that
    ast.literal_eval parses downstream in trackmedhmpipeline.py).

    Returns: (local_fragment, remote_fragment). Empty extras → ("", "")
    so callers can splice unconditionally without affecting legacy
    trackers — guarantees byte-identical SPL when no extras are set.

    Encoding scheme — applied to each *value* (field names are
    validated to a strict identifier upstream, so they're safe to
    embed unencoded):
      "%"  → "%25" first so subsequent encodings don't double-escape
      "\\" → "%5C" so a value containing a backslash (e.g. a Windows
             path like `C:\\Users\\app.log`) can't break the
             single-quoted dict literal that current_summary uses —
             `\\U`, `\\n`, `\\t` are all Python escape triggers that
             would crash or corrupt ast.literal_eval downstream
      "'"  → "%27" so a value containing a single quote (e.g. a path
             like `/var/log/O'Brien/app.log`) can't close the
             single-quoted dict literal
      "|"  → "%7C" so the pair-delimiter is unambiguous (Splunk source
             paths can contain `|` for tail-style log pipes)
      "="  → "%3D" so the key=value separator is unambiguous (free-form
             values can contain `=`)

    The pipeline's _unquote_extras_value() reverses this in matching
    order so a value round-trips intact. Centralizing here keeps both
    the lib and the REST handler from drifting (the handler imports
    and calls this same function).

    The remote fragment is derived from the local one via a single
    envelope-escape pass (each `\\` → `\\\\`, each `"` → `\\"`) so any
    future encoding tweak only needs one edit.
    """
    if not effective_extras:
        return "", ""
    # Build the inner SPL replace-chain per extras field. Escape
    # hierarchy for the backslash regex:
    #   1. PCRE regex pattern for a literal `\` is `\\` (2 chars)
    #   2. SPL string syntax escapes backslash with backslash, so the
    #      SPL source must be `"\\\\"` (4 chars between quotes) to hold
    #      the 2-char string content `\\`
    #   3. Python source escapes backslash with backslash, so the
    #      Python literal needs 8 backslashes (`"\\\\\\\\"`) to produce
    #      the 4-backslash SPL string source
    # `[|]` is a regex character class for one literal `|` (avoids
    # alternation); `'`, `=` are plain regex literals.
    inner_tpl = (
        'replace('
        'replace('
        'replace('
        'replace('
        'replace('
        '{f}, "%", "%25"),'
        ' "\\\\\\\\", "%5C"),'
        ' "\'", "%27"),'
        ' "[|]", "%7C"),'
        ' "=", "%3D")'
    )
    parts_local = [
        '"{f}=" . coalesce({inner}, "")'.format(
            f=f, inner=inner_tpl.format(f=f)
        )
        for f in effective_extras
    ]
    local_fragment = (
        '\n``` extras combo grain ```\n| eval _trackme_combo_extras_str = '
        + ' . "|" . '.join(parts_local)
    )
    # Remote variant — embedded inside splunkremotesearch's
    # `search="..."` argument, so every `\` becomes `\\` and every `"`
    # becomes `\"` (in that order — escape backslashes first so the
    # quote-escape's introduced backslashes aren't doubled). The
    # comment header has no `\` or `"` so it survives unchanged.
    remote_fragment = local_fragment.replace("\\", "\\\\").replace('"', '\\"')
    return local_fragment, remote_fragment


def generate_dhm_report_search(
    entity_info,
    search_mode,
    tenant_id,
    account,
    index_earliest_time,
    index_latest_time,
    earliest_time,
    latest_time,
    root_constraint,
    dhm_tstats_root_breakby_include_splunk_server,
    dhm_tstats_root_time_span,
    breakby_field,
    breakby_extra_fields=None,
):
    #
    # breaby statement
    #

    # set breakby_field if none
    if breakby_field == "none":
        breakby_field = None

    # merged mode: drop sourcetype from the tstats root split-by and treat
    # sourcetype as "@all" downstream. Entity is still keyed by host
    # (DHM is host-centric); only the per-sourcetype dimension is collapsed.
    is_merged = breakby_field == "merged"

    # Extras: additional per-host metadata dimensions appended to the
    # combo grain (on top of index, sourcetype). Mutually exclusive with
    # merged mode by design. breakby_field stays a single field name —
    # extras are a structurally separate list. Filter out empty / falsy
    # values so an empty-string entry never reaches the SPL.
    if is_merged or not breakby_extra_fields:
        effective_extras = []
    else:
        effective_extras = [str(f).strip() for f in breakby_extra_fields if f and str(f).strip()]

    #
    # define trackme_root_splitby and trackme_aggreg_splitby
    #

    breakby_field_list = ["index", "sourcetype", "splunk_server"]
    if breakby_field and not is_merged:
        # breakby_field is a single field name (host identifier) — no CSV split.
        if breakby_field not in breakby_field_list:
            breakby_field_list.append(breakby_field)
        # set meta
        trackme_dhm_host_meta = str(breakby_field)
    else:
        breakby_field_list.append("host")
        # set meta (entity keyed by host in both standard and merged modes)
        trackme_dhm_host_meta = "host"

    # Append extras after the host identifier — they enter both the root
    # tstats split-by and the aggreg split-by, extending the per-host
    # combo grain.
    for f in effective_extras:
        if f not in breakby_field_list:
            breakby_field_list.append(f)

    # translates into a csv list while handling few more options
    trackme_root_splitby = []
    for field in breakby_field_list:
        if field == "index":
            trackme_root_splitby.append(field)
        elif field == "sourcetype":
            # In merged mode, drop sourcetype from the tstats root split-by;
            # `eval sourcetype="@all"` is injected after the root tstats below.
            if not is_merged:
                trackme_root_splitby.append(field)
        elif field == "splunk_server":
            if dhm_tstats_root_breakby_include_splunk_server:
                trackme_root_splitby.append(field)
        else:
            trackme_root_splitby.append(field)

    # return as csv list
    trackme_root_splitby = ",".join(trackme_root_splitby)

    # aggreg split by (required for tstats searches)
    # In merged mode, sourcetype is kept here because it is set to "@all"
    # immediately after the root tstats so the aggregation rolls up per index.
    trackme_aggreg_splitby_list = ["index", "sourcetype"]
    if breakby_field and not is_merged:
        if breakby_field not in trackme_aggreg_splitby_list:
            trackme_aggreg_splitby_list.append(breakby_field)
    else:
        trackme_aggreg_splitby_list.append("host")

    for f in effective_extras:
        if f not in trackme_aggreg_splitby_list:
            trackme_aggreg_splitby_list.append(f)

    # translates into a csv list
    trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

    # SPL fragment that collapses sourcetype to "@all" in merged mode,
    # injected between the tstats root and the bucket span step.
    merged_sourcetype_eval_local = (
        '\n``` merged mode ```\n| eval sourcetype="@all"' if is_merged else ""
    )
    # Same fragment but for remote (splunkremotesearch) — quotes are
    # escaped because the string is embedded inside a `search="..."`.
    merged_sourcetype_eval_remote = (
        '\n``` merged mode ```\n| eval sourcetype=\\"@all\\"' if is_merged else ""
    )

    # SPL fragment that builds _trackme_combo_extras_str — picked up by
    # the trackme_dhm_tracker_abstract macro to extend combo_id beyond
    # (index, sourcetype). See _build_dhm_extras_eval_fragments() for
    # the encoding contract.
    extras_eval_local, extras_eval_remote = _build_dhm_extras_eval_fragments(
        effective_extras
    )

    # "none" tstats root time span — drop _time and span= from the root
    # tstats by-clause and inject `eval _time=now()` so the rest of the
    # pipeline still has a single (synthetic) time bucket. Trades per-bucket
    # latency accuracy for substantially cheaper root tstats execution.
    is_no_span = str(dhm_tstats_root_time_span).lower() == "none"
    if is_no_span:
        # No _time, no span=...
        root_by_clause_local = " by " + str(trackme_root_splitby)
        root_by_clause_remote = " by " + str(trackme_root_splitby)
    else:
        root_by_clause_local = (
            " by _time,"
            + str(trackme_root_splitby)
            + " span="
            + str(dhm_tstats_root_time_span)
        )
        root_by_clause_remote = root_by_clause_local
    no_span_eval = (
        '\n``` no tstats time span ```\n| eval _time=now()' if is_no_span else ""
    )

    # set tracker_type
    if account == "local":
        tracker_type = "local"
    else:
        tracker_type = "remote"

    #
    # define search string aggreg
    #

    if tracker_type == "local":
        search_string_aggreg = (
            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
            + "sum(data_eventcount) as data_eventcount by "
            + str(trackme_aggreg_splitby)
            + "\n"
            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
            + ' | eval host="key:'
            + str(trackme_dhm_host_meta)
            + '|" . '
            + str(trackme_dhm_host_meta)
        )

    elif tracker_type == "remote":
        if search_mode in "tstats":
            search_string_aggreg = (
                "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                + "sum(data_eventcount) as data_eventcount by "
                + str(trackme_aggreg_splitby)
                + "\n"
                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                + ' | eval host=\\"remote|account:'
                + str(account.replace('"', ""))
                + "|key:"
                + str(trackme_dhm_host_meta)
                + '|\\" . '
                + str(trackme_dhm_host_meta)
            )

        elif search_mode in "raw":
            search_string_aggreg = (
                "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                + "sum(data_eventcount) as data_eventcount by "
                + str(trackme_aggreg_splitby)
                + "\n"
                + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                + ' | eval host=\\"remoteraw|account:'
                + str(account.replace('"', ""))
                + "|key:"
                + str(trackme_dhm_host_meta)
                + '|\\" . '
                + str(trackme_dhm_host_meta)
            )

    # report search
    if tracker_type == "local":
        if search_mode in "tstats":
            report_search = (
                "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + 'count as data_eventcount, dc(host) as dcount_host where (host=* host!="") '
                + str(root_constraint)
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + root_by_clause_local
                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                + merged_sourcetype_eval_local
                + no_span_eval
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                + str(trackme_aggreg_splitby)
                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + extras_eval_local
                + "\n``` tenant_id ```"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n| `trackme_dhm_tracker_abstract("
                + str(tenant_id)
                + ", tstats)`"
            )

        elif search_mode in "raw":
            report_search = (
                str(root_constraint)
                + ' (host=* host!="")'
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                + merged_sourcetype_eval_local
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + "count as data_eventcount by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + extras_eval_local
                + "\n``` tenant_id ```\n"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n| `trackme_dhm_tracker_abstract("
                + str(tenant_id)
                + ", raw)`"
            )

    elif tracker_type == "remote":
        if search_mode in "tstats":
            report_search = (
                '| splunkremotesearch account="'
                + str(account)
                + '"'
                + ' search="'
                + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + 'count as data_eventcount where (host=* host!=\\"\\") '
                + str(root_constraint.replace('"', '\\"'))
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + root_by_clause_remote
                + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                + merged_sourcetype_eval_remote
                + no_span_eval
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                + str(trackme_aggreg_splitby)
                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + extras_eval_remote
                + '" earliest="'
                + str(earliest_time)
                + '" '
                + 'latest="'
                + str(latest_time)
                + '" tenant_id="'
                + str(tenant_id)
                + '" component="splk-dhm"'
                + "\n``` set tenant_id ```"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n`trackme_dhm_tracker_abstract("
                + str(tenant_id)
                + ", tstats)`"
            )

        elif search_mode in "raw":
            report_search = (
                '| splunkremotesearch account="'
                + str(account)
                + '"'
                + ' search="'
                + 'search (host=* host!=\\"\\") '
                + str(root_constraint.replace('"', '\\"'))
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                + merged_sourcetype_eval_remote
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + "count as data_eventcount, dc(host) as dcount_host by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + extras_eval_remote
                + '" earliest="'
                + str(earliest_time)
                + '" '
                + 'latest="'
                + str(latest_time)
                + '" tenant_id="'
                + str(tenant_id)
                + '" component="splk-dhm"'
                + "\n``` tenant_id ```"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n`trackme_dhm_tracker_abstract("
                + str(tenant_id)
                + ", raw)`"
            )

    #
    # finalize the search
    #

    report_search = remove_leading_spaces(
        f"""\
        {report_search}
        ``` collects latest collection state into the summary index ```
        | `trackme_collect_state("current_state_tracking:splk-dhm:{tenant_id}", "object", "{tenant_id}")`

        ``` output flipping change status if changes ```
        | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-dhm"
        | `trackme_outputlookup(trackme_dhm_tenant_{tenant_id}, key, {tenant_id})`
        | `trackme_mcollect(object, splk-dhm, "metric_name:trackme.splk.feeds.avg_eventcount_5m=avg_eventcount_5m, metric_name:trackme.splk.feeds.latest_eventcount_5m=latest_eventcount_5m, metric_name:trackme.splk.feeds.perc95_eventcount_5m=perc95_eventcount_5m, metric_name:trackme.splk.feeds.stdev_eventcount_5m=stdev_eventcount_5m, metric_name:trackme.splk.feeds.avg_latency_5m=avg_latency_5m, metric_name:trackme.splk.feeds.latest_latency_5m=latest_latency_5m, metric_name:trackme.splk.feeds.perc95_latency_5m=perc95_latency_5m, metric_name:trackme.splk.feeds.stdev_latency_5m=stdev_latency_5m, metric_name:trackme.splk.feeds.eventcount_4h=data_eventcount, metric_name:trackme.splk.feeds.lag_event_sec=data_last_lag_seen, metric_name:trackme.splk.feeds.lag_ingestion_sec=data_last_ingestion_lag_seen", "tenant_id, object_category, object", "{tenant_id}")`
        """
    )

    return report_search


# Usage:
# report_search = generate_dsm_report_search(
#     tracker_type='local',
#     search_mode='tstats',
#     tenant_id='tenant1',
#     root_constraint='index=*',
#     index_earliest_time='-24h',
#     index_latest_time='now',
#     dsm_tstats_root_time_span='1m',
#     trackme_root_splitby='source',
#     trackme_aggreg_splitby='source',
#     search_string_aggreg='| stats sum(data_eventcount) as data_eventcount',
#     tracker_name='my_tracker',
#     account='my_account',
#     earliest_time='-5m',
#     latest_time='now'
# )


def generate_dsm_report_search(
    entity_info,
    search_mode,
    tenant_id,
    account,
    index_earliest_time,
    index_latest_time,
    earliest_time,
    latest_time,
    root_constraint,
    dsm_tstats_root_time_span,
    breakby_field,
    dsm_tstats_root_breakby_include_splunk_server,
    dsm_tstats_root_breakby_include_host,
):
    #
    get_effective_logger().debug(
        f"retrieving search with function generate_dsm_report_search, search_mode={search_mode}, tenant_id={tenant_id}, account={account}, index_earliest_time={index_earliest_time}, index_latest_time={index_latest_time}, earliest_time={earliest_time}, latest_time={latest_time}, root_constraint={root_constraint}, dsm_tstats_root_time_span={dsm_tstats_root_time_span}, breakby_field={breakby_field}, dsm_tstats_root_breakby_include_splunk_server={dsm_tstats_root_breakby_include_splunk_server}, dsm_tstats_root_breakby_include_host={dsm_tstats_root_breakby_include_host}"
    )

    #
    # breaby statement
    #

    # set breakby_field if none
    if breakby_field == "none":
        breakby_field = None

    #
    # define trackme_root_splitby and trackme_aggreg_splitby
    #

    breakby_field_list = ["index", "sourcetype", "splunk_server", "host"]

    # default for breakby_field_include_sourcetype
    breakby_field_include_sourcetype = True

    if breakby_field and breakby_field != "merged":

        # if sourcetype in entity_info is set to *, then breakby_field_include_sourcetype is False
        if entity_info["sourcetype"] == "*":
            breakby_field_include_sourcetype = False

        custom_breakby_field_list = breakby_field.split(",")
        for field in custom_breakby_field_list:
            if not field in breakby_field_list:
                breakby_field_list.append(field)

    # translates into a csv list while handling few more options
    trackme_root_splitby = []
    for field in breakby_field_list:
        if field in ("index", "sourcetype"):
            trackme_root_splitby.append(field)
        elif field == "splunk_server":
            if dsm_tstats_root_breakby_include_splunk_server:
                trackme_root_splitby.append(field)
        elif field == "host":
            if dsm_tstats_root_breakby_include_host:
                trackme_root_splitby.append(field)
        else:
            trackme_root_splitby.append(field)

    # return as csv list
    trackme_root_splitby = ",".join(trackme_root_splitby)

    # aggreg split by (required for tstats searches)
    trackme_aggreg_splitby_list = ["index", "sourcetype"]
    if breakby_field and breakby_field != "merged":
        custom_breakby_field_list = breakby_field.split(",")
        for field in custom_breakby_field_list:
            if not field in trackme_aggreg_splitby_list:
                trackme_aggreg_splitby_list.append(field)

    # if entity_info["sourcetype"] is set to *, then remove sourcetype from trackme_aggreg_splitby_list
    if entity_info["sourcetype"] == "*":
        trackme_aggreg_splitby_list.remove("sourcetype")

    # translates into a csv list
    trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

    # "none" tstats root time span — drop _time and span= from the root
    # tstats by-clause and inject `eval _time=now()` so the rest of the
    # pipeline still has a single (synthetic) time bucket. Trades per-bucket
    # latency accuracy for substantially cheaper root tstats execution.
    is_no_span = str(dsm_tstats_root_time_span).lower() == "none"
    if is_no_span:
        # No _time, no span=...
        root_by_clause = " by " + str(trackme_root_splitby)
    else:
        root_by_clause = (
            " by _time,"
            + str(trackme_root_splitby)
            + " span="
            + str(dsm_tstats_root_time_span)
        )
    no_span_eval = (
        '\n``` no tstats time span ```\n| eval _time=now()' if is_no_span else ""
    )

    # set tracker_type
    if account == "local":
        tracker_type = "local"
    else:
        tracker_type = "remote"

    #
    # define search string aggreg
    #

    if tracker_type == "local":
        if breakby_field:
            if breakby_field == "merged":
                # remove sourcetype
                trackme_aggreg_splitby_list = []
                trackme_aggreg_splitby_list = trackme_aggreg_splitby.split(",")
                if "sourcetype" in trackme_aggreg_splitby_list:
                    trackme_aggreg_splitby_list.remove("sourcetype")
                trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

                # set object definition based on existing entity's object value
                # Check if entity_info has an object field and determine the convention
                existing_object = entity_info.get("object", "")
                # Check if existing object uses old convention (:all without @)
                # This ensures backward compatibility - existing entities keep :all, new ones use :@all
                if existing_object and existing_object.endswith(":all") and not existing_object.endswith(":@all"):
                    # Use old convention for existing entities
                    object_definition = ' | eval object=data_index . ":all"'
                else:
                    # Use new convention for new entities or entities with @all
                    object_definition = ' | eval object=data_index . ":@all"'

                if search_mode in "tstats":
                    search_string_aggreg = (
                        "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                        + "sum(data_eventcount) as data_eventcount by "
                        + str(trackme_aggreg_splitby)
                        + "\n| eval dcount_host=round(latest_dcount_host_5m, 2)"
                        + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                        + '\n| rename index as data_index | eval data_sourcetype="all"'
                        + object_definition
                    )

                elif search_mode in "raw":
                    search_string_aggreg = (
                        "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                        + "sum(data_eventcount) as data_eventcount by "
                        + str(trackme_aggreg_splitby)
                        + "\n"
                        + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                        + " | rename index as data_index\n"
                        + object_definition
                    )

            else:
                if search_mode in "tstats":
                    # support multiple fields
                    break_by_field = breakby_field.split(",")

                    if len(break_by_field) == 1:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=data_index . ":" . "any" . "|key:" . "'
                                + str(breakby_field)
                                + '" . "|" . '
                                + str(breakby_field)
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=data_index . ":" . data_sourcetype . "|key:" . "'
                                + str(breakby_field)
                                + '" . "|" . '
                                + str(breakby_field)
                            )

                    else:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=data_index . ":" . "any" . "|key:" . "'
                                + str(breakby_field).replace(",", ";")
                                + '" . "|"'
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=data_index . ":" . data_sourcetype . "|key:" . "'
                                + str(breakby_field).replace(",", ";")
                                + '" . "|"'
                            )

                        append_count = 0
                        for subbreak_by_field in break_by_field:
                            if append_count == 0:
                                object_definition = (
                                    object_definition + " . " + subbreak_by_field
                                )
                            else:
                                object_definition = (
                                    object_definition
                                    + " . "
                                    + '";"'
                                    + " . "
                                    + subbreak_by_field
                                )
                            append_count += 1

                    # search string aggreg
                    if not breakby_field_include_sourcetype:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n| eval dcount_host=round(latest_dcount_host_5m, 2)"
                            + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + '\n| rename index as data_index | eval data_sourcetype="any"'
                            + object_definition
                        )

                    else:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n| eval dcount_host=round(latest_dcount_host_5m, 2)"
                            + "\n| eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + "\n| rename index as data_index, sourcetype as data_sourcetype"
                            + object_definition
                        )

                elif search_mode in "raw":
                    # support multiple fields
                    break_by_field = breakby_field.split(",")

                    if len(break_by_field) == 1:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=data_index . ":" . "any" . "|rawkey:" . "'
                                + str(breakby_field)
                                + '" . "|" . '
                                + str(breakby_field)
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=data_index . ":" . data_sourcetype . "|rawkey:" . "'
                                + str(breakby_field)
                                + '" . "|" . '
                                + str(breakby_field)
                            )

                    else:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=data_index . ":" . "any" . "|rawkey:" . "'
                                + str(breakby_field).replace(",", ";")
                                + '" . "|"'
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=data_index . ":" . data_sourcetype . "|rawkey:" . "'
                                + str(breakby_field).replace(",", ";")
                                + '" . "|"'
                            )

                        append_count = 0
                        for subbreak_by_field in break_by_field:
                            if append_count == 0:
                                object_definition = (
                                    object_definition + " . " + subbreak_by_field
                                )
                            else:
                                object_definition = (
                                    object_definition
                                    + " . "
                                    + '";"'
                                    + " . "
                                    + subbreak_by_field
                                )
                            append_count += 1

                    # search string aggreg
                    if not breakby_field_include_sourcetype:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n"
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                            + ' | rename index as data_index | eval data_sourcetype="any"\n'
                            + object_definition
                        )

                    else:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + "\n"
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)\n"
                            + " | rename index as data_index, sourcetype as data_sourcetype\n"
                            + object_definition
                        )

        else:
            if search_mode in "tstats":
                search_string_aggreg = (
                    "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                    + "sum(data_eventcount) as data_eventcount by "
                    + str(trackme_aggreg_splitby)
                    + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                    + " | rename index as data_index, sourcetype as data_sourcetype"
                    + ' | eval object=data_index . ":" . data_sourcetype'
                )

            elif search_mode in "raw":
                search_string_aggreg = (
                    "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                    + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                    + "sum(data_eventcount) as data_eventcount by "
                    + str(trackme_aggreg_splitby)
                    + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                    + " | rename index as data_index, sourcetype as data_sourcetype"
                    + ' | eval object=data_index . ":" . data_sourcetype'
                )

    elif tracker_type == "remote":
        if breakby_field:
            if breakby_field == "merged":
                # remove sourcetype
                trackme_aggreg_splitby_list = []
                trackme_aggreg_splitby_list = trackme_aggreg_splitby.split(",")
                if "sourcetype" in trackme_aggreg_splitby_list:
                    trackme_aggreg_splitby_list.remove("sourcetype")
                trackme_aggreg_splitby = ",".join(trackme_aggreg_splitby_list)

                # set object definition based on existing entity's object value
                # Check if entity_info has an object field and determine the convention
                existing_object = entity_info.get("object", "")
                # Check if existing object uses old convention (:all without @)
                # This ensures backward compatibility - existing entities keep :all, new ones use :@all
                if existing_object and existing_object.endswith(":all") and not existing_object.endswith(":@all"):
                    # Use old convention for existing entities
                    object_definition = (
                        ' | eval object=\\"remote|account:'
                        + str(account.replace('"', ""))
                        + '|\\" . data_index . \\":all\\"'
                    )
                else:
                    # Use new convention for new entities or entities with @all
                    object_definition = (
                        ' | eval object=\\"remote|account:'
                        + str(account.replace('"', ""))
                        + '|\\" . data_index . \\":@all\\"'
                    )

                if search_mode in "tstats":
                    search_string_aggreg = (
                        "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                        + "sum(data_eventcount) as data_eventcount by "
                        + str(trackme_aggreg_splitby)
                        + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                        + ' | rename index as data_index | eval data_sourcetype=\\"all\\"'
                        + object_definition
                    )

                elif search_mode in "raw":
                    search_string_aggreg = (
                        "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                        + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                        + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                        + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                        + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                        + "sum(data_eventcount) as data_eventcount by "
                        + str(trackme_aggreg_splitby)
                        + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                        + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                        + ' | rename index as data_index | eval data_sourcetype=\\"all\\"'
                        + object_definition
                    )

            else:
                if search_mode in "tstats":
                    # support multiple fields
                    break_by_field = breakby_field.split(",")

                    if len(break_by_field) == 1:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|key:\\" . \\"'
                                + str(breakby_field)
                                + '\\" . \\"|\\" . '
                                + str(breakby_field)
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|key:\\" . \\"'
                                + str(breakby_field)
                                + '\\" . \\"|\\" . '
                                + str(breakby_field)
                            )

                    else:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|key:\\" . \\"'
                                + str(breakby_field).replace(",", ";")
                                + '\\" . \\"|\\" . '
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|key:\\" . \\"'
                                + str(breakby_field).replace(",", ";")
                                + '\\" . \\"|\\" . '
                            )

                        append_count = 0
                        for subbreak_by_field in break_by_field:
                            if append_count == 0:
                                object_definition = (
                                    object_definition + " . " + subbreak_by_field
                                )
                            else:
                                object_definition = (
                                    object_definition
                                    + " . "
                                    + '\\";\\"'
                                    + " . "
                                    + subbreak_by_field
                                )
                            append_count += 1

                    # search string aggreg
                    if not breakby_field_include_sourcetype:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + ' | rename index as data_index | eval data_sourcetype=\\"any\\"'
                            + object_definition
                        )

                    else:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + " | rename index as data_index, sourcetype as data_sourcetype"
                            + object_definition
                        )

                elif search_mode in "raw":
                    # support multiple fields
                    break_by_field = breakby_field.split(",")

                    if len(break_by_field) == 1:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|rawkey:\\" . \\"'
                                + str(breakby_field)
                                + '\\" . \\"|\\" . '
                                + str(breakby_field)
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|rawkey:\\" . \\"'
                                + str(breakby_field)
                                + '\\" . \\"|\\" . '
                                + str(breakby_field)
                            )

                    else:

                        # sourcetype to any with a custom breakby
                        if not breakby_field_include_sourcetype:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . \\"any\\" . \\"|rawkey:\\" . \\"'
                                + str(breakby_field).replace(",", ";")
                                + '\\" . \\"|\\" . '
                            )

                        # otherwise
                        else:
                            object_definition = (
                                ' | eval object=\\"remote|account:'
                                + str(account.replace('"', ""))
                                + '|\\" . data_index . \\":\\" . data_sourcetype . \\"|rawkey:\\" . \\"'
                                + str(breakby_field).replace(",", ";")
                                + '\\" . \\"|\\" . '
                            )

                        append_count = 0
                        for subbreak_by_field in break_by_field:
                            if append_count == 0:
                                object_definition = (
                                    object_definition + " . " + subbreak_by_field
                                )
                            else:
                                object_definition = (
                                    object_definition
                                    + " . "
                                    + '\\";\\"'
                                    + " . "
                                    + subbreak_by_field
                                )
                            append_count += 1

                    # search string aggreg
                    if not breakby_field_include_sourcetype:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + ' | rename index as data_index | eval data_sourcetype=\\"any\\"'
                            + object_definition
                        )

                    else:
                        search_string_aggreg = (
                            "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                            + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                            + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                            + "max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                            + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                            + "sum(data_eventcount) as data_eventcount by "
                            + str(trackme_aggreg_splitby)
                            + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                            + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                            + " | rename index as data_index, sourcetype as data_sourcetype"
                            + object_definition
                        )

        else:
            if search_mode in "tstats":
                search_string_aggreg = (
                    "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                    + " max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                    + "sum(data_eventcount) as data_eventcount by "
                    + str(trackme_aggreg_splitby)
                    + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                    + " | rename index as data_index, sourcetype as data_sourcetype"
                    + ' | eval object=\\"remote|account:'
                    + str(account.replace('"', ""))
                    + '|\\" . data_index . \\":\\" . data_sourcetype'
                )

            elif search_mode in "raw":
                search_string_aggreg = (
                    "stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m, "
                    + "latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m, "
                    + "latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, "
                    + " max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, "
                    + "max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, "
                    + "sum(data_eventcount) as data_eventcount by "
                    + str(trackme_aggreg_splitby)
                    + " | eval dcount_host=round(latest_dcount_host_5m, 2)\n"
                    + " | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)"
                    + " | rename index as data_index, sourcetype as data_sourcetype"
                    + ' | eval object=\\"remoteraw|account:'
                    + str(account.replace('"', ""))
                    + '|\\" . data_index . \\":\\" . data_sourcetype'
                )

    # report search
    if tracker_type == "local":
        if search_mode in "tstats":
            if dsm_tstats_root_breakby_include_host:
                report_search = (
                    "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                    + "count as data_eventcount where "
                    + str(root_constraint)
                    + ' _index_earliest="'
                    + index_earliest_time
                    + '" _index_latest="'
                    + index_latest_time
                    + '"'
                    + root_by_clause
                    + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                    + no_span_eval
                    + "\n``` intermediate calculation ```"
                    + "\n| bucket _time span=1m"
                    + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, dc(host) as dcount_host by _time,"
                    + str(trackme_aggreg_splitby)
                    + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                    + str(trackme_aggreg_splitby)
                    + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                    + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                    + str(trackme_aggreg_splitby)
                    + "\n| "
                    + str(search_string_aggreg)
                    + "\n``` tenant_id ```"
                    + '\n| eval tenant_id="'
                    + str(tenant_id)
                    + '"'
                    + "\n``` call the abstract macro ```"
                    + "\n`trackme_dsm_tracker_abstract("
                    + str(tenant_id)
                    + ", tstats)`"
                )

            else:
                report_search = (
                    "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                    + "count as data_eventcount, dc(host) as dcount_host where "
                    + str(root_constraint)
                    + ' _index_earliest="'
                    + index_earliest_time
                    + '" _index_latest="'
                    + index_latest_time
                    + '"'
                    + root_by_clause
                    + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                    + no_span_eval
                    + "\n``` intermediate calculation ```"
                    + "\n| bucket _time span=1m"
                    + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, max(dcount_host) as dcount_host by _time,"
                    + str(trackme_aggreg_splitby)
                    + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                    + str(trackme_aggreg_splitby)
                    + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                    + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                    + str(trackme_aggreg_splitby)
                    + "\n| "
                    + str(search_string_aggreg)
                    + "\n``` tenant_id ```"
                    + '\n| eval tenant_id="'
                    + str(tenant_id)
                    + '"'
                    + "\n``` call the abstract macro ```"
                    + "\n`trackme_dsm_tracker_abstract("
                    + str(tenant_id)
                    + ", tstats)`"
                )

        elif search_mode in "raw":
            report_search = (
                str(root_constraint)
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + "count as data_eventcount, dc(host) as dcount_host by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                + str(trackme_aggreg_splitby)
                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + "\n``` tenant_id ```"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n`trackme_dsm_tracker_abstract("
                + str(tenant_id)
                + ", raw)`"
            )

    elif tracker_type == "remote":
        if search_mode in "tstats":
            if dsm_tstats_root_breakby_include_host:
                report_search = (
                    '| splunkremotesearch account="'
                    + str(account)
                    + '"'
                    + ' search="'
                    + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                    + 'count as data_eventcount where (host=* host!=\\"\\") '
                    + str(root_constraint.replace('"', '\\"'))
                    + ' _index_earliest="'
                    + index_earliest_time
                    + '" _index_latest="'
                    + index_latest_time
                    + '"'
                    + root_by_clause
                    + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                    + no_span_eval
                    + "\n``` intermediate calculation ```"
                    + "\n| bucket _time span=1m"
                    + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, dc(host) as dcount_host by _time,"
                    + str(trackme_aggreg_splitby)
                    + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                    + str(trackme_aggreg_splitby)
                    + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                    + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                    + str(trackme_aggreg_splitby)
                    + "\n| "
                    + str(search_string_aggreg)
                    + '" earliest="'
                    + str(earliest_time)
                    + '" '
                    + 'latest="'
                    + str(latest_time)
                    + '" tenant_id="'
                    + str(tenant_id)
                    + '" component="splk-dsm"'
                    + "\n``` set tenant_id ```\n"
                    + '\n| eval tenant_id="'
                    + str(tenant_id)
                    + '"'
                    + "\n``` call the abstract macro ```"
                    + "\n`trackme_dsm_tracker_abstract("
                    + str(tenant_id)
                    + ", tstats)`"
                )

            else:
                report_search = (
                    '| splunkremotesearch account="'
                    + str(account)
                    + '"'
                    + ' search="'
                    + "| tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                    + "count as data_eventcount, dc(host) as dcount_host where "
                    + str(root_constraint.replace('"', '\\"'))
                    + ' _index_earliest="'
                    + index_earliest_time
                    + '" _index_latest="'
                    + index_latest_time
                    + '"'
                    + root_by_clause
                    + "\n| eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen"
                    + no_span_eval
                    + "\n``` intermediate calculation ```"
                    + "\n| bucket _time span=1m"
                    + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, sum(data_eventcount) as data_eventcount, max(dcount_host) as dcount_host by _time,"
                    + str(trackme_aggreg_splitby)
                    + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                    + str(trackme_aggreg_splitby)
                    + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                    + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                    + str(trackme_aggreg_splitby)
                    + "\n| "
                    + str(search_string_aggreg)
                    + '" earliest="'
                    + str(earliest_time)
                    + '" '
                    + 'latest="'
                    + str(latest_time)
                    + '" tenant_id="'
                    + str(tenant_id)
                    + '" component="splk-dsm"'
                    + "\n``` set tenant_id ```\n"
                    + '\n| eval tenant_id="'
                    + str(tenant_id)
                    + '"'
                    + "\n``` call the abstract macro ```"
                    + "\n`trackme_dsm_tracker_abstract("
                    + str(tenant_id)
                    + ", tstats)`"
                )

        elif search_mode in "raw":
            report_search = (
                '| splunkremotesearch account="'
                + str(account)
                + '"'
                + ' search="'
                + "search "
                + str(root_constraint.replace('"', '\\"'))
                + ' _index_earliest="'
                + index_earliest_time
                + '" _index_latest="'
                + index_latest_time
                + '"'
                + "\n| eval data_last_ingestion_lag_seen=(_indextime-_time)"
                + "\n``` intermediate calculation ```"
                + "\n| bucket _time span=1m"
                + "\n| stats avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, "
                + "count as data_eventcount, dc(host) as dcount_host by _time,"
                + str(trackme_aggreg_splitby)
                + "\n| eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen by "
                + str(trackme_aggreg_splitby)
                + " | eval spantime=if(spantime>=(now()-300), spantime, null())"
                + "\n| eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime,"
                + str(trackme_aggreg_splitby)
                + "\n| "
                + str(search_string_aggreg)
                + '" earliest="'
                + str(earliest_time)
                + '" '
                + 'latest="'
                + str(latest_time)
                + '" tenant_id="'
                + str(tenant_id)
                + '" component="splk-dsm"'
                + "\n``` tenant_id ```"
                + '\n| eval tenant_id="'
                + str(tenant_id)
                + '"'
                + "\n``` call the abstract macro ```"
                + "\n`trackme_dsm_tracker_abstract("
                + str(tenant_id)
                + ", raw)`"
            )

    #
    # finalize the search
    #

    report_search = remove_leading_spaces(
        f"""\
        {report_search}
        ``` collects latest collection state into the summary index ```
        | `trackme_collect_state("current_state_tracking:splk-dsm:{tenant_id}", "object", "{tenant_id}")`

        ``` output flipping change status if changes ```
        | trackmesplkgetflipping tenant_id="{tenant_id}" object_category="splk-dsm"
        | `trackme_outputlookup(trackme_dsm_tenant_{tenant_id}, key)`
        | `trackme_mcollect(object, splk-dsm, "metric_name:trackme.splk.feeds.avg_eventcount_5m=avg_eventcount_5m, metric_name:trackme.splk.feeds.latest_eventcount_5m=latest_eventcount_5m, metric_name:trackme.splk.feeds.perc95_eventcount_5m=perc95_eventcount_5m, metric_name:trackme.splk.feeds.stdev_eventcount_5m=stdev_eventcount_5m, metric_name:trackme.splk.feeds.avg_latency_5m=avg_latency_5m, metric_name:trackme.splk.feeds.latest_latency_5m=latest_latency_5m, metric_name:trackme.splk.feeds.perc95_latency_5m=perc95_latency_5m, metric_name:trackme.splk.feeds.stdev_latency_5m=stdev_latency_5m, metric_name:trackme.splk.feeds.eventcount_4h=data_eventcount, metric_name:trackme.splk.feeds.hostcount_4h=dcount_host, metric_name:trackme.splk.feeds.lag_event_sec=data_last_lag_seen, metric_name:trackme.splk.feeds.lag_ingestion_sec=data_last_ingestion_lag_seen", "tenant_id, object_category, object", "{tenant_id}")`
        """
    )

    return report_search


def generate_lookups_report_search(
    tenant_id,
    account,
    app_namespace,
    name_pattern,
    lookup_type,
    data_max_delay_allowed,
    kvstore_time_fields=None,
):
    """Build the SPL for a Hybrid Tracker running in lookups mode.

    The tracker invokes the ``trackmelookupsmonitor`` generative command
    (shipped by the ``TA-trackme-lookupmonitor`` add-on) to discover and
    inspect CSV and KVstore lookups visible on the search head, then feeds
    the resulting rows through the standard DSM persist pipeline via the
    new ``trackme_lookups_dedicated_tracker`` macro.

    ``kvstore_time_fields`` is a comma-separated, preference-ordered list
    of candidate field names the command tries when probing KVstore
    collections for a per-record mtime (KVstore does not maintain a
    timestamp automatically). Falls back to a sensible default matching
    the TA's own ``Option`` default.

    When ``account`` is anything other than ``"local"``, the command is
    wrapped with ``splunkremotesearch`` so it runs on the remote search
    head — that remote SH must have ``TA-trackme-lookupmonitor`` installed.
    """
    get_effective_logger().debug(
        "retrieving search with function generate_lookups_report_search, "
        "tenant_id=%s, account=%s, app_namespace=%s, name_pattern=%s, "
        "lookup_type=%s, kvstore_time_fields=%s, data_max_delay_allowed=%s",
        tenant_id,
        account,
        app_namespace,
        name_pattern,
        lookup_type,
        kvstore_time_fields,
        data_max_delay_allowed,
    )

    is_remote = bool(account) and account != "local"

    # Defence in depth: the REST handler already runs the lookups inputs
    # through ``sanitize_spl_quoted_arg`` at the parse boundary, but a
    # non-REST caller (e.g. internal Python code, a test) could bypass
    # that. Apply the same sanitiser here so the helper is safe in
    # isolation as well.
    safe_app_namespace = sanitize_spl_quoted_arg(app_namespace)
    safe_name_pattern = sanitize_spl_quoted_arg(name_pattern)
    safe_lookup_type = sanitize_spl_quoted_arg(lookup_type)
    safe_account = sanitize_spl_quoted_arg(account or "local")
    safe_tenant_id = sanitize_spl_quoted_arg(tenant_id)
    safe_kvstore_time_fields = sanitize_spl_quoted_arg(
        kvstore_time_fields
        or "_time, mtime, updated_at, modified, timestamp, last_modified"
    )

    core_command = (
        f'| trackmelookupsmonitor tenant_id="{safe_tenant_id}" '
        f'app_namespace="{safe_app_namespace}" '
        f'name_pattern="{safe_name_pattern}" '
        f'lookup_type="{safe_lookup_type}" '
        f'kvstore_time_fields="{safe_kvstore_time_fields}"'
    )

    if is_remote:
        # Escape BACKSLASHES FIRST, then double-quotes — otherwise a
        # regex `name_pattern` carrying `\d`, `\w`, `\.` etc. (preserved
        # by `sanitize_spl_quoted_arg`, which only strips trailing
        # backslashes) gets mangled when nested inside
        # `splunkremotesearch search="..."`: the remote SH's SPL parser
        # treats the bare `\` as an escape sequence and drops it before
        # the inner command sees the value. Same pattern as the
        # `remote_fragment` helper above (line 1448).
        core_escaped = core_command.replace("\\", "\\\\").replace('"', '\\"')
        prefix = (
            f'| splunkremotesearch account="{safe_account}" '
            f'search="{core_escaped}" tenant_id="{safe_tenant_id}"'
        )
    else:
        prefix = core_command

    # The latency-neutralisation eval chain
    # (`data_last_ingest`, `data_last_ingestion_lag_seen=0`,
    # `avg_latency_5m=0`, `data_max_lag_allowed=0`) lives inside the
    # ``trackme_lookups_dedicated_tracker`` macro — emitting it here would
    # duplicate the same statements at every call site. Only the
    # user-supplied delay threshold is bound at search-generation time.
    report_search = remove_leading_spaces(
        f"""\
        {prefix}

        ``` delay threshold: alert when the lookup has not been updated in
            the past data_max_delay_allowed seconds ```
        | eval data_max_delay_allowed={int(data_max_delay_allowed)}

        ``` standard DSM persist pipeline for lookups entities, including
            the latency-neutralisation evals (see the macro definition) ```
        | `trackme_lookups_dedicated_tracker({safe_tenant_id})`
        """
    )

    return report_search


# This function is used to generate metrics for splk-dsm and for the data sampling feature per model metrics
def trackme_splk_dsm_data_sampling_gen_metrics(
    tenant_id, metrics_idx, object_value, object_key, model_split_dict
):
    try:
        # Create a dedicated logger for DSM metrics
        dsm_logger = logging.getLogger("trackme.dsm.metrics")
        dsm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not dsm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_splk_dsm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            filehandler.setFormatter(formatter)
            dsm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            dsm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in dsm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_splk_dsm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                filehandler.setFormatter(formatter)
                dsm_logger.addHandler(filehandler)

        for key, record in model_split_dict.items():
            dsm_logger.info(
                "Metrics - group=feeds_metrics",
                extra={
                    "target_index": metrics_idx,
                    "tenant_id": tenant_id,
                    "object": decode_unicode(object_value),
                    "object_id": object_key,
                    "object_category": "splk-dsm",
                    "model_id": key,
                    "model_name": record.get("model_name"),
                    "model_type": record.get("model_type"),
                    "model_is_major": record.get("model_is_major"),
                    "metrics_event": json.dumps(
                        {
                            "sampling.model_pct_match": float(
                                record.get("model_pct_match")
                            ),
                            "sampling.model_count_matched": int(
                                record.get("model_count_matched")
                            ),
                            "sampling.model_count_parsed": int(
                                record.get("model_count_parsed")
                            ),
                        }
                    ),
                },
            )

        return True

    except Exception as e:
        raise Exception(str(e))


# This function is used to generate metrics for splk-dsm and for the data sampling feature and the total run_time/event_count metrics
def trackme_splk_dsm_data_sampling_total_run_time_gen_metrics(
    tenant_id, metrics_idx, object_value, object_key, run_time, events_count
):
    try:
        # Create a dedicated logger for DSM metrics
        dsm_logger = logging.getLogger("trackme.dsm.metrics")
        dsm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not dsm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_splk_dsm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            filehandler.setFormatter(formatter)
            dsm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            dsm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in dsm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_splk_dsm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                filehandler.setFormatter(formatter)
                dsm_logger.addHandler(filehandler)

        dsm_logger.info(
            "Metrics - group=feeds_metrics",
            extra={
                "target_index": metrics_idx,
                "tenant_id": tenant_id,
                "object": decode_unicode(object_value),
                "object_id": object_key,
                "object_category": "splk-dsm",
                "metrics_event": json.dumps(
                    {
                        "sampling.run_time": round(run_time, 3),
                        "sampling.events_count": int(events_count),
                    }
                ),
            },
        )

        return True

    except Exception as e:
        raise Exception(str(e))


# This function is used to generate metrics for splk-dhm
def trackme_splk_dhm_gen_metrics(tenant_id, metrics_idx, records):
    try:
        # Create a dedicated logger for DHM metrics
        dhm_logger = logging.getLogger("trackme.dhm.metrics")
        dhm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not dhm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_splk_dhm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            filehandler.setFormatter(formatter)
            dhm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            dhm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in dhm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_splk_dhm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                filehandler.setFormatter(formatter)
                dhm_logger.addHandler(filehandler)

        for record in records:
            metrics_dict = record.get("metrics_dict", None)

            if metrics_dict:
                for metric_entity, metrics_event in metrics_dict.items():
                    extra_payload = {
                        "target_index": metrics_idx,
                        "tenant_id": tenant_id,
                        "object": decode_unicode(record.get("object")),
                        "object_id": record.get("object_id"),
                        "alias": record.get("alias"),
                        "object_category": record.get("object_category"),
                        "idx": metrics_event.get("idx"),
                        "st": metrics_event.get("st"),
                        "metrics_event": json.dumps(
                            {
                                "last_eventcount": float(
                                    metrics_event.get("last_eventcount")
                                ),
                                "last_ingest_lag": float(
                                    metrics_event.get("last_ingest_lag")
                                ),
                                "last_event_lag": float(
                                    metrics_event.get("last_event_lag")
                                ),
                            }
                        ),
                    }
                    # Extras-aware trackers (breakby_extra_fields) attach a
                    # per-combo dict mapping field name → value. Splat each
                    # entry as a top-level dimension on the metric event so
                    # mstats queries can group by the extra field (e.g.
                    # `by source`). Reserved keys above (idx, st, object,
                    # object_id, alias, tenant_id, object_category,
                    # metrics_event, target_index) are NOT overwritten so a
                    # rogue extras field name can't shadow them. Defensive
                    # against malformed entries from the pipeline cache.
                    extras = metrics_event.get("extras")
                    if isinstance(extras, dict) and extras:
                        for extras_key, extras_value in extras.items():
                            if not extras_key:
                                continue
                            key_str = str(extras_key)
                            if key_str in extra_payload:
                                continue
                            extra_payload[key_str] = (
                                "" if extras_value is None else str(extras_value)
                            )
                    dhm_logger.info(
                        "Metrics - group=feeds_metrics",
                        extra=extra_payload,
                    )

        return True

    except Exception as e:
        raise Exception(str(e))


# This function is used to generate metrics for splk-mhm
def trackme_splk_mhm_gen_metrics(tenant_id, metrics_idx, records):
    try:
        # Create a dedicated logger for MHM metrics
        mhm_logger = logging.getLogger("trackme.mhm.metrics")
        mhm_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not mhm_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_splk_mhm_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            filehandler.setFormatter(formatter)
            mhm_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            mhm_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in mhm_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_splk_mhm_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                filehandler.setFormatter(formatter)
                mhm_logger.addHandler(filehandler)

        for record in records:
            metrics_dict = record.get("metrics_dict", None)

            if metrics_dict:
                for metric_entity, metrics_event in metrics_dict.items():
                    mhm_logger.info(
                        "Metrics - group=feeds_metrics",
                        extra={
                            "target_index": metrics_idx,
                            "tenant_id": tenant_id,
                            "object": decode_unicode(record.get("object")),
                            "object_id": record.get("object_id"),
                            "alias": record.get("alias"),
                            "object_category": record.get("object_category"),
                            "metric_category": metrics_event.get("metric_category"),
                            "metrics_event": json.dumps(
                                {
                                    "last_metric_lag": float(
                                        metrics_event.get("last_metric_lag")
                                    ),
                                }
                            ),
                        },
                    )

        return True

    except Exception as e:
        raise Exception(str(e))
