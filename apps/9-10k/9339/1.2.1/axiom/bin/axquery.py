#!/usr/bin/env python
# coding=utf-8
#
import os
import sys
import json
import requests
from time import sleep
import re
from datetime import datetime
from typing import List

# Splunk Libraries
import splunk.mining.dcutils as dcu
# add splunklib to lib path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    dispatch, GeneratingCommand, Configuration, Option, validators
)
import splunklib.client as client

from axiom_common import (
    AxiomCommandRuntimeMixin,
    AplPipeline,
    AxiomResponseMapper,
    TimeRangeResolver,
    dict_to_log_kv_str,
    dict_to_kv_str,
    flatten_dict,
)

# initialise logger
logger = dcu.getLogger()
logger.setLevel('INFO')

@Configuration(type='events', retainsevents=True, streaming=False)
class Axiom(AxiomCommandRuntimeMixin, GeneratingCommand):
    """
    The axquery command accepts an APL query, tokenName, and optional args such as
    startTime, endTime, earliest, latest, debug, and paginate, then queries Axiom
    and returns the results within Splunk.

    Example:

    ``| axquery apl="myindex | field=\"value_with_escaped_doublequotes\"" [ startTime="2024-09-28T10:00:00Z" ] [ endTime="2024-09-29T12:00:00Z" ]``

    If no explicit time options are provided, axquery uses the Splunk search
    dispatch time range when Splunk provides one. Non-positive dispatch values
    such as Splunk's all-time sentinel are treated as unbounded and omitted from
    the Axiom API request.

    Returns the data from Axiom as Splunk results.

    The streams pipeline generates or processes time-ordered event records on an indexer or search head.
    The events pipeline generates or processes records on a search head.
    The reports pipeline also runs on a search head, but yields data structures for presentation, not event records.
    """

    command_name = "axquery"
        
    TIME_PATTERN1 = re.compile(
       r'^'
        r'\d{4}-\d{2}-\d{2}T'
        r'\d{2}:\d{2}:\d{2}'
        r'(?:\.\d{3,9})?Z'
        r'$'
    )

    TIME_PATTERN2 = re.compile(r"""
        ^(?:
            [-+]
            (?:\d+)?
            (?:yrs|yr|years|year|y|weeks|week|w|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)
            (?:
                @(?:yrs|yr|years|year|y|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)$
                |@(?:weeks|week|w)(?:[0-7])?$
                |$
            )
            |
            (?:
                @(?:yrs|yr|years|year|y|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)$
                |@(?:weeks|week|w)(?:[0-7])?$
                |$
            )
        )
    """, re.VERBOSE)
    
    RFC3339_RE = re.compile(
        r'^(\d{4})-(\d{2})-(\d{2})T'
        r'(\d{2}):(\d{2}):(\d{2})'
        r'(?:\.(\d{1,9}))?'
        r'(Z|[+-]\d{2}:\d{2})$'
    )

    def __init__(self):
        """Initialise the Axiom command, setting up a unique job ID, HTTP session, and signal handlers."""
        super(Axiom, self).__init__()
        self.initialize_runtime()


    # Define the command options (arguments)
    apl = Option(
        doc='''
        **Syntax:** apl=<string>
        **Description:** Required argument. This field should contain your APL query.
        NOTE1: double quotes within the string should be escaped or use single quotes
        NOTE2: datasets may need to have square brackets surrounding them, if for example
                the dataset name contains a '.' or '-'.
        EXAMPLE: the APL search:
            "['my_dataset'] | where name == "Fred"",
        should be expressed as:
            apl="['my_dataset'] | where name == \"Fred\"",
            or
            apl="my_dataset | where name == 'Fred'"
        ''',
        require=True,  # apl is required
        validate=validators.Match("apl", r'.*')  # Accept any string for apl
    )

    tokenName = Option(
        doc='''
        **Syntax:** tokenName=<string>
        **Description:** Optional argument. This field should contain the name for the Axiom API key.
        **Default:** Default is no option given. To make it easier, if you call your token axiom_token, you will not need to specify this argument.''',
        require=False,  # tokenName is optional
        default="axiom_token",  # Default value is "axiom_token"
        validate=validators.Match("tokenName", r'.*')  # Accept any string for token
    )

    startTime = Option(
        doc='''
        **Syntax:** startTime=<string>
        **Description:** Optional argument. This is the Axiom query start time in RFC3339 UTC format ("%Y-%m-%dT%H:%M:%SZ") or supported relative time. Overrides the Splunk dispatch earliest time.''',
        require=False,  # startTime is optional
    )
    
    endTime = Option(
        doc='''
        **Syntax:** endTime=<string>
        **Description:** Optional argument. This is the Axiom query end time in RFC3339 UTC format ("%Y-%m-%dT%H:%M:%SZ") or supported relative time. Overrides the Splunk dispatch latest time.''',
        require=False,  # endTime is optional
    )

    earliest = Option(
        doc='''
        **Syntax:** earliest=<string>
        **Description:** Optional Splunk-style alias for startTime. If neither startTime nor earliest is provided, the Splunk search dispatch earliest time is used when available.''',
        require=False,
    )

    latest = Option(
        doc='''
        **Syntax:** latest=<string>
        **Description:** Optional Splunk-style alias for endTime. If neither endTime nor latest is provided, the Splunk search dispatch latest time is used when available.''',
        require=False,
    )

    paginate = Option(
        doc='''
        **Syntax:** paginate=<cursor|time>
        **Description:** Optional argument. Axiom will limit results to 50000 without pagination.
            This option instructs Axiom to paginate through results. 
        **Options:**
            time - will use the _time and _sysTime as a primary key and hashing of entire event to remove duplicates
            cursor - will use minCursor and maxCursor to select next page of results.
            NOTE: For either pagination to work, the search MUST be sorted by _time, optionally asc or desc (defaults desc).
        ''',
        require=False,  # paginate is optional
        default=None,   # default to None for testing var later
        validate=validators.Match("paginate", r'^["\']*(cursor|time)["\']*$')
    )

    mgmtPort = Option(
        doc='''
        **Syntax:** mgmtPort=<integer>
        **Description:** Optional argument. Instructs this instance which management port Splunk is running on
        **Default:** 8089
        ''',
        require=False,
        default=None,
        validate=validators.Integer()   # check argument is an integer
    )
    
    maxTime = Option(
        doc='''
        **Syntax:** maxTime=<integer>
        **Description:** Optional argument. Defines the maxtime in seconds that this script can run to prevent infinty
        **Default:** 600
        ''',
        require=False,  # debug is optional
        default=600,  # Default value is 600 secs (10 minutes)
        validate=validators.Integer()  # Validate that the input is True or False
    )

    debug = Option(
        doc='''
        **Syntax:** debug=<True|False>
        **Description:** Optional argument. Enable or disable debug mode.
        Will accept the following Boolean responses:
            truth_values = {
                '1': True, '0': False,
                't': True, 'f': False,
                'true': True, 'false': False,
                'y': True, 'n': False,
                'yes': True, 'no': False
            }''',
        require=False,  # debug is optional
        default=False,  # Default value is False
        validate=validators.Boolean()  # Validate that the input is True or False
    )
    
    def validate_time_args(self, timestring: str, arg_name: str) -> str:
        """Validate and normalise a time argument to an RFC3339 UTC string.

        Accepts either a UTC RFC3339 timestamp (YYYY-MM-DDTHH:MM:SSZ) or a relative
        time expression (e.g. '-7d@d', '+2h', '@mon'). Relative times are resolved to
        absolute RFC3339 strings. Raises ValueError for unrecognised formats.
        """
        return TimeRangeResolver.validate_time_arg(timestring, arg_name)

    def flatten(self, dictionary, parent_key='', separator='.'):
        """Recursively flatten a nested dictionary, joining keys with a separator.

        Nested dict keys are joined with `separator` (default '.').
        List values are flattened using their integer index as part of the key.
        Returns a flat dict of {compound_key: leaf_value} pairs.
        """
        return flatten_dict(dictionary, parent_key=parent_key, separator=separator)

    def dict_to_kv_str(self, d):
        """Convert a dictionary to a comma-separated 'key=value' string for logging."""
        return dict_to_kv_str(d)

    def dict_to_log_kv_str(self, d):
        """Convert a dictionary to Splunk-friendly comma-separated log fields."""
        return dict_to_log_kv_str(d)

    def merge_two_dicts(self, x, y):
        """Return a new dict containing all key/value pairs from x, updated with those from y."""
        z = x.copy()   # start with keys and values of x
        z.update(y)    # modifies z with keys and values of y
        return z


    def get_cursor_as_integer(self, c):
        """Extract and return the numeric segment of an Axiom cursor string as an integer."""
        return int(c.split("-")[2], 16)

    def get_status_data(self, r):
        """Extract and flatten the 'status' block from an Axiom API response dict.

        Returns a flat dict with keys prefixed 'status.', or None if the block is absent.
        """
        return AxiomResponseMapper.get_status_data(r)
    
    def get_header_data(self, r):
        """Flatten HTTP response headers into a dict with keys prefixed 'resp_headers.'."""
        return AxiomResponseMapper.get_header_data(r)

    def get_query_data(self, r):
        """Return the last table from an Axiom API response dict.

        Simple queries return a single table; 'summarize' queries may return two (raw
        and aggregated). Taking the last table always yields the primary result set.
        Returns None if no tables are present.
        """
        return AxiomResponseMapper.get_query_data(r)

    def split_apl_pipeline(self, query: str) -> List[str]:
        """
        Split an APL query into pipeline stages on `|` operators,
        while ignoring `|` characters that appear inside:
        - double-quoted strings: "..."
        - single-quoted strings: '...'
        - line comments: // ...
        - block comments: /* ... */
        Empty segments (e.g. from leading/trailing or repeated `|`) are dropped.
        """
        return AplPipeline.split(query)

    def get_sort_direction(self, apl):
        """Parse the APL query and return its sort direction ('asc' or 'desc').

        When pagination is used the query must contain '| sort by _time', optionally
        followed by 'asc' or 'desc'. Defaults to 'desc' if no direction is specified.
        Raises ValueError if the required sort stage is missing or duplicated.
        """

        sort_direction = AplPipeline.get_sort_direction(apl)
        logger.debug(f"{self.log_prefix()}, sort_direction={sort_direction}")
        return sort_direction
        

    def get_or_set_limit(self, apl, paging, page_size, event_limit):
        """ 
        DEFAULT BEHAVIOUR
            ** If not using pagination,
                * If limit option is not supplied, Axiom will return 1000 results
                * If limit option is supplied, limit defines number of results to return (as expected)
                  but since the maximum page size in Axiom is 50,000, a max. of 50,000 results will be returned.
            ** If using pagination,
                * If limit option is not supplied, Axiom will return 1000 results
                * If limit option is supplied, limit flips to becoming the "page_size", 
                  NOT number of results to return (as would be expected)
        THIS SCRIPTS CHANGES THE DEFAULT BEHAVIOUR IN THIS WAY
            ** If using pagination,
                * If limit option is supplied, limit is artificially made to mimick the behaviour
                  of limit without pagination, and page_size is set to 50,000, unless page_size is
                  greater than limit, in which case page_size is set to limit (number of events to return)
        """
        return AplPipeline.get_or_set_limit(apl, paging, page_size, event_limit)

    def get_column_headings(self, d):
        """Return the ordered list of field names from a query data table."""
        return AxiomResponseMapper.get_column_headings(d)

    def get_columns(self, d):
        """Return the columnar data arrays from a query data table, or None if absent."""
        return AxiomResponseMapper.get_columns(d)

    def rfc3339_to_ns(self, ts: str) -> int:
        """Parse an RFC3339 timestamp and return it as integer nanoseconds since the Unix epoch.

        Handles UTC ('Z') and explicit timezone offsets (±HH:MM). Fractional seconds
        up to nanosecond precision (9 digits) are preserved. Integer arithmetic is used
        throughout to avoid floating-point rounding at sub-microsecond resolution.
        Raises ValueError if the timestamp does not match the expected format.
        """

        return TimeRangeResolver.rfc3339_to_ns(ts)

    def ns_to_rfc3339(self, ns: int) -> str:
        """Convert an integer nanosecond epoch timestamp to an RFC3339 UTC string with nanosecond precision."""
        return TimeRangeResolver.ns_to_rfc3339(ns)
    
    
    def get_formatted_duration(self, s, e):
        """Return a human-readable duration string (e.g. '0d 00h 01m 23.456s') for the interval between two datetimes."""
        duration = e - s
        days = duration.days
        seconds = duration.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        millisecs = duration.microseconds // 1000
        formatted_str = f"{days}d {hours:02}h {minutes:02}m {seconds:02}.{millisecs}s"
        return formatted_str

        
    def get_next_cursor(self, data, sort_dir):
        """Return the next pagination cursor from status data based on sort direction.

        Uses maxCursor for ascending sort and minCursor for descending. Returns False
        if no matching cursor is found or the sort direction is unrecognised.
        """
        if sort_dir == "asc":
            c_name = 'status.maxCursor'
        elif sort_dir == "desc":
            c_name = 'status.minCursor'
        else:
            return False
        
        if c_name in data:
            #logger.debug(f"jobId={self.job_id}, sort_direction={sort_dir}, next_cursor={data[c_name]}")
            return data[c_name]        
        return False

    def manage_rate_limit(self, api_response, page_size, start, event_limit, rows_received_so_far):
        """
        Manages the API rate limit and introduces a delay if necessary.
        """
        # variables
        elapsed_time_secs = max(0, round(datetime.now().timestamp() - start.timestamp()))
        remaining_records = max(0, event_limit - rows_received_so_far)

        # Calculate the estimated number of remaining API calls (Ceiling division)
        estimated_remaining_calls = -(-remaining_records // page_size) if page_size > 0 else 0
        calls_so_far = max(rows_received_so_far / page_size, 1) if page_size > 0 else 1
        average_interval_per_request = elapsed_time_secs / calls_so_far

        rate_limit_remaining = int(api_response.headers.get('X-Ratelimit-Remaining', 1000))
        SECONDS_IN_MINUTE = 60
        remaining_time_in_window = SECONDS_IN_MINUTE - (elapsed_time_secs % SECONDS_IN_MINUTE)

        # Calculate required delay to stay within rate limit
        estimated_delay = 0
        # If close to the rate limit, introduce a delay
        if rate_limit_remaining <= 0 and estimated_remaining_calls > 0:
            estimated_delay = remaining_time_in_window
            sleep(estimated_delay)
        elif 0 < rate_limit_remaining < estimated_remaining_calls:
            estimated_delay = max(
                remaining_time_in_window / max(rate_limit_remaining, 1),
                average_interval_per_request,
            )
            sleep(estimated_delay)

        logger.debug(
            f"{self.log_prefix()}, event_limit={event_limit}, page_size={page_size}, "
            f"rows_received_so_far={rows_received_so_far}, remaining_records={remaining_records}, "
            f"rate_limit_remaining={rate_limit_remaining}, estimated_remaining_calls={estimated_remaining_calls}, "
            f"elapsed_time_secs={elapsed_time_secs}, secs_until_Xrate_limit_reset={remaining_time_in_window}, "
            f"delay={estimated_delay}"
        )
        return

    def generate(self):
        """Execute the APL query against Axiom and yield events to Splunk.

        Resolves time arguments, retrieves the API token, and issues paginated or
        single-page requests to the Axiom APL endpoint. Each result row is yielded
        as a Splunk event dict wrapped with host, source, and sourcetype metadata,
        with _time converted from RFC3339 nanoseconds to epoch microseconds.

        Supports two pagination modes:
          - 'cursor': uses minCursor/maxCursor from the API response status block.
          - 'time':   uses the last event's _time as the next page boundary, with
                      MD5-based duplicate detection for events sharing the same timestamp.

        Terminates early if the event limit, maxTime, or a signal (SIGTERM/SIGHUP/SIGINT)
        is received.
        """
        start = datetime.now()          # when we begin this job
        first_time = True               # true for first time through loop
        next_cursor = False             # next cursor for pagination
        keep_going = True               # should we keep looping
        page = 0                        # keeps a count of pages that we requested
        page_size = 50_000              # get pages of 50,000 results (maximum set by Axiom)
        sort_dir = "n/a"                # default sort direction is "n/a"
        event_limit = 1_000_000         # set nominal value for number of events to be returned if paginating (1000 if not paginating)
        event_count = 0                 # count of events received
        rows_received_so_far = 0        # number of records so far
        est_num_pages = 20              # set nominal figure for estimated pages (event_limit / page_size)
        elapsed_seconds = 0             # time this script has been running
        last_time_ns = 0                # event '_time' from last event we processed in nanoseconds
        hashes_for_this_time = set()       # a set of event hashes for this _time if using pagination
        events_matched = 0               # number of events Axiom matched on initial query.
        
        # turn on debug-level logging
        if self.debug:
            logger.setLevel('DEBUG')
            logger.debug(
                f"{self.log_prefix()}, event=query_start, instanceEvent=BEGIN, "
                f"instance_st={round(start.timestamp(),3)}, "
                f"instance_st_iso={start.isoformat()}, apl={json.dumps(self.apl)}, paginate={self.paginate}"
            )
    
        self.startTime, self.endTime = self.resolve_query_time_range()
        logger.debug(
            f"{self.log_prefix()}, resolved_startTime={self.startTime}, resolved_endTime={self.endTime}"
        )

        if not self.mgmtPort:
            self.mgmtPort = self.get_mgmt_port()

        axiom_token = self.get_axiom_token()    # get the Axiom API token from Splunk cred store.
        
        (self.apl, event_limit, page_size) = self.get_or_set_limit(self.apl, self.paginate, page_size, event_limit)
        logger.debug(f"{self.log_prefix()}, apl={json.dumps(self.apl)}, event_limit={event_limit}, page_size={page_size}")

        if self.paginate:
            sort_dir = self.get_sort_direction(self.apl)

        while keep_going:
            # exit if Splunk is trying to finalize job!
            if self.exit_requested:  # Check termination conditions
                break

            page += 1
            skipped_dups = 0 # number of duplicate events skipped while time-based paginating
            
            api_response = self.post_to_axiom(self.apl, self.startTime, self.endTime, axiom_token, next_cursor)
            resp_json = api_response.json()
            
            query_data = self.get_query_data(resp_json)
            #logger.debug(f'jobId={self.job_id}, DATA: {query_data}')                     # uncomment to debug response data before processing

            column_headings = self.get_column_headings(query_data)
            #logger.debug(f'jobId={self.job_id}, column_headings={column_headings}')      # uncomment to debug field names before processing
            columns = self.get_columns(query_data) or []
            #logger.debug(f'jobId={self.job_id}, columns: {columns}')                     # uncomment to debug field values before processing
            num_cols = len(column_headings)
            
            # get number of records received in this call
            if not columns:
                num_rows = 0
            else:
                num_rows = len(columns[0])
                
            rows_received_so_far += num_rows     # get the total num of records received so far
            logger.debug(f'{self.log_prefix()}, num_cols={num_cols}, num_rows={num_rows}, rows_received_so_far={rows_received_so_far}')
            
            if num_rows == 0:
                # prevents infinite loop where we call api and receive a response with no records but cursor is still valid.
                logger.debug(f'{self.log_prefix()}, num_rows={num_rows}, no_more_data=true')
                keep_going = False

            status_data = self.get_status_data(resp_json) or {}
            resp_header = self.get_header_data(api_response.headers) or {}

            if first_time:
                first_time = False
                events_matched = status_data.get('status.rowsMatched', event_limit)
                est_num_pages = -(-event_limit // page_size ) # ceiling division

            # for each row (event), and for each column (fieldname) get this event's fieldname=value pairs
            for row_values in zip(*columns):  # each row_values is tuple of length num_cols
                
                this_event = dict(zip(column_headings, row_values))

                if '_time' in this_event:
                    # convert a rfc3339 ts to epoch nanoseconds for hashing
                    this_event_ns = self.rfc3339_to_ns(this_event['_time'])

                    if self.paginate == 'time':
                        if this_event_ns == last_time_ns:
                            # _time matches last event, need to check for duplicate event.
                            if 'axiom_hash' in this_event:
                                this_hash = this_event['axiom_hash']
                                if this_hash in hashes_for_this_time:
                                    # we have already seen this event.
                                    skipped_dups += 1
                                    logger.debug(
                                        f"{self.log_prefix()}, duplicate_event_skipped=true, "
                                        f"axiom_hash={this_hash}, event_time={this_event['_time']}"
                                    )
                                    continue
                                else:
                                    hashes_for_this_time.add(this_hash)
                            else:
                                raise ValueError(f"{self.log_prefix()}, when pagination is set to 'time', every event should have a hash field called 'axiom_hash', check apl: {self.apl}")
                        else:
                            last_time_ns = this_event_ns     # record new _time
                            hashes_for_this_time = set()
                            if 'axiom_hash' in this_event:
                                hashes_for_this_time.add(this_event['axiom_hash'])

                if self.debug:
                    this_event = self.merge_two_dicts(this_event, {
                        "apl": self.apl,
                        "startTime": self.startTime,
                        "endTime": self.endTime
                    })
                else:
                    if self.paginate == "time":
                        # drop helper hash if present.
                        this_event.pop('axiom_hash', None)
                
                # emit the row's keys as real Splunk fields so callers do not need
                # to append '| spath', keeping _raw for the Events tab.
                yield AxiomResponseMapper.row_to_splunk_event(this_event)
                event_count += 1

                if event_count == event_limit:
                    break

            elapsed_seconds = int((datetime.now() - start).total_seconds())
            
            if self.paginate == 'cursor':
                next_cursor = self.get_next_cursor(status_data, sort_dir)
                self.manage_rate_limit(api_response, page_size, start, event_limit, rows_received_so_far)
                if not next_cursor:
                    keep_going = False
                #logger.debug(f"jobId={self.job_id}, event_count={event_count}, rows_received_so_far={rows_received_so_far}")
            elif self.paginate == 'time':
                if sort_dir == 'asc':
                    # Use last time we processed as next page's timestamp, and use as 'startTime'
                    self.startTime = self.ns_to_rfc3339(last_time_ns)   # convert back to rfc3339
                    logger.debug(f"{self.log_prefix()}, page={page}, last_event_time={self.ns_to_rfc3339(last_time_ns)}, next_startTime={self.startTime}")
                else:
                    # Use last time we processed as next page's timestamp, and use as 'endTime'
                    self.endTime = self.ns_to_rfc3339(last_time_ns)   # convert back to rfc3339
                    logger.debug(f"{self.log_prefix()}, page={page}, last_event_time={self.ns_to_rfc3339(last_time_ns)}, next_endTime={self.endTime}")
            else:
                keep_going = False

            if event_count >= events_matched or event_count >= event_limit or elapsed_seconds >= self.maxTime:
                keep_going = False
            
            logger.debug(f"{self.log_prefix()}, event=query_page, page={page}, est_pages={est_num_pages}, elapsed_seconds={elapsed_seconds}, next_cursor={next_cursor}, keep_going={keep_going}, num_cols={num_cols}, num_rows={num_rows}, initial_events_matched={events_matched}, sub_total_results={event_count}, event_limit={event_limit}, skipped_dups={skipped_dups}, {self.dict_to_log_kv_str(status_data)}, {self.dict_to_log_kv_str(resp_header)}")

        end = datetime.now()
        duration_timestamp = round(end.timestamp() - start.timestamp())
        formatted_duration = self.get_formatted_duration(start, end)
        logger.info(
            f"{self.log_prefix()}, event=query_end, instanceEvent=END, "
            f"instance_st={round(start.timestamp(),3)}, instance_et={round(end.timestamp(),3)}, "
            f"paginate={self.paginate}, debug={self.debug}, "
            f'duration_formatted="{formatted_duration}", duration={duration_timestamp}'
        )


if __name__ == "__main__":
    # Dispatch the command to Splunk
    dispatch(Axiom, sys.argv, sys.stdin, sys.stdout, __name__)
    
