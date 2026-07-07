# encoding = utf-8
"""Retrieve ExtraHop metrics from REST API and send to Splunk as events."""

import sys
import json
import math
import time
from collections import namedtuple
from splunk.clilib import cli_common as cli
from extrahop_common import ExtraHopClient
from extrahop_objecttypes import EXTRAHOP_OBJECT_TYPES

import os
import traceback
from extrahop_common import get_proxy_uri
from extrahop_services import KVStoreCollection, ObjectNotFoundError, InvalidHostError
from ta_extrahop_addon_declare import ta_name


class EventPayloadFactory:
    """Packages and produces Splunk event data for ExtraHop metrics."""

    def __init__(self, cycle, hostname, inputname, metcat, object_type):
        """Saves metadata for ExtraHop metrics and produces the correct event formatting for each metric type.

        Args:
            cycle (str): Metric cycle length (30sec)
            hostname (str): ExtraHop appliance hostname
            inputname (str): Splunk Data input name
            metcat (str): ExtraHop metric category
            object_type (str): ExtraHop object type
        """
        self.metadata = {
            "hostname": hostname,
            "source": f"extrahop:{inputname}",
            "sourcetype": "extrahop",
        }
        self.cycle = cycle
        self.metcat = metcat
        self.object_type = object_type

    def new_payload(self, oid, timestamp):
        """Initializes ExtraHop metadata for Splunk event.

        Args:
            oid (int): ExtraHop object ID
            timestamp (int): Cycle start time in milliseconds

        Returns:
            EventPayload: event data for Splunk stream
        """
        event = self.EventPayload()
        event.data["oid"] = oid
        event.data["cycle"] = self.cycle
        event.data["metric_category"] = self.metcat
        event.data["object_type"] = self.object_type
        event.meta = self.metadata
        event.meta["timestamp"] = timestamp / 1000  # convert ms->s
        return event

    class EventPayload:
        """Event data for ExtraHop metrics."""

        def __init__(self):
            """Init method."""
            self.data = {}
            self.meta = {}
            self.has_data = False

        def add(self, key, value):
            """Adds a single metric to the event payload.

            Args:
                key (str): Metric name
                value: Metric value
            """
            self.data[key] = value
            self.has_data = True

        def batchadd(self, vlist):
            """Adds multiple metrics to the event payload.

            Args:
                vlist (list(k,v)): List of (metric name, metric value)
            """
            for (k, v) in vlist:
                self.add(k, v)
            self.has_data = True

        def make_event(self, helper):
            """Creates a Splunk event with the data in this EventPayload.

            Args:
                helper: Splunk Add-On Builder helper object

            Returns:
                Splunk event object
            """
            return helper.new_event(
                json.dumps(self.data),
                time=self.meta["timestamp"],
                source=self.meta["source"],
                sourcetype=self.meta["sourcetype"],
                host=self.meta["hostname"],
                index=helper.get_output_index(),
            )


def cycle_to_msecs(cycle):
    """Converts cycle name to milliseconds."""
    default_cycle = "30sec"
    cyclesizes = {"30sec": 30000, "5min": 300000, "1hr": 3600000}
    default_cyclesize = cyclesizes[default_cycle]
    return cyclesizes.get(cycle, default_cyclesize)


def get_cycle_boundary(t, cycle):
    """Gets the epoch time of the start of the metric cycle that t is in."""
    return t - (t % cycle_to_msecs(cycle))


def get_metrictype_kv(
    oids, data_input_type, metric_category, metric_name, kvc, kvc_metcat_name, extrahop, helper
):
    """Retrieves the metric type from the Splunk KV Store.

    If the metric type hasn't been committed to the KV Store, infer the metric
    type in a query to the ExtraHop appliance, then store it.

    :param int oids: list of ExtraHop object id
    :param str data_input_type: ExtraHop Add-On data input type
    :param str metric_category: metric category from modinput
    :param str metric_name: metric name from modinput
    :param kvc: Splunk KV Store to read from / write to
    :type kvc: KVStoreCollection
    :param extrahop: ExtraHop REST API client
    :type extrahop: ExtraHopClient
    :return: mtype, the type of metric from the KV Store
    :rtype: str
    """
    # helper.log_debug("get_metrictype_kv method start")
    object_type = EXTRAHOP_OBJECT_TYPES.get(data_input_type).api_object_type
    canonical_type = EXTRAHOP_OBJECT_TYPES.get(data_input_type).canonical_metric_type
    key = ".".join([canonical_type, metric_category, metric_name])
    stanza_name = helper.get_input_stanza_names()

    try:
        # look up metric type in KV store
        kv_data = kvc.get_by_key(kvc_metcat_name, key)
        return kv_data["value"]
    except ObjectNotFoundError:
        # couldn't find metric type in KV store, so infer metric type from /metrics response
        # look at the last day of metrics to try to get a value
        payload, _ = create_metric_querydata(
            oids,
            object_type,
            metric_category,
            {metric_name: ""},
            cycle="auto",
            time_from=-86400000,
        )
        try:
            output = extrahop.post("metrics/total", payload).json()
            # Command Appliance shim
            xid = output.get("xid")
            num_results = output.get("num_results", 1)
            if xid:  # COMMAND APPLIANCE RESULTS
                try:
                    for _ in range(
                        num_results
                    ):  # iterate through results until we have values to test
                        output = extrahop.get(f"metrics/next/{xid}").json()
                        if output["stats"][0]["values"][0]:
                            break
                except Exception as exn:
                    helper.log_error(
                        f"{stanza_name}:: Could not retrieve ECA metrics: {exn}"
                    )
            # end Command Appliance shim
            value = output["stats"][0]["values"][0]
            vtype = infer_metric_type(value, metric_name)
            assert vtype
            kvc.insert(kvc_metcat_name, {"_key": key, "value": vtype})
            return vtype
        except Exception as exn:
            helper.log_error(
                f"{stanza_name}:: Could not find metric {metric_name} in category "
                f"{canonical_type}.{metric_category}: {exn}"
            )


def infer_metric_type(data, metric_name):
    """Guess what metric type we've been given.

    :param data: a metric value from EH REST API
    :type data: int or list
    :param str metric_name: name of the metric (needed for sset/dsset discrimination)
    :return: string representing metric type
    """
    if isinstance(data, int):
        return "count"
    if isinstance(data, list) and len(data) > 0:
        # non-tsets will wrap the data object in a list
        # for tset processing, we've already unwrapped
        data = data[0]
    if "vtype" in data:
        vtype = data["vtype"]
        if vtype == "count":
            return "dcount"
        if vtype == "dmax":
            return "dcount"
        if vtype == "dset":
            return "ddset"
        if vtype == "max":
            return "dmax"
        if vtype == "sset":
            if extract_detail_key(data["key"]) == metric_name:
                return "sset"
            return "dsset"
        if vtype == "tset":
            return "tset"
        if vtype == "time":
            return "time"
        if vtype == "snap":
            return "dsnap"
    elif "freq" in data:
        return "dset"

    return ""


def create_metric_querydata(
    object_ids,
    object_type,
    metric_category,
    metrics,
    cycle="30sec",
    time_from=-30000,
    time_until=0,
):
    """Formats the data for a metric lookup in the ExtraHop REST API.

    :param int object_ids: List of ExtraHop object IDs
    :param str object_type: ExtraHop object type
    :param str metric_category: ExtraHop metric category
    :param metrics: metric names to request in format {metric_name: metric_type}
    :type metrics: dict(str, str)
    :param str cycle: metric cycle, element of ("30sec", "5min", "1hr")
    :param int time_from: timestamp for beginning of metric request
    :param int time_until: timestamp for end of metric request
    :return: REST API query string, list of metric names in request order
    :rtype: tuple(str, list(str))
    """
    metric_specs = []
    metric_names = []
    for metric_name, mtype in metrics.items():
        if mtype in ("dset", "ddset"):
            metric_specs.append(
                f'{{"name":"{metric_name}", "calc_type":"percentiles", "percentiles":[5,25,50,75,95]}}'
            )
        else:
            metric_specs.append(f'{{"name":"{metric_name}"}}')
        metric_names.append(metric_name)
    metric_specs = str(metric_specs).replace("'", "")
    return (
        "".join(
            (
                "{",
                f'"cycle":"{cycle}",',
                f'"from":{time_from},',
                f'"until":{time_until},',
                f'"object_ids":{object_ids},',
                f'"object_type":"{object_type}",',
                f'"metric_category":"{metric_category}",',
                f'"metric_specs":{metric_specs}',
                "}",
            )
        ),
        metric_names,
    )


def metric_processor_factory(mtype):
    """Returns the processing function for the given metric type."""
    # BASIC METRICS
    def process_dcount(metric, value, tset_key=None):
        """Extracts detail count metrics from metric payload.

        extrahop.device.ssl_client.cipher
        {
            "key": {
              "key_type": "string",
              "str": "TLS_RSA_WITH_AES_256_GCM_SHA384"
            },
            "vtype": "count",
            "value": 1
        }
        """
        assert len(value) > 0
        detail = extract_detail_key(value["key"])
        outputdata = [(metric, value["value"]), ("detail", detail)]
        if tset_key:
            outputdata.append(("key", tset_key))
        return outputdata

    def process_sset(metric, value):
        """Extracts sampleset metrics from metric payload.

        Expect only to be called through process_dsset(),
        since there are no scalar sampleset metrics <= EDA 7.7.0
        {
            "count": 1,
            "sum": 43.062,
            "sum2": 1854.335844
        }
        """
        assert len(value) > 0
        # calculate mean
        ndig = 3  # number of digits to round to
        count = value["count"]
        if count > 0:
            mean = round(float(value["sum"]) / float(count), ndig)
        else:
            mean = value["sum"]
        # calculate standard deviation
        if count > 1:
            std_dev = round(math.sqrt(float(value["sum2"]) / (float(count) - 1)), ndig)
        else:
            std_dev = 0
        return [
            (".".join([metric, "mean"]), mean),
            (".".join([metric, "sd"]), std_dev),
            (".".join([metric, "count"]), count),
        ]

    def process_dset(metric, value):
        """Extracts dataset metrics from metric payload.

        Expect five percentiles as the result (see create_metric_querydata())
        extrahop.device.ssl_client.rtt
         [
          7.0265,
          9.2685,
          18.947,
          30.17,
          50.9552
        ]
        """
        assert len(value) > 0
        quantiles = ["p5", "p25", "p50", "p75", "p95"]
        return [(".".join([metric, q]), v) for (q, v) in zip(quantiles, value)]

    # DETAIL METRIC FUNCTIONS
    #   For these metrics, we can rely on the above processors
    #   with some additional finesse for handling the detail keys
    def process_dsset(metric, value, tset_key=None):
        """Extracts detail sampleset metrics from metric payload.

        extrahop.device.http_client_detail.tprocess
        {
            "key": {
              "key_type": "ipaddr",
              "addr": "1.2.3.4",
              "device_oid": 15,
              "host": "somehost.extrahop.com"
            },
            "vtype": "sset",
            "value": {
              "count": 1,
              "sum": 43.062,
              "sum2": 1854.335844
            }
          }
        """
        assert len(value) > 0
        detail = extract_detail_key(value["key"])
        outputdata = process_sset(metric, value["value"])
        outputdata.append(("detail", detail))
        if tset_key:
            outputdata.append(("key", tset_key))
        return outputdata

    def process_ddset(metric, value, tset_key=None):
        """Extracts detail dataset metrics from metric payload.

        Expect five percentiles as the result (see create_metric_querydata())
        extrahop.device.ssl_client_detail.handshake_time_version
        {
            "key": {
              "key_type": "string",
              "str": "TLSv1.2"
            },
            "vtype": "dset",
            "value": [
              1.03225,
              1.80775,
              2.7965,
              3.6535,
              9.22515
            ]
        }
        """
        assert len(value) > 0
        detail = extract_detail_key(value["key"])
        outputdata = process_dset(metric, value["value"])
        outputdata.append(("detail", detail))
        if tset_key:
            outputdata.append(("key", tset_key))
        return outputdata

    def process_dmax(metric, value, tset_key=None):
        """Extracts detail max metrics from metric payload.

        extrahop.device.tcp_detail.established_max
        {
            "key": {
              "key_type": "ipaddr",
              "addr": "1.2.3.4",
              "device_oid": 15,
              "host": "somehost.extrahop.com"
            },
            "vtype": "max",
            "value": 1
          }
        """
        return process_dcount(metric, value, tset_key)

    def process_time(metric, value, tset_key=None):
        """Extracts time metrics from metric payload.

        extrahop.device.ssl_server.
        {
            "key": {
              "key_type": "string",
              "str": "somehost.extrahop.com:RSA_2048"
            },
            "vtype": "time",
            "value": 1564778310000
        }
        """
        return process_dcount(metric, value, tset_key)

    def process_dsnap(metric, value, tset_key=None):
        """Extracts detail snap metrics from metric payload.

        extrahop.device.tcp_detail.established
        {
            "key": {
              "key_type": "ipaddr",
              "addr": "1.2.3.4",
              "device_oid": 15
            },
            "vtype": "snap",
            "value": 1
          }
        """
        return process_dcount(metric, value, tset_key)

    # metric_processor_factory body
    return locals().get(f"process_{mtype}")


def extract_detail_key(key):
    """Extracts detail key data from metric payload."""
    if key["key_type"] == "string":
        return key["str"]
    if key["key_type"] == "ipaddr":
        return key["addr"]


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # hostname = definition.parameters.get('hostname', None)
    # api_key = definition.parameters.get('api_key', None)
    # validate_ssl_certificates = definition.parameters.get('validate_ssl_certificates', None)
    # object_type = definition.parameters.get('object_type', None)
    # object_id = definition.parameters.get('object_id', None)
    # metric_category = definition.parameters.get('metric_category', None)
    # metric_name = definition.parameters.get('metric_name', None)
    parameters = definition.parameters if "parameters" in dir(definition) else definition
    data_input_type = parameters.get("object_type", "").strip()
    object_id = parameters.get("object_id", "").strip()
    cyclesize = parameters.get("cyclesize", "").strip()
    interval = parameters.get("interval", 0).strip()
    CYCLE_SIZES = ["30sec", "5min", "1hr"]

    try:
        oids = object_id.split(",")
        for obj_id in oids:
            oid = int(obj_id)
            assert isinstance(oid, int)
    except AssertionError:
        helper.log_error(
            "Invalid Object ID found for the input name: {}. "
            "Object ID should be a number".format(parameters.get("name", ""))
        )
        return False
    except ValueError:
        helper.log_error(
            "Invalid Object ID found for the input name: {}. "
            "Object ID should be a number".format(parameters.get("name", ""))
        )
        return False
    except Exception as e:
        helper.log_error(
            "Error while validating the object_id for the input name: {}. "
            "Error: {}".format(parameters.get("name", ""), e)
        )
        return False

    try:
        assert data_input_type in EXTRAHOP_OBJECT_TYPES
    except AssertionError:
        helper.log_error(
            "Invalid Object type found for the input name: {}. "
            "Object type should be one of the following: {}"
            .format(parameters.get("name", ""), [x for x in EXTRAHOP_OBJECT_TYPES])
        )
        return False

    try:
        assert cyclesize in CYCLE_SIZES
    except AssertionError:
        helper.log_error(
            "Invalid Cycle size found for the input name: {}. "
            "Cycle size should be one of the following: {}"
            .format(CYCLE_SIZES, parameters.get("name", ""))
        )
        return False

    try:
        interval = int(interval)
        assert interval > 0
    except ValueError:
        helper.log_error(
            "Invalid Interval found for the input name: {}. "
            "Interval should be integer value".format(parameters.get("name", ""))
        )
        return False
    except AssertionError:
        helper.log_error(
            "Invalid Interval found for the input name: {}. "
            "Interval should be greater than 0".format(parameters.get("name", ""))
        )
        return False

    return True


def collect_events(helper, ew):
    def collect(oids, cycle_start, cycle_end):
        """Collects events for particular object.

        Called from collect_events method. Called in loop for handling list of object ids.

        :param oids: object ids from extrahop REST api
        :type object_id: str
        :param cycle_start: timestamp for lower bound on metric request
        :type cycle_start: int
        :param cycle_end: timestamp for upper bound on metric request
        :type cycle_end: int
        """
        helper.log_debug(
            f"{stanza_name}:: processing cycle, Object ID = {oids}, starttime = {cycle_start}, endtime = {cycle_end}"
        )

        # metric_nametypes should be dictionary of {metric_name: metric_type}
        metric_nametypes = {
            metric_name: get_metrictype_kv(
                oids,
                data_input_type,
                metric_category,
                metric_name,
                kvc_service,
                kvc_metcat_name,
                extrahop,
                helper,
            )
            for metric_name in metric_names
        }
        helper.log_debug(f"{stanza_name}:: metric_nametypes: {metric_nametypes}")

        payload, metric_names_ordered = create_metric_querydata(
            oids,
            object_type,
            metric_category,
            metric_nametypes,
            cycle=cycle,
            time_from=cycle_start,
            time_until=cycle_end - 1,
        )
        helper.log_info("{}:: Request Payload is: {}".format(stanza_name, payload))
        try:
            metrics_endpoint = EXTRAHOP_OBJECT_TYPES.get(
                data_input_type
            ).metrics_endpoint
            extrahop_response = extrahop.post(metrics_endpoint, payload).json()
        except Exception as exn:
            helper.log_error(
                f"{stanza_name}:: Could not retrieve metrics, probably due to incorrect metric name, "
                f"metric category, or object ID: {exn}"
            )
            raise ValueError(exn)
        epfactory = EventPayloadFactory(
            cycle=cycle,
            hostname=hostname,
            inputname=helper.get_arg("name"),
            metcat=metric_category,
            object_type=event_object_type,
        )
        # test for ECA or EDA results
        # ECA will return an xid and num_results:
        #   /metrics/next/{xid} will return stats, up to {num_results} times
        # EDA will return a simple stats response, once
        xid = extrahop_response.get("xid")
        num_results = extrahop_response.get("num_results", 1)
        helper.log_debug(
            f"{stanza_name}:: extrahop_response: xid {xid}, num_results {num_results}"
        )
        total_events = 0
        indexed_events = 0
        for _ in range(num_results):
            if xid:  # COMMAND APPLIANCE RESULTS
                try:
                    metric_data = extrahop.get(f"metrics/next/{xid}").json()
                except Exception as exn:
                    helper.log_error(
                        f"{stanza_name}:: Could not retrieve ECA metrics: {exn}"
                    )
                    continue
            else:  # DISCOVER APPLIANCE RESULTS
                metric_data = extrahop_response

            # format data into events
            total_events += len(metric_data.get("stats"))
            for item in metric_data.get("stats"):
                # summary metrics produce oid=-1 in API response
                item_oid = item["oid"] if item["oid"] != -1 else oids
                timestamp = item["time"]
                basic_event_payload = epfactory.new_payload(item_oid, timestamp)
                for (metric, value) in zip(metric_names_ordered, item["values"]):
                    thismetrictype = metric_nametypes[metric]
                    if thismetrictype == "tset":
                        for val in value:
                            key_value = extract_detail_key(val["key"])
                            tset_key = key_value if key_value != metric else None
                            for v in val["value"]:
                                submetrictype = infer_metric_type(v, metric)
                                processor = metric_processor_factory(submetrictype)
                                detail_event_payload = epfactory.new_payload(
                                    item_oid, timestamp
                                )
                                detail_event_payload.batchadd(
                                    processor(metric, v, tset_key)
                                )
                                if detail_event_payload.has_data:
                                    indexed_events += 1
                                    ew.write_event(
                                        detail_event_payload.make_event(helper)
                                    )
                    elif thismetrictype in ("count", "max"):
                        basic_event_payload.add(metric, value)
                    elif thismetrictype in ("dset", "sset"):
                        processor = metric_processor_factory(thismetrictype)
                        basic_event_payload.batchadd(processor(metric, value))
                    elif thismetrictype in (
                        "dcount",
                        "ddset",
                        "dsset",
                        "dmax",
                        "time",
                        "dsnap",
                    ):
                        # we expect an array of detail metrics, so for each object in the array:
                        # 1. grab the method that handles this type of data
                        # 2. create a new Splunk event for this
                        # 3. extract the metrics from object, append to Splunk event
                        # 4. commit to Splunk
                        for val in value:
                            if len(val) > 0:
                                processor = metric_processor_factory(thismetrictype)
                                detail_event_payload = epfactory.new_payload(
                                    item_oid, timestamp
                                )
                                detail_event_payload.batchadd(processor(metric, val))
                                if detail_event_payload.has_data:
                                    indexed_events += 1
                                    ew.write_event(
                                        detail_event_payload.make_event(helper)
                                    )

                if basic_event_payload.has_data:
                    indexed_events += 1
                    ew.write_event(basic_event_payload.make_event(helper))

                # add oid to object data lookup set
                this_ehobject = EHObject(hostname, str(item_oid), event_object_type)
                this_ehobject_id = ":".join(this_ehobject)
                try:
                    kvc_service.get_by_key(kvc_oiddev_name, this_ehobject_id)
                except ObjectNotFoundError:
                    helper.log_debug(
                        f"{stanza_name}:: adding {this_ehobject_id} to lookup set"
                    )
                    ehobject_lookup_set.add(this_ehobject)
        helper.log_info(
            "{}:: Received total {} events from response and indexed total {} events into the splunk "
            "after processing the data for processing cycle, Object ID = {}, starttime = {}, endtime = {}"
            .format(stanza_name, total_events, indexed_events, oids, cycle_start, cycle_end)
        )

    helper.set_log_level(helper.get_log_level())
    stanza_name = helper.get_input_stanza_names()
    input_stanza = helper.get_input_stanza(stanza_name)
    try:
        assert validate_input(helper, input_stanza) == True
    except AssertionError:
        sys.exit()

    hostname = helper.get_arg("global_account").get("hostname").strip().lower()
    verify_certs = cli.getConfStanza('ta_extrahop_addon_settings', 'additional_parameters').get(
        'validate_ssl_certificates', '1')
    verify_certs = False if verify_certs in ["False", "0", "false"] else True
    # data_input_type is a combination of ExtraHop object type and metrics aggregation type.
    # data_input_type is configured in the data input, and EXTRAHOP_OBJECT_TYPES translates this
    # into object_type for 'metrics' or 'metrics/total' API calls.
    data_input_type = helper.get_arg("object_type").strip().lower()
    object_type = EXTRAHOP_OBJECT_TYPES.get(data_input_type).api_object_type
    event_object_type = EXTRAHOP_OBJECT_TYPES.get(data_input_type).event_object_type
    object_ids = helper.get_arg("object_id").strip().split(",")
    metric_category = helper.get_arg("metric_category").strip().lower()
    metric_names = helper.get_arg("metric_name").split(",")
    # assuming multi-threaded, stanza_name should be str, not list

    # Splunk Management host:port settings for SDK client connection
    splunk_mgmt_env_type = helper.get_global_setting("splunk_mgmt_env_type")
    splunk_mgmt_host = helper.get_global_setting("splunk_mgmt_host")
    splunk_mgmt_port = helper.get_global_setting("splunk_mgmt_port")
    splunk_mgmt_username = helper.get_global_setting("splunk_mgmt_username")
    splunk_mgmt_password = helper.get_global_setting("splunk_mgmt_password")

    # default to 30sec cycles if it's not configured
    # (may not be configured for legacy data inputs)
    cycle = helper.get_arg("cyclesize")
    cycle = cycle.strip().lower() if cycle is not None else "30sec"
    cyclesize = cycle_to_msecs(cycle)

    # calculate the boundaries for the proposed metric pull
    # if we don't have new metrics to pull, i.e. if the event triggers
    # more frequently than the metric cycle length, then don't bother
    # trying to retrieve metric data
    now = int(time.time()) * 1000  # convert to msec
    checkpoint_time = helper.get_check_point(stanza_name)
    # init checkpoint with a default value, default to one hour ago
    if checkpoint_time is None:
        checkpoint_time = now - (60 * 60 * 1000)
        helper.log_info(
            f"{stanza_name}:: did not find checkpoint time, defaulting to {checkpoint_time}"
        )

    # define the boundaries of our metric collection
    collection_start_time = get_cycle_boundary(int(checkpoint_time), cycle)
    collection_end_time = get_cycle_boundary(now, cycle)
    if collection_end_time == collection_start_time:
        helper.log_debug(
            f"{stanza_name}:: don't need new metrics yet: checkpoint time {checkpoint_time} + "
            f"cycle length {cyclesize} msecs < time now {now}"
        )
        return

    helper.log_debug(f"{stanza_name}:: collect_events method start")

    # Setup Proxy
    try:
        proxies = get_proxy_uri(helper.context_meta["session_key"])
        if proxies:
            # Splunk's local network call throws error if NO_PROXY is not set.
            # This is a list of hostnames, which should not go through proxy.
            os.environ["no_proxy"] = "localhost,127.0.0.1,0.0.0.0,localaddress"
            os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0,localaddress"

            os.environ["http_proxy"] = proxies.get('http')
            os.environ["HTTP_PROXY"] = proxies.get('http')

            os.environ["https_proxy"] = proxies.get('https')
            os.environ["HTTPS_PROXY"] = proxies.get('https')

            helper.log_info(f"{stanza_name}:: Proxy settings are configured successfully.")
    except Exception as err:
        helper.log_error(
            "{}:: Error occurred while setting up proxy settings: {}\n{}"
            .format(stanza_name, err, traceback.format_exc())
        )
        return

    # # Initialize KVStoreCollection client
    if not splunk_mgmt_env_type or splunk_mgmt_env_type == "local_instance":
        splunk_mgmt_host = 'localhost'
        if splunk_mgmt_port is None:
            splunk_mgmt_port = cli.getConfStanza(
                'ta_extrahop_addon_settings', 'add_on_settings'
            ).get('local_instance_management_port', '8089')

        helper.log_info(
            "{}:: Splunk Management configuration: {{Host: {}, Port: {}}}"
            .format(stanza_name, splunk_mgmt_host, splunk_mgmt_port)
        )

        # if local instance then use token for authentication
        # instead of username and password
        kvc_service = KVStoreCollection(
            host=splunk_mgmt_host,
            port=splunk_mgmt_port,
            token=helper.context_meta['session_key'],
            app=ta_name
        )
        try:
            kvc_service.verify_port()
        except InvalidHostError:
            raise Exception(
                "Error occurred while validating Splunk Management settings. "
                "Can not connect to Splunk server. Please enter valid port number and "
                "make sure that port is open."
            )

    else:
        helper.log_info(
            "{}:: Splunk Management configuration: {{Host: {}, Port: {}}}"
            .format(stanza_name, splunk_mgmt_host, splunk_mgmt_port)
        )

        # authenticate cluster instance with username and password
        kvc_service = KVStoreCollection(
            host=splunk_mgmt_host,
            port=splunk_mgmt_port,
            username=splunk_mgmt_username,
            password=splunk_mgmt_password,
            app=ta_name
        )
        try:
            kvc_service.login()
        except InvalidHostError:
            raise Exception(
                "Error occurred while validating Splunk Management settings. "
                "Can not connect to Splunk server. Please enter valid port number and "
                "make sure that port is open."
            )

    # connect to KV Store containing metric catalog definitions
    kvc_metcat_name = "TA_extrahop_metcat"
    kvc_applianceuuid_name = "TA_extrahop_appuuid"

    # create a set to store object data as we process metrics
    # later, we'll look in the TA_extrahop_oiddev KV Store for those objects
    # and query ExtraHop for object data if it's missing
    # as a replacement for oid_search.py

    EHObject = namedtuple("EHObject", ["hostname", "oid", "object_type"])
    ehobject_lookup_set = set()
    kvc_oiddev_name = "TA_extrahop_oiddev"

    try:
        # init extrahop client
        extrahop = ExtraHopClient(
            hostname,
            helper,
            verify_certs=bool(verify_certs)
        )
    except Exception as e:
        helper.log_error("Exception occured while initializing Extrahop client: {}".format(e))
        sys.exit(1)
    # put appliance UUID in KV Store
    try:
        kvc_service.get_by_key(kvc_applianceuuid_name, hostname)
    except ObjectNotFoundError:
        helper.log_info(f"{stanza_name}:: adding appliance uuid to KV store")
        try:
            eh_platform = extrahop.get("extrahop/platform").json()["platform"]
            if eh_platform == "extrahop":
                uuid = extrahop.get("networks/0").json()["appliance_uuid"]
            elif eh_platform in ("eca", "ecm"):
                uuid_raw = extrahop.get("appliances/0").json()["uuid"].split("-")[1:]
                uuid = "".join(uuid_raw)
            if uuid:
                kvc_service.insert(kvc_applianceuuid_name, {"_key": hostname, "uuid": uuid})
        # helper.log_debug(f"found kv, key={key}, value={kv_data}")
        except Exception as exn:
            helper.log_error(
                f"{stanza_name}:: Could not lookup appliance UUID for hostname {hostname}, reason = {exn}"
            )

    # everything should be set up and ready for metrics processing at this point
    helper.log_debug(f"{stanza_name}:: read checkpoint time = {checkpoint_time}")
    helper.log_debug(
        f"{stanza_name}:: This run should cover the following interval: {collection_start_time} - {collection_end_time}"
    )
    starttime = time.time()
    helper.log_info(f"Starting data collection for input {stanza_name}.")
    try:
        starttime = time.time()
        object_ids = [int(id) for id in object_ids]
        collect(object_ids, collection_start_time, collection_end_time)

        # save checkpoint on completing all oids for this time period
        helper.save_check_point(stanza_name, collection_end_time)
        helper.log_debug(f"{stanza_name}:: checkpointed endtime: {collection_end_time}")

        total_seconds = round(time.time() - starttime, 2)
        helper.log_info(
            f"{stanza_name}:: Data collection was completed successfully. "
            f"Total time taken: {total_seconds} seconds"
        )
    except Exception as exn:
        # Check for Invalid Object ID
        if "invalid node id" in str(exn):
            helper.log_error("{}:: Invalid Object Id found from the input. Please verify.".format(stanza_name))

        # Check for Invalid Metric Name or Matric Category
        elif "Provided spec name or category is incorrect" in str(exn):
            helper.log_error(
                "{}:: Invalid Metric Category or Metric Name found from the input. Please verify."
                .format(stanza_name)
            )

        else:
            helper.log_error(f"{stanza_name}:: Something went wrong while collecting the data. Exception : {exn}")
        helper.log_info(
            f"{stanza_name}:: Data collection was not completed successfully. Kindly check input configurations."
        )

    # finally, go through the object data lookup set
    # and save IP addresses, etc for all unknown devices
    # to the TA_extrahop_oiddev KV Store
    for ehobject in ehobject_lookup_set:
        try:
            object_endpoint = f"{ehobject.object_type.replace('_','')}s"

            raw_object_data = extrahop.get(f"{object_endpoint}/{ehobject.oid}").json()
        except Exception as exn:
            helper.log_debug(
                f"{stanza_name}:: could not query ExtraHop for data on object {ehobject}: {exn}"
            )
        else:
            kvc_object_data = {}
            kvc_object_data["oid"] = ehobject.oid
            kvc_object_data["otype"] = ehobject.object_type
            kvc_object_data["hostname"] = ehobject.hostname
            kvc_object_data["discovery_id"] = raw_object_data.get("discovery_id", "")
            # set the display name using the first matching key
            all_display_name_keys = ["display_name", "dns_name", "default_name", "name"]
            object_display_name_keys = [
                key for key in all_display_name_keys if key in raw_object_data
            ]
            kvc_object_data["display_name"] = (
                raw_object_data.get(object_display_name_keys[0])
                if len(object_display_name_keys) > 0
                else ""
            )
            kvc_object_data["_key"] = ":".join(ehobject)
            if ehobject.object_type == "device":
                kvc_object_data["macaddr"] = raw_object_data.get("macaddr", "")
                kvc_object_data["ipaddr4"] = raw_object_data.get("ipaddr4", "")
                kvc_object_data["ipaddr6"] = raw_object_data.get("ipaddr6", "")
            else:
                # need to write blank entries for non-devices
                # else Splunk may ignore these fields for ALL records
                kvc_object_data["macaddr"] = ""
                kvc_object_data["ipaddr4"] = ""
                kvc_object_data["ipaddr6"] = ""
            try:
                kvc_service.insert(kvc_oiddev_name, kvc_object_data)
            except Exception as exn:
                helper.log_debug(
                    f"{stanza_name}:: could not insert data for object {ehobject} into lookup table "
                    f"{kvc_oiddev_name}: {exn}"
                )

    helper.log_debug(f"{stanza_name}:: collect_events method end")
