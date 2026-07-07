#!/usr/bin/env python
import sys
import json
from vendor.splunklib.searchcommands import (
    StreamingCommand,
    dispatch,
    Configuration,
    Option,
)


@Configuration(local=True)
class MergeJsonRowsCommand(StreamingCommand):
    """
    Merges multiple JSON rows into a single JSON object.

    ##Syntax
    | mergejson json_field=<field_name>

    ##Description
    Takes JSON content from multiple rows and merges them into a single JSON object.

    ##Example
    | mergejson json_field="my_field"
    """

    # Define command parameters
    json_field = Option(
        doc="""
        **Syntax:** **json_field=***<fieldname>*
        **Description:** The field which we are expecting to merge JSON.
        """,
        require=False,
        default="content",
    )

    def stream(self, records):
        """Stream command implementation."""
        field = self.json_field
        merged_data = {}

        # Process each record and merge JSON data
        for record in records:
            try:
                content = json.loads(record.get(field, "{}"))
                merged_data.update(content)
            except Exception:
                self.logger.error(record)

        # Output the merged result as a single record
        yield {"content": json.dumps(merged_data)}


dispatch(MergeJsonRowsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
