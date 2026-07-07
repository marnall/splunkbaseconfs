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

# Disable warnings for insecure requests (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_get_flipping.log" % splunkhome,
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
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import trackme_reqinfo, trackme_gen_state, trackme_idx_for_tenant
from trackme_libs_utils import decode_unicode

# import trackme libs sla
from trackme_libs_sla import trackme_sla_gen_metrics


@Configuration(distributed=False)
class TrackMeSplkGetFlipping(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    object_category = Option(
        doc="""
        **Syntax:** **object_category=****
        **Description:** The object_category value.""",
        require=False,
        validate=validators.Match(
            "object_category", r"^splk-(dsm|dhm|mhm|wlk|flx|fqm)$"
        ),
    )

    def stream(self, records):
        start = time.time()
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # set object_category
        if self.object_category:
            object_category = self.object_category
        else:
            object_category = None

        # create a list for SLA metrics generation
        sla_metrics_records = []

        for record in records:
            # extract the object_id, it can be set as key in the record, or as object_id
            key_id = record.get("key", None)
            object_id = record.get("object_id", None)
            if not object_id:
                if key_id:
                    object_id = key_id
                else:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", object_id="{object_id}", object_id could not be extracted (using key or object_id) from the record: {json.dumps(record, indent=1)}'
                    )
                    continue

            # other fields
            object_value = record.get("object")

            # get object_category if not set as an option (not expected anymore)
            if not object_category:
                object_category = record.get("object_category")

            alias = record.get("alias")
            monitored_state = record.get("monitored_state")
            priority = record.get("priority")
            current_state = record.get("current_state", "unknown")
            previous_state = record.get("previous_state", "unknown")
            anomaly_reason = record.get("anomaly_reason", "unknown")
            previous_anomaly_reason = record.get("previous_anomaly_reason", "unknown")
            disruption_time = 0
            try:
                latest_flip_time = float(record.get("latest_flip_time", time.time()))
            except Exception as e:
                latest_flip_time = time.time()
            latest_flip_state = record.get("latest_flip_state", "unknown")
            # Per-entity maintenance flag — lets the flip-event state description
            # distinguish a maintenance-induced blue from a logical-group blue
            # (see the trackme_eval_*_flip macros). Coerced to 1/0.
            try:
                is_under_maintenance = 1 if int(record.get("is_under_maintenance", 0) or 0) == 1 else 0
            except (TypeError, ValueError):
                is_under_maintenance = 0

            #
            # SLA metrics
            #

            if current_state == "green":
                object_num_state = 1
            elif current_state == "red":
                object_num_state = 2
            elif current_state == "orange":
                object_num_state = 3
            elif current_state == "blue":
                object_num_state = 4
            else:
                object_num_state = 5

            # add to our list
            sla_metrics_records.append(
                {
                    "tenant_id": self.tenant_id,
                    "object_id": object_id,
                    "object": object_value,
                    "alias": alias,
                    "object_category": object_category,
                    "monitored_state": monitored_state,
                    "priority": priority,
                    "metrics_event": {"object_state": object_num_state},
                }
            )

            #
            # flipping
            #

            if current_state != previous_state:
                if previous_state in ("unknown"):
                    logging.info(
                        f'previous_state is not part of the upstream results for object="{object_value}", will perform an additional KVstore record verification'
                    )

                    collection_name = f"kv_trackme_{object_category.split('-')[1]}_tenant_{self.tenant_id}"
                    collection = self.service.kvstore[collection_name]
                    query_string = {"_key": object_id}

                    try:
                        kvrecord = collection.data.query(
                            query=json.dumps(query_string)
                        )[0]
                        previous_state = kvrecord["object_state"]
                        previous_anomaly_reason = kvrecord["anomaly_reason", "unknown"]
                    except Exception as e:
                        previous_state = "discovered"
                        previous_anomaly_reason = "None"
                        logging.info(
                            f'could not find a KVstore record for object="{object_value}", this is expected if the object is not yet registered'
                        )

                gen_flip_event = current_state != previous_state

                if gen_flip_event:

                    # calculate disruption time if current_state is green and previous_state was red
                    if current_state == "green" and previous_state == "red":
                        try:
                            disruption_time = round(time.time() - latest_flip_time, 2)
                        except Exception as e:
                            disruption_time = 0

                    flip_timestamp = time.strftime(
                        "%d/%m/%Y %H:%M:%S", time.localtime(time.time())
                    )
                    disruption_time_str = f', disruption_time="{disruption_time}"' if disruption_time and disruption_time > 0 else ""
                    flip_result = f'{flip_timestamp}, object="{decode_unicode(object_value)}" has flipped from previous_state="{previous_state}" to state="{current_state}" with anomaly_reason="{anomaly_reason}", previous_anomaly_reason="{previous_anomaly_reason}"{disruption_time_str}'

                    flip_record = {
                        "timeStr": flip_timestamp,
                        "tenant_id": self.tenant_id,
                        "alias": alias,
                        "object": decode_unicode(object_value),
                        "keyid": object_id,
                        "object_category": object_category,
                        "object_state": current_state,
                        "object_previous_state": previous_state,
                        "priority": priority,
                        "latest_flip_time": latest_flip_time,
                        "latest_flip_state": latest_flip_state,
                        "anomaly_reason": anomaly_reason,
                        "is_under_maintenance": is_under_maintenance,
                        "result": flip_result,
                    }

                    # add event_id
                    flip_record["event_id"] = hashlib.sha256(
                        json.dumps(flip_record).encode()
                    ).hexdigest()

                    try:
                        trackme_gen_state(
                            index=tenant_indexes["trackme_summary_idx"],
                            sourcetype="trackme:flip",
                            source="flip_state_change_tracking",
                            event=flip_record,
                        )
                        logging.info(
                            f'TrackMe flipping event created successfully, tenant_id="{self.tenant_id}", record="{json.dumps(flip_record, indent=1)}"'
                        )

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", object="{object_value}", record="{json.dumps(flip_record, indent=1)}", failed to generate a flipping state event with exception="{e}"'
                        )

            yield record

        # call the SLA gen metrics function
        sla_metrics_gen_start = time.time()
        try:
            sla_metrics = trackme_sla_gen_metrics(
                self.tenant_id,
                tenant_indexes.get("trackme_metric_idx"),
                sla_metrics_records,
            )
            logging.info(
                f'context="sla_gen_metrics", tenant_id="{self.tenant_id}", function trackme_sla_gen_metrics success {sla_metrics}, run_time={round(time.time()-sla_metrics_gen_start, 3)}, no_entities={len(sla_metrics_records)}'
            )
        except Exception as e:
            logging.error(
                f'context="sla_gen_metrics", tenant_id="{self.tenant_id}", function trackme_sla_gen_metrics failed with exception {str(e)}'
            )

        run_time = round(time.time() - start, 3)
        logging.info(
            f'trackmesplkgetflipping has terminated, tenant_id="{self.tenant_id}", run_time={run_time}'
        )


dispatch(TrackMeSplkGetFlipping, sys.argv, sys.stdin, sys.stdout, __name__)
