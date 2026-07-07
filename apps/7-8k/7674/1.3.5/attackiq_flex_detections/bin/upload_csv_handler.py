import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from splunk.persistconn.application import PersistentServerConnectionApplication


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.custom_splunk_endpoint_base import CustomSplunkEndpointBase
from libs.base_objects.splunk_command_base import SplunkCommandBaseMixin
from libs.base_objects.table_structures import Ioc, PackageRun, Prevention
from libs.constants import (
    FLEX_INDEX,
    SOURCE_TYPE_IOCS,
    SOURCE_TYPE_PACKAGE_RUNS,
    SOURCE_TYPE_PREVENTIONS,
)


class RunIdConflictException(Exception):
    pass


class UploadCSVHandler(
    SplunkCommandBaseMixin,
    CustomSplunkEndpointBase,
    PersistentServerConnectionApplication,
):
    """Handler for uploading and processing CSV content."""

    VALID_SOURCETYPES = {
        "ioc": SOURCE_TYPE_IOCS,
        "prevention": SOURCE_TYPE_PREVENTIONS,
        "package_run": SOURCE_TYPE_PACKAGE_RUNS,
    }

    def __init__(self, command_line, command_arg, logger=None):
        PersistentServerConnectionApplication.__init__(self)
        CustomSplunkEndpointBase.__init__(self)

    def process_payload(self, payload):
        """Process the payload for CSV content."""
        csv_content = self._extract_csv_content(payload.get("payload", ""))

        if csv_content:
            index = self._get_index(FLEX_INDEX)
            sourcetype = self._get_csv_sourcetype(payload)

            # Process the CSV content, create KV store entries, and index events
            try:
                rows = self._process_csv(sourcetype, index, csv_content)
            except RunIdConflictException:
                return self._create_response("File has already been uploaded.", 200)

            return self._create_response(
                f"CSV content processed successfully, added {rows} rows to index {FLEX_INDEX}",
                200,
            )
        else:
            return self._create_response("No valid CSV content found", 200)

    def _process_csv(self, sourcetype, index, csv_content):
        """Process the CSV content: add to KV Store and index events."""
        rows = 0
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                if rows == 0 and self._run_id_already_present(row, sourcetype):
                    raise RunIdConflictException
                if sourcetype == SOURCE_TYPE_PACKAGE_RUNS:
                    # Add to Package Status
                    self.add_new_package(
                        PackageRun.from_dict(**row),
                        str(int(datetime.now(timezone.utc).timestamp())),
                    )
                self._add_event_to_index(index, sourcetype, row)
                rows += 1

            self.aiq_logger.info(
                f"CSV content added to index '{FLEX_INDEX}' and sourcetype '{sourcetype}'. Rows: {rows}"
            )
        except RunIdConflictException:
            raise
        except Exception as e:
            self.aiq_logger.error(
                f"Failed to process CSV content for index '{FLEX_INDEX}' and KV Store: {e}"
            )
            raise RuntimeError(f"Failed to process CSV content: {e}")

        return rows

    def _get_csv_sourcetype(self, payload):
        """Retrieve the correct sourcetype based on query parameters."""
        query_values = payload.get("query", [])

        for query in query_values:
            if query[0] == "sourcetype":
                sourcetype = query[1]
                if sourcetype in self.VALID_SOURCETYPES:
                    return self.VALID_SOURCETYPES[sourcetype]
                else:
                    raise ValueError(f"Invalid sourcetype: {sourcetype}")

        return self.VALID_SOURCETYPES["ioc"]

    def _extract_csv_content(self, payload):
        """Extract CSV content from the payload."""

        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        match = re.search(
            r"Content-Type: text/csv[\r\n]*(.*?)[\r\n]*---[-]*[A-Za-z0-9]",
            payload,
            re.DOTALL,
        )

        if match:
            return match.group(1)

        return None

    def _get_index(self, index_name):
        """Retrieve the Splunk index."""
        try:
            index = self.splunk_service.indexes[index_name]
        except Exception as e:
            self.aiq_logger.error(f"Failed to retrieve index '{index_name}': {e}")
            raise RuntimeError(f"Failed to retrieve index '{index_name}': {e}")
        return index

    def _add_event_to_index(self, index, sourcetype, event_data):
        """Add an event to the Splunk index."""
        try:
            index.submit(json.dumps(event_data), sourcetype=sourcetype)
        except Exception as e:
            self.aiq_logger.error(f"Failed to add event to index '{FLEX_INDEX}': {e}")
            raise RuntimeError(f"Failed to add event to index '{FLEX_INDEX}': {e}")

    def _run_id_already_present(self, event_row, sourcetype):
        if sourcetype == SOURCE_TYPE_IOCS:
            run_id = Ioc.from_dict(**event_row).run_id
        elif sourcetype == SOURCE_TYPE_PACKAGE_RUNS:
            run_id = PackageRun.from_dict(**event_row).run_id
        elif sourcetype == SOURCE_TYPE_PREVENTIONS:
            run_id = Prevention.from_dict(**event_row).run_id
        try:
            query = f'search index={FLEX_INDEX} sourcetype="{SOURCE_TYPE_PACKAGE_RUNS}" | spath input=_raw path="run_id" output=run_id | where run_id="{run_id}"'
            results = self._query_splunk(query)
            return bool(results.records)
        except Exception:
            self.aiq_logger.error(
                "Failed to analyze run_id existance. Proceeding with the upload."
            )
        return False
