#!/usr/bin/env python


import sys
from collections import OrderedDict
from datetime import datetime
from splunklib.searchcommands import dispatch, Configuration
from utils.scanner_base_command import ScannerBaseCommand
from typing import Any, Dict, List


@Configuration(type='reporting', distributed=False)
class ScannerTableCommand(ScannerBaseCommand):
    def create_splunk_row(
        self,
        _query_latest_datetime: datetime,
        scanner_column_ordering: List[str],
        scanner_row: Dict[str, Any],
        _scanner_row_idx: int,
    ) -> Dict[str, Any]:
        """
        Render the Scanner row as a table row in Splunk. Sort the columns by
        their position in scanner_column_ordering so we can try to get Splunk
        to render the columns in the right order.
        """
        def scanner_column_ordering_index(key: str) -> int:
            try:
                return scanner_column_ordering.index(key)
            except ValueError:
                return -1
        columns: Dict[str, Any] = scanner_row.get('columns', {})
        keys: list[str] = list(columns.keys())
        keys.sort(key=scanner_column_ordering_index)
        ordered_columns: OrderedDict = OrderedDict()
        key: str
        for key in keys:
            ordered_columns[key] = columns[key]
        return ordered_columns


dispatch(ScannerTableCommand, sys.argv, sys.stdin, sys.stdout, __name__)
