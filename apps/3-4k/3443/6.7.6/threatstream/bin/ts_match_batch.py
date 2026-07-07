# pylint: disable=wrong-import-position, import-error, no-self-use
"""
The file contains the custom lookup command used for matching Threatstream IOCs in Splunk KVstore
and saving them to a field
"""

import sys
import time
import json
import re
from six.moves import zip
from collections import namedtuple
from util.splunk_access import SplunkAccess

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators


class SplunkCommandMetric(object):
    """
    A class to hold the record of a splunk metric

    Arguments:
        iterations (float): number to start the invocations metric on
        seconds_elapsed (float): number to start the seconds_elpased metric on
        input_items (float): number to start the input items metrics on
        output_items (float): number to start the output items metrics on
    """

    iterations = "iterations"
    seconds_elapsed = "seconds_elapsed"
    input_items = "input_items"
    output_items = "output_items"

    metric_array = {}

    def __init__(self, iterations=None, seconds_elapsed=None, input_items=None, output_items=None):
        self.metric_array = {
            self.iterations: iterations,
            self.seconds_elapsed: seconds_elapsed,
            self.input_items: input_items,
            self.output_items: output_items
        }

    def metric_update(self, value, context):
        """
        Function used to update the metric object

        Arguments:
            value (float): the value to update the metric with. Always assumed as cumulative
            context (str): the context the value applies to

        """
        if context in [self.iterations, self.seconds_elapsed, self.input_items, self.output_items]:
            self.metric_array[context] += value

    def output_as_text(self):
        """
        Function used to output a metric as text

        Returns:
            (str): the metric as text
        """

        metric_text = "seconds_elapsed: %s, iterations: %s, input_items: %s, output_items: %s" % (
            self.metric_array[self.seconds_elapsed],
            self.metric_array[self.iterations],
            self.metric_array[self.input_items],
            self.metric_array[self.output_items]
        )

        return metric_text

    def output_as_tuple(self):
        """
        Function used to output the metric array as a tuple, order of elements is important

        Returns:
            metric_tuple (tuple): a metric tuple in the form that splunk metrics can use
        """
        SearchMetric = namedtuple('SearchMetric', ('elapsed_seconds', 'invocation_count', 'input_count', 'output_count'))

        metric_tuple = SearchMetric(
            self.metric_array[self.seconds_elapsed],
            self.metric_array[self.iterations],
            self.metric_array[self.input_items],
            self.metric_array[self.output_items]
        )
        return metric_tuple


@Configuration()
class TSMatchesCommand(EventingCommand):
    """Matches the specified fields against Anomali IOCs

       ##Syntax
       .. code-block::

       ##Description

       Matches against the Anomali Threatstream indicators stored in the Splunk KVStores.
       This command filters out events that do not match any indicators.
       The results are stored in a JSON field inside of <dest_field>.

       <dest_field> will be overwritten if it already exists or created if it does not.

       ##Example

       .. code-block::
           index=main
           | stats count by src, dest
           | ts_matches type=ip dest_field=anomali_results src, dest

       .. code-block::
           index=main
           | eval ip_decision_field = if(xxxxx,mvadd("src", decision_field),)
           | eval ip_decision_field = if(xxxxx, mvadd("dest", decision_field, )
           | ts_matches type=auto dest_field=anomali_results fieldlist_field=decision_field
    """

    # These mirror the kvstore names, this is important for matching purposes
    kv_store_is_enabled = {
        "ip": False,
        "domain": False,
        "email": False,
        "md5": False,
        "url": False,
    }

    kv_store_to_indicator_mapping = {
        "ip": "srcip",
        "domain": "domain",
        "url": "url",
        "md5": "md5",
        "email": "email"
    }

    kvstore_query_exclude_fields = [
        "_time:0",
        "_user:0",
        "_key:0",
    ]

    match_type = Option(
        default="auto",
        doc='''
    **Syntax:** **match_type=***(ip or domain or url or email or md5 or auto)*
    **Description:** The type of IOC to match on ''',
    )

    dest_field = Option(
        default="anomali_results",
        doc='''
    **Syntax:** **dest_field=***<fieldname>*
    **Description:** The field to write the matching results to''',
    )

    fieldlist_field = Option(
        default=None,
        doc='''
    **Syntax:** **fieldlist_field=***<fieldname>*
    **Description:** A multivalue field the fields to match against. 
    Has priority over trailing fieldnames''',
        validate=validators.Fieldname()
    )

    # Metrics written to the search inspector
    # { name : (elapsed_seconds, invocations, input_count, output_count)}
    metrics = {
        "overall_status": SplunkCommandMetric(
            seconds_elapsed=0,
            input_items=0,
            output_items=0
        ),
        "lookup_query": SplunkCommandMetric(
            iterations=0,
            seconds_elapsed=0,
        ),
        "lookup_cache": SplunkCommandMetric(
            seconds_elapsed=0,
            iterations=0,
            input_items=0,
            output_items=0
        ),
        "preparation_status": SplunkCommandMetric(
            seconds_elapsed=0
        ),
        "validation": SplunkCommandMetric(
            seconds_elapsed=0,
            input_items=0,
            output_items=0
        ),
        "second_event_matching": SplunkCommandMetric(
            seconds_elapsed=0
        ),
        "clean_up": SplunkCommandMetric(
            seconds_elapsed=0
        ),
        "record_processing": SplunkCommandMetric(
            seconds_elapsed=0
        ),
        "field_processing": SplunkCommandMetric(
            seconds_elapsed=0
        )

    }

    # Loads the entire KVstore indicator set into memory as a set
    pre_match_kvstore = {
        "ip": set(),
        "domain": set(),
        "url": set(),
        "md5": set(),
        "email": set()
    }

    # Used as a cache for indicator metainformation after matching happens
    kvstore_queues = {
        "ip": [],
        "domain": [],
        "url": [],
        "md5": [],
        "email": []
    }

    # The maximum size a KVstore or Event queue can be after matching occurs but before meta-information is retrieved
    ## this reflects the size the query can be in limits.conf for the kvstore, 1000 is the default
    kv_queue_max_size = 999
    kv_batch_results = dict()

    event_queue = {
        "ip": [],
        "domain": [],
        "url": [],
        "md5": [],
        "email": []
    }  # list of tuples ( splunk_event, field_type )

    ip_regex = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    domain_regex = re.compile(r'^(?!:\/\/)([a-zA-Z0-9-_]+\.)*[a-zA-Z0-9][a-zA-Z0-9-_]+\.[a-zA-Z]{2,11}?$')
    url_regex = re.compile(r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$")
    email_regex = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    def transform(self, records):
        """
        Function that does the matching, metric writing and generally all the work within the
        class

        Args:
            records (list): a list of records that have been passed by the Splunk Command Processor

        Yields:
            record (dict): transformed records to be output to Splunk
        """

        metric_prep_t0 = time.time()
        flush_count = 0

        splunkd = SplunkAccess(logger=self.logger, session_key=self.service.token)
        kvstore = splunkd.kvsm

        # Command argument validation
        # Condition 1: check that a field list has been defined
        self.validate_args()
        self.logging_level = "INFO"

        # Create the preparation phase metric
        metric_prep_time_delta = time.time() - metric_prep_t0
        self.metrics["preparation_status"].metric_update(
            int(metric_prep_time_delta),
            "seconds_elapsed"
        )
        metric_overall_t0 = time.time()
        self.logger.info("Entered event matching loop")

        for record in records:
            self.metrics["overall_status"].metric_update(1, "input_items")
            fieldnames_to_match = self.get_fieldnames(record)

            # Main Event Matching loop
            for indicator_fieldname in fieldnames_to_match:
                # If the field doesn't exist, pass to next iteration of the loop
                if indicator_fieldname not in record:
                    continue
                field_type = self.validate_field_value(record, indicator_fieldname)

                if not field_type:
                    continue

                # Load the entire Kvstore collection into the matching if it is not already there
                if not self.pre_match_kvstore[field_type] and self.kv_store_is_enabled[field_type]:
                    self.load_ioc_store_as_set(kvstore, field_type)
                indicator = record[indicator_fieldname]

                # Check whether the indicator is in the kvstore, move onto next event if not
                if not indicator in self.pre_match_kvstore[field_type]:
                    continue

                record["indicator"] = indicator
                # Add the indicator to the matching array and the event to the event_queue
                metric_sec_event_t0 = time.time()
                queue_counter = self.kvstore_match_queue_update(field_type, indicator)
                self.event_queue[field_type].append((record, indicator_fieldname))
                self.metrics["second_event_matching"].metric_update(
                    time.time() - metric_sec_event_t0,
                    "seconds_elapsed"
                )
                # If the either of our queues is greater than the max size, then match & flush
                if queue_counter >= self.kv_queue_max_size or len(self.event_queue[field_type]) >= (5 * self.kv_queue_max_size):
                    flush_count += 1
                    flush_trigger = "kvquery queue %s" % field_type if queue_counter >= self.kv_queue_max_size else "event queue"
                    self.logger.info("Flushing Queues and batch matching due to %s: flush_count %s" % (flush_trigger, flush_count))
                    self.kv_batch_results = self.kvstore_batch_find(field_type)
                    # Loop through event queue and match against the results from the KVStore
                    for splunk_event in self.event_queue[field_type]:
                        splunk_record = splunk_event[0]
                        indicator_field = splunk_event[1]
                        ioc = splunk_record[indicator_field]
                        match_in_kvstore = self.kv_batch_results.get(ioc, False)

                        # Yield the match, pass the event otherwise
                        if match_in_kvstore:
                            splunk_record[self.dest_field] = json.dumps({ioc: match_in_kvstore})
                            yield splunk_record
                        else:
                            continue

                    # Add IOCs to cache and flush queues
                    self.event_queue[field_type][:] = []
                    self.kvstore_queues[field_type][:] = []
                    self.kv_batch_results.clear()

        self.logger.info("Ended record matching Loop, performing cleanup of queues")
        # catch the last events from the loop
        # Dont care about cleanup here, cache wont help

        metric_overall_time_delta = time.time() - metric_overall_t0
        self.metrics["overall_status"].metric_update(metric_overall_time_delta, "seconds_elapsed")

        # Write the metrics to the Search Inspector at the end of the command
        for metric_to_write in self.metrics:
            self.logger.info("Metric:%s, %s" % (metric_to_write, self.metrics[metric_to_write].output_as_text()))
            self.write_metric(metric_to_write, self.metrics[metric_to_write].output_as_tuple())

        for indicator_type in self.event_queue:
            self.logger.info("flushing event queue %s:%s" % (indicator_type, len(self.event_queue[indicator_type])))
            if self.event_queue[indicator_type]:
                self.kv_batch_results = self.kvstore_batch_find(indicator_type)
                for splunk_event in self.event_queue[indicator_type]:
                    splunk_record = splunk_event[0]
                    indicator_field = splunk_event[1]
                    ioc = splunk_record[indicator_field]
                    match_in_kvstore = self.kv_batch_results.get(ioc, False)

                    if match_in_kvstore:
                        splunk_record[self.dest_field] = json.dumps({ioc: match_in_kvstore})
                        yield splunk_record
                    else:
                        continue

            self.event_queue[indicator_type][:] = []
            self.kvstore_queues[indicator_type][:] = []
            self.kv_batch_results.clear()

    def load_ioc_store_as_set(self, kvstore, ioc_type):
        """
        Fucntion used to load a KVstore into memory
        Args:
            kvstore: kvstore instance
            ioc_type: the kvstore to get
        """

        if ioc_type in self.kv_store_is_enabled and self.kv_store_is_enabled[ioc_type]:
            ioc_map_field = self.kv_store_to_indicator_mapping[ioc_type]
            ioc_collection = kvstore.get_kvs("ts_%s" % ioc_type, ioc_map_field)
            self.pre_match_kvstore[ioc_type] = set([result.get(ioc_map_field) for result in ioc_collection])
            self.logger.info("loaded collection ts_%s into command, %s iocs loaded " %
                (
                ioc_type,
                len(self.pre_match_kvstore[ioc_type]
                )))

    def validate_args(self):
        # Condition 1: Check that a field is specified
        if not (self.fieldlist_field is not None or self.fieldnames):
            error_message = "TS-05-01, msg=A field to match must be specified"
            self.logger.error(error_message)
            sys.exit(error_message)

        # Condition 2: Check that the match type is as expected
        if self.match_type not in self.kv_store_is_enabled.keys() and self.match_type != "auto":
            error_message = "TS-05-02, msg=Unsupported match type found: %s" % self.match_type
            self.logger.error(error_message)
            sys.exit(error_message)

        # To increase performance, if a KVStore collection is empty we will disable matches
        # against it. The function below enables matching against a KVStore when records are found
        # This pretty much stops the md5 collection being matched when self.match_type="auto"

        for kvstore_collection in self.kv_store_is_enabled:
            try:
                results = self.service.kvstore["ts_%s" % kvstore_collection].data.query(limit=1)
                if results:
                    self.kv_store_is_enabled[kvstore_collection] = True
                    self.logger.info(
                        "Enabling matching against Key Value store collection ts_%s" % kvstore_collection)
            except KeyError:
                self.logger.warning(
                    "TS-05-03, msg=Looks like Key Value store collection ts_%s does not exist" % kvstore_collection)

    def get_fieldnames(self, record):
        """
        Determines which fields to examine in the event for matching in the kvstore
        Args:
            record: splunk event record

        Returns:
            (list): a list of fieldnames to examine in the splunk event
        """
        # For additional filtering functionality, we will override
        # the default positional arguments to the command
        # with those found inside the fieldlist_field

        fieldnames_to_match = []
        # Condition 1: Check for multivalue field
        if "__mv_%s" % self.fieldlist_field in record:
            fieldnames_to_match = self.deserialize_mv(record["__mv_%s" % self.fieldlist_field])
        # Condition 2: Check for the field existence
        elif self.fieldlist_field in record:
            if isinstance(record.get(self.fieldlist_field), str):
                fieldnames_to_match.append(record.get(self.fieldlist_field))
            else:
                fieldnames_to_match = record.get(self.fieldlist_field)
        # Else use the positional arguments
        else:
            fieldnames_to_match = self.fieldnames

        return fieldnames_to_match

    def validate_field_value(self, record, indicator_field):
        """
        Checks the record for field indicator_field and determines whether the value can be matched in our kvstore

        Args:
            record (str): the event from splunk
            indicator_field (str): the field to validate inside the record
        Returns:
            (bool|str): False, means that we cannot match against this in our ioc kvstore else,
                str, the indicator type
        """

        metric_validation_t0 = time.time()
        self.metrics["validation"].metric_update(1, "input_items")

        # Validate that the field value can be matched on based on the match_type
        try:
            if self.match_type == "auto":
                field_type = self.validate_field_auto_match(record.get(indicator_field))
            else:
                field_type = self.validate_field_per_match_type(record.get(indicator_field))
            metric_validation_finish = time.time() - metric_validation_t0
            self.metrics["validation"].metric_update(metric_validation_finish, "seconds_elapsed")
            self.metrics["validation"].metric_update(1, "output_items")
            return field_type

        except ValueError:
            metric_validation_finish = time.time() - metric_validation_t0
            self.metrics["validation"].metric_update(metric_validation_finish, "seconds_elapsed")
            return False


    def kvstore_batch_find(self, indicator_type):
        """
        Performs a batch lookup against the KVStore

        Args:
            indicator_type (str): which type of Indicator to search KVstore for

        Returns:
            (dict): results for KVstore
        """

        metric_kvstore_t0 = time.time()
        indicator_mapping = self.kv_store_to_indicator_mapping[indicator_type]

        results = self.service.kvstore["ts_%s" % indicator_type].data.batch_find(
            *({"query": {indicator_mapping: x}} for x in self.kvstore_queues[indicator_type])
        )
        dict_to_return = dict(zip(self.kvstore_queues[indicator_type], results))

        self.metrics["lookup_query"].metric_update(len(self.kvstore_queues[indicator_type]), "iterations")
        self.metrics["lookup_query"].metric_update(time.time() - metric_kvstore_t0, "seconds_elapsed")
        # Dict comprehension to convert list of dicts to dict, working now
        return dict_to_return

    def kvstore_match_queue_update(self, indicator_type, indicator ):
        """
        Adds a query to the KVStore batch_find method

        Args:
            indicator_type: which kvstore should it be placed in
            indicator: the indicator to be searched

        Returns:
            (int): length of the queue
        """

        if indicator not in self.kvstore_queues[indicator_type]:
            self.kvstore_queues[indicator_type].append(indicator)

        return len(self.kvstore_queues[indicator_type])

    def indicator_cache_check(self, indicator, indicator_type):
        """
        Checks the KVStore cache after matching to determine if the indicator has already been searched for
        Args:
            indicator (str): the indicator to check the cache for
            indicator_type (str): the type of indicator ( ip, domain, url, md5, email )

        Returns:
            indicator_metadata (dict): the indicator metadata ready for formatting as JSON
        """
        metric_caching_t0 = time.time()
        if indicator in self.kvstore_query_cache[indicator_type]:
            metric_caching_finish = time.time() - metric_caching_t0
            self.metrics["lookup_cache"].metric_update(metric_caching_finish, "seconds_elapsed")
            self.metrics["lookup_cache"].metric_update(1, "iterations")
            self.info.logger("cache_hit")
            return {indicator: self.kvstore_query_cache[indicator_type][indicator]}

        else:
            metric_caching_finish = time.time() - metric_caching_t0
            self.metrics["lookup_cache"].metric_update(metric_caching_finish, "seconds_elapsed")
            return None

    def validate_field_auto_match(self, field_value):
        """
        This function validates the field value can be matched against the IOC kvstores and then
        returns the appropriate type of IOC that could be matched

        Args:
            field_value (str): the field value to validate

        Returns:
            ioc_type (str): what type of IOC is the field value

        Raises:
            ValueError: On inability to validate the field value
        """

        if self.ip_regex.match(field_value) and self.kv_store_is_enabled["ip"]:
            field_type = "ip"
        elif self.domain_regex.match(field_value) and self.kv_store_is_enabled["domain"]:
            field_type = "domain"
        elif self.email_regex.match(field_value) and self.kv_store_is_enabled["email"]:
            field_type = "email"
        elif self.url_regex.match(field_value) and self.kv_store_is_enabled['url']:
            field_type = "url"
        elif self.kv_store_is_enabled['md5']:
            field_type = "md5"
        else:
            raise ValueError

        return field_type

    def validate_field_per_match_type(self, field_value):
        """
        This function validates the field value can be matched against the IOC kvstores and then
        returns the appropriate type of IOC that could be matched

        Args:
            field_value (str): the field value to validate

        Returns:
            ioc_type (str): what type of IOC is the field value

        Raises:
            ValueError: On inability to validate the field value
        """

        field_type = None

        if self.match_type == "ip" and self.kv_store_is_enabled["ip"]:
            if self.ip_regex.match(field_value):
                field_type = "ip"
        elif self.match_type == "domain" and self.kv_store_is_enabled["domain"]:
            if self.domain_regex.match(field_value):
                field_type = "domain"
        elif self.match_type == "email" and self.kv_store_is_enabled["email"]:
            if self.email_regex.match(field_value):
                field_type = "email"
        elif self.match_type == "url" and self.kv_store_is_enabled["url"]:
            if self.url_regex.match(field_value):
                field_type = "url"
        elif self.match_type == "md5" and self.kv_store_is_enabled["md5"]:
            field_type = "md5"

        if field_type:
            return field_type
        else:
            raise ValueError

    def deserialize_multi_value_field(self, multivalue_field):
        """
        This function de-serializes the Splunk Multivalue field format as described here
        https://docs.splunk.com/DocumentationStatic/PythonSDK/1.3.0/searchcommands.html
        - Design Notes (8)


        Args:
            multivalue_field (str): field to deserialize

        Returns
            field_list (list): a list of values within the multivalue field
        """
        mv_field_list = multivalue_field.split(";")

        field_list = ()
        for mv_fieldname in mv_field_list:
            field_name = mv_fieldname.strip("$")
            field_name = field_name.replace("$$", "$")
            mv_field_list.append(field_name)

        return field_list


dispatch(TSMatchesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
