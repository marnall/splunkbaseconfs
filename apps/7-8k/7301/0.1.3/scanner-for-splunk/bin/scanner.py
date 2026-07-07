#!/usr/bin/env python


import json, sys
from datetime import datetime, timedelta
from splunklib.searchcommands import dispatch, Configuration
from typing import Any, Dict, List, Union
from typing_extensions import TypedDict
from utils.scanner_base_command import ScannerBaseCommand

LogEventId = TypedDict('LogEventId', {'t': str, 's': str})


@Configuration(type='events', distributed=False)
class ScannerCommand(ScannerBaseCommand):
    def create_splunk_row(
        self,
        query_latest_datetime: datetime,
        _scanner_column_ordering: List[str],
        scanner_row: Dict[str, Any],
        scanner_row_idx: int,
    ) -> Dict[str, Any]:
        """ Render the Scanner row as a log event. Add _raw and _time fields. """
        event: Dict[str, Any] = scanner_row.get('columns', {})
        row_id: Union[LogEventId, int] = scanner_row.get('row_id', {})
        raw: str = json.dumps(event)
        time: float = ScannerCommand._compute_timestamp(row_id, scanner_row_idx, query_latest_datetime) # pyright: ignore [reportAttributeAccessIssue]
        event['_raw'] = raw
        event['_time'] = time
        return event

    @staticmethod
    def _compute_timestamp(
        row_id: Union[LogEventId, int],
        scanner_row_idx: int,
        query_latest_datetime: datetime,
    ) -> float:
        """ Compute the timestamp for a log event. """
        if isinstance(row_id, dict):
            # If the row_id is a dictionary, this is a log event. Compute the
            # timestamp from the timestamp_nanos field.
            timestamp_nanos_str: str | None = row_id.get('t')
            if timestamp_nanos_str:
                return int(timestamp_nanos_str) / 1000000000
            else:
                return 0
        else:
            # If the row_id is an integer, this is a table. We will create an
            # artificial timestamp for each row. This ensures that the rows are
            # rendered in the same order they arrived from the Scanner API.
            artificial_date_time: datetime = query_latest_datetime - timedelta(milliseconds=scanner_row_idx)
            return artificial_date_time.timestamp()


dispatch(ScannerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
