"""Unified modular input for Catalyst Center Inventory and Compliance Reports."""

import import_declare_test  # noqa: F401
import io
import csv
import json
import sys
import time
from typing import Dict, List

import cisco_dnac_api as api
import consts
import logger_manager
from splunklib import modularinput as smi
import utils


def extract_filename_from_content_disposition(content_disposition: str):
    """Extract filename from content-disposition header.

    Args:
        content_disposition: Content-disposition header value

    Returns:
        Filename if found, None otherwise
    """
    if not content_disposition:
        return None

    cd_lower = content_disposition.lower()
    if "filename=" not in cd_lower:
        return None

    try:
        # Extract substring after filename=
        # Handle both filename="foo.csv" and filename=foo.csv
        after = content_disposition.split("filename=", 1)[1].strip()
        if after.startswith('"') or after.startswith("'"):
            quote = after[0]
            filename = after.split(quote, 2)[1]
        else:
            # Strip any trailing parameters after semicolon
            filename = after.split(";", 1)[0].strip()
        return filename
    except Exception:
        return None


def determine_type_from_filename(filename: str, logger):
    """Determine response type from filename extension.

    Args:
        filename: Filename to check
        logger: Logger instance

    Returns:
        Response type ('json', 'csv') or None if undetermined
    """
    if not filename:
        return None

    filename_lower = filename.lower()
    if filename_lower.endswith(".json"):
        logger.info(
            f"Detected JSON from content-disposition filename: {filename}."
        )
        return "json"
    if filename_lower.endswith(".csv"):
        logger.info(
            f"Detected CSV from content-disposition filename: {filename}."
        )
        return "csv"
    return None


def determine_type_from_content_type(content_type: str, logger):
    """Determine response type from content-type header.

    Args:
        content_type: Content-type header value
        logger: Logger instance

    Returns:
        Response type ('json', 'csv') or None if undetermined
    """
    if not content_type:
        return None

    content_type_lower = content_type.lower()
    if (
        "application/json" in content_type_lower
        or "text/json" in content_type_lower
    ):
        logger.info("Detected JSON from content-type header.")
        return "json"
    elif (
        "text/csv" in content_type_lower or "application/csv" in content_type_lower
    ):
        logger.info("Detected CSV from content-type header.")
        return "csv"
    elif "application/octet-stream" in content_type_lower:
        logger.info("Content-type is octet-stream, analyzing content.")
        return None  # Continue to content analysis
    return None


def analyze_response_content(response_content: str, logger) -> str:
    """Analyze response content to determine type.

    Args:
        response_content: Response content as string
        logger: Logger instance

    Returns:
        Response type ('json', 'csv', 'unknown')
    """
    content_stripped = response_content.strip()

    if not content_stripped:
        logger.info("Empty content received")
        return "unknown"

    # Check if it's JSON
    if content_stripped.startswith(("{", "[")):
        logger.info("Content appears to be JSON.")
        try:
            json.loads(content_stripped)
            logger.info("Successfully validated JSON content.")
            return "json"
        except (ValueError, TypeError) as e:
            logger.info(f"JSON validation failed: {e}, treating as CSV.")

    # Check for ZIP/binary files - skip ingestion
    if response_content.startswith("PK"):
        logger.info("Detected ZIP/binary file (PK signature) - skipping ingestion.")
        return "unknown"

    # Default to CSV
    logger.info("Treating content as CSV.")
    return "csv"


def detect_response_type(
    response_content: str,
    content_type: str = None,
    content_disposition: str = None,
    logger=None,
) -> str:
    """Detect the type of response content.

    Args:
        response_content: The response content as string
        content_type: Optional content-type header value
        content_disposition: Optional content-disposition header value
        logger: Logger for debugging

    Returns:
        Response type ('json', 'csv', 'unknown')
    """
    logger.info(
        f"Detecting response type. Content-type: {content_type}, "
        f"Content-disposition: {content_disposition}"
    )

    # Prefer content-disposition filename (when available) to determine type
    filename = extract_filename_from_content_disposition(content_disposition)
    response_type = determine_type_from_filename(filename, logger)
    if response_type:
        return response_type

    # Check content-type header first (ignore misleading octet-stream)
    response_type = determine_type_from_content_type(content_type, logger)
    if response_type:
        return response_type

    # Content analysis
    return analyze_response_content(response_content, logger)


def parse_json_response(response_content: str, logger) -> List[Dict]:
    """Parse JSON response content and return structured data.

    Args:
        response_content: JSON response content
        logger: Logger object

    Returns:
        List of JSON objects
    """
    try:
        data = json.loads(response_content)

        if isinstance(data, dict):
            if "Compliance" in data:
                compliance_data = data["Compliance"]
                logger.info(
                    f"Processed JSON compliance response: {len(compliance_data)} records."
                )
                return compliance_data
            elif "response" in data:
                response_data = data["response"]
                return (
                    response_data
                    if isinstance(response_data, list)
                    else [response_data]
                )
            else:
                return [data]
        elif isinstance(data, list):
            logger.info(f"Processed JSON list response: {len(data)} records.")
            return data
        else:
            logger.info(f"Unexpected JSON structure: {type(data)}.")
            return [{"raw_data": data}]
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse JSON response: {e}.")
        return []


def detect_delimiter(lines: List[str], default_delimiter: str = ",") -> str:
    """Detect custom separator directive from CSV content.

    Args:
        lines: CSV content split into lines
        default_delimiter: Default delimiter to use

    Returns:
        Detected delimiter
    """
    if not lines:
        return default_delimiter

    first_line = lines[0].strip()
    if first_line.lower().startswith("sep="):
        # Extract delimiter after "sep="
        sep_value = first_line.split("=", 1)[1].strip()
        if sep_value:
            return sep_value[0]
        else:
            return ";"
    return default_delimiter


def parse_csv_rows(csv_content: str, delimiter: str) -> List[List[str]]:
    """Parse CSV content into rows using specified delimiter.

    Args:
        csv_content: CSV content as string
        delimiter: CSV delimiter to use

    Returns:
        List of CSV rows
    """
    csv_input = io.StringIO(csv_content)
    reader = csv.reader(csv_input, delimiter=delimiter)
    return list(reader)


def find_header_row_index(all_rows: List[List[str]], required_columns: List[str]):
    """Find the index of the header row containing required columns.

    Args:
        all_rows: All parsed CSV rows
        required_columns: List of required column names (case-insensitive)

    Returns:
        Index of header row, or None if not found
    """
    for idx, row in enumerate(all_rows):
        row_lower = [col.lower().strip() for col in row]
        if all(col in row_lower for col in required_columns):
            return idx
    return None


def extract_headers_and_data(all_rows: List[List[str]], header_row_idx: int) -> tuple:
    """Extract headers and data rows from parsed CSV.

    Args:
        all_rows: All parsed CSV rows
        header_row_idx: Index of the header row

    Returns:
        Tuple of (headers_list, data_rows_list)
    """
    headers = [h.strip().strip('"') for h in all_rows[header_row_idx]]
    data_rows = all_rows[header_row_idx + 1:]
    return headers, data_rows


def process_data_rows(data_rows: List[List[str]], headers: List[str], logger) -> List[Dict]:
    """Process data rows into clean dictionaries.

    Args:
        data_rows: List of data rows
        headers: List of header names
        logger: Logger instance

    Returns:
        List of processed data dictionaries
    """
    data = []
    for row in data_rows:
        if row and any(cell.strip() for cell in row):  # Skip empty rows
            row_dict = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                row_dict[header] = value
            if any(row_dict.values()):
                cleaned_row = utils.clean_row(row_dict)
                data.append(cleaned_row)
    logger.info(f"Converted CSV to {len(data)} JSON objects.")
    return data


def parse_csv_data(csv_content, logger, delimiter=","):
    """Parse CSV content and return structured data records.

    Args:
        csv_content: CSV content as string
        logger: Logger object
        delimiter: CSV delimiter

    Returns:
        List of JSON objects
    """
    try:
        lines = csv_content.splitlines()
        if not lines:
            logger.info("Empty CSV content received")
            return []

        # Detect custom separator directive if present
        delimiter = detect_delimiter(lines, delimiter)

        # Parse CSV into rows
        all_rows = parse_csv_rows(csv_content, delimiter)

        # Find the header row index
        required_columns = ["device type", "ip address", "device name"]
        header_row_idx = find_header_row_index(all_rows, required_columns)

        if header_row_idx is None:
            logger.error("Could not find header row with required columns")
            return []

        # Extract headers and data rows
        headers, data_rows = extract_headers_and_data(all_rows, header_row_idx)

        # Process data rows
        return process_data_rows(data_rows, headers, logger)

    except Exception as e:
        logger.error(f"Error converting CSV to JSON: {e}.")
        return []


def get_reports(catalystc, logger):
    """Get list of reports from Catalyst Center.

    Args:
        catalystc: Catalyst Center API object
        logger: Logger object

    Returns:
        List of reports
    """
    try:
        logger.debug("Fetching reports list from Catalyst Center.")
        reports = catalystc.reports.get_reports()
        if reports:
            logger.info(f"Successfully retrieved {len(reports)} reports.")
            return reports
        else:
            logger.info("No reports found")
            return []
    except Exception as e:
        logger.error(f"Error fetching reports list: {e}.")
        return []


def get_report_data(report_name, report_id, execution_id, catalystc, logger):
    """Download a report from Catalyst Center and return processed data.

    Args:
        report_name: Name of the report
        report_id: ID of the report
        execution_id: ID of the execution
        catalystc: Catalyst Center API object
        logger: Logger object

    Returns:
        List of JSON objects if successful, empty list if failed
    """
    try:
        logger.info(f"Downloading report: {report_name}.")
        url = api.Reports.CATALYSTC_REPORT_EXECUTION_ENDPOINT.format(
            report_id=report_id, execution_id=execution_id
        )

        headers = {"Accept": "*/*"}
        response = catalystc.session.request("GET", url, 0, headers=headers)

        # Log response details

        content_type = response.headers.get("content-type", "")
        content_disposition = response.headers.get("content-disposition", "")
        logger.info(
            f"Response content-type: {content_type}, "
            f"content-disposition: {content_disposition}, "
            f"length: {len(response.text)}"
        )

        # Detect and process response

        response_type = detect_response_type(
            response.text,
            content_type=content_type,
            content_disposition=content_disposition,
            logger=logger,
        )

        processed_data = []

        if response_type == "csv":
            # Pass full content; CSV parser will dynamically locate the header row

            processed_data = parse_csv_data(response.text, logger)
        else:
            logger.info(
                f"Skipping ingestion for unknown response type: {response_type}"
            )
            processed_data = []
        return processed_data
    except Exception as e:
        logger.error(f"Error downloading report {report_name}: {e}.")
        return []


def find_and_validate_report(reports: List[Dict], report_name: str, logger) -> tuple:
    """Find a report by name and validate it has executions.

    Args:
        reports: List of available reports from Catalyst Center
        report_name: Name of the report to find
        logger: Logger instance

    Returns:
        Tuple of (report_dict, execution_id) if valid, (None, None) otherwise
    """
    for report in reports:
        if report.get("name") == report_name:
            if not report.get("executions") or len(report["executions"]) == 0:
                logger.info(f"No executions found for report: {report_name}.")
                return None, None
            execution_id = report["executions"][0]["executionId"]
            return report, execution_id

    logger.info(f"Report '{report_name}' not found in Catalyst Center.")
    return None, None


def process_report_data(
    processed_data: List[Dict],
    report_type: str,
    report_name: str,
    logger
) -> List[Dict]:
    """Process report data and handle success/failure logging.

    Args:
        processed_data: The processed report data
        report_type: Type of report
        report_name: Name of the report
        logger: Logger instance

    Returns:
        The processed data or empty list
    """
    if processed_data:
        logger.info(
            f"Successfully ingested {report_type} report: {report_name} ({len(processed_data)} records)."
        )
        return processed_data
    else:
        logger.info(
            f"No data ingested for {report_type} report: {report_name}."
        )
        return []


def get_report_by_type(report_name, report_type, reports, catalystc, logger):
    """Process a specific report type and return the report data.

    Args:
        report_name: Name of the report to download
        report_type: Type of report ('inventory' or 'compliance')
        reports: List of available reports from Catalyst Center
        catalystc: Catalyst Center API object
        logger: Logger object

    Returns:
        List of JSON data if successful, empty list otherwise
    """
    if not report_name or not report_name.strip():
        logger.info(f"No {report_type} report name specified, skipping collection.")
        return []
    logger.info(f"Processing {report_type} report: {report_name}.")

    # Find and validate the report
    report, execution_id = find_and_validate_report(reports, report_name, logger)
    if not report:
        return []

    # Process the report data
    try:
        report_id = report["reportId"]
        processed_data = get_report_data(
            report_name, report_id, execution_id, catalystc, logger
        )
        return process_report_data(processed_data, report_type, report_name, logger)

    except Exception as e:
        logger.error(
            f"Error processing {report_type} report {report_name}: {e}."
        )
        return []


def write_report_events(data, report_type, report_name, input_name, host, ew, logger):
    """Write report events to Splunk.

    Args:
        data: List of report records to write as events
        report_type: Type of report ('inventory' or 'compliance')
        report_name: Name of the report
        input_name: Name of the input configuration
        host: Host value for events
        ew: EventWriter instance
        logger: Logger instance
    """
    if not data:
        return
    logger.info(f"Ingesting {len(data)} {report_type} events.")
    try:
        for record in data:
            record["cisco_catalyst_host"] = host
            record["report_type"] = report_type
            record["report_name"] = report_name
            record["collection_timestamp"] = int(time.time())

            event = smi.Event(
                data=json.dumps(record),
                source=f"cisco_catalyst_center_{report_type}_report://{input_name}",
                host=host,
                index=None,
                sourcetype=f"cisco:catalyst:center:{report_type}:report",
            )
            ew.write_event(event)
        logger.info(f"Successfully ingested {len(data)} events for {report_type} report type.")
    except Exception as e:
        logger.error(f"Error creating {report_type} events: {e}.")


class CiscoCatalystCenterReports(smi.Script):
    """Splunk modular input for Cisco Catalyst Center reports."""

    def __init__(self):
        """Initialize the modular input."""
        super(CiscoCatalystCenterReports, self).__init__()

    def get_scheme(self):
        """Define the input scheme for Splunk."""
        scheme = smi.Scheme("cisco_catalyst_center_reports")
        scheme.title = "Catalyst Center Reports"
        scheme.description = (
            "Collect inventory and compliance reports from Cisco Catalyst Center"
        )
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Input name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "cisco_dna_center_account",
                title="Catalyst Center Account",
                description="Account configuration for Catalyst Center",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "inventory_report_name",
                title="Inventory Report Name",
                description="Name of the inventory report to collect",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "compliance_report_name",
                title="Compliance Report Name",
                description="Name of the compliance report to collect",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate input parameters."""
        pass

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Event collection method."""
        session_key = self._input_definition.metadata["session_key"]
        input_name, input_conf = [
            [key.split("/")[-1], val] for key, val in inputs.inputs.items()
        ][0]

        # Extract configuration

        account_name = input_conf.get("cisco_dna_center_account")
        inventory_report_name = input_conf.get("inventory_report_name", "").strip()
        compliance_report_name = input_conf.get("compliance_report_name", "").strip()

        # Initialize logger

        logger = logger_manager.get_logger(
            f"catalyst_center_reports_{input_name}",
            input_conf.get("logging_level", "INFO"),
        )
        logger.info(f"Starting data collection for input: {input_name}.")

        # Validate input

        if not inventory_report_name and not compliance_report_name:
            logger.error("At least one report name must be specified.")
            return
        # Get account configuration

        try:
            account_conf = utils.get_account_config(
                session_key, consts.ACCOUNT_CONF_FILE, logger
            )
            account_info = account_conf.get(account_name)
            if not account_info:
                logger.error(f"Account configuration not found: {account_name}.")
                return
            host = account_info.get("cisco_dna_center_host")
            username = account_info.get("username")
            password = account_info.get("password")
            use_ca_cert = account_info.get("use_ca_cert")
            CATALYSTC_VERSION = "2.2.3.3"

            # SSL configuration

            if utils.is_true(use_ca_cert):
                verify = consts.CATALYSTC_CERT_FILE_LOC.format(
                    cert_name=account_info.get("copy_account_name", "").strip()
                )
                logger.debug(f"Using SSL certificate: {verify}.")
            else:
                verify = utils.get_sslconfig(session_key, logger)

            # Initialize Catalyst Center API

            catalystc = api.CatalystCenterAPI(
                username=username,
                password=password,
                base_url=host,
                version=CATALYSTC_VERSION,
                verify=verify,
                debug=False,
                helper=logger,
            )
            # Get reports list

            reports = get_reports(catalystc, logger)

            # Process inventory report

            inventory_data = []
            if inventory_report_name:
                inventory_data = get_report_by_type(
                    inventory_report_name, "inventory", reports, catalystc, logger
                )
            # Process compliance report

            compliance_data = []
            if compliance_report_name:
                compliance_data = get_report_by_type(
                    compliance_report_name, "compliance", reports, catalystc, logger
                )
            # Create inventory events

            write_report_events(
                inventory_data,
                "inventory",
                inventory_report_name,
                input_name,
                host,
                ew,
                logger,
            )

            # Create compliance events

            write_report_events(
                compliance_data,
                "compliance",
                compliance_report_name,
                input_name,
                host,
                ew,
                logger,
            )

            logger.info(
                f"Data collection completed successfully for input: {input_name}."
            )
            logger.info(
                "instance={}, product=Cisco Catalyst Center,"
                " filter_value=cisco_catalyst_center_reports://{},"
                " status=Connected,".format(input_name, input_name)
            )
        except Exception as e:
            logger.error(
                f"Data collection failed for input: {input_name} Status: Not Connected - {str(e)}."
            )
            logger.info(
                "instance={}, product=Cisco Catalyst Center, "
                "filter_value=cisco_catalyst_center_reports://{}, "
                "status=Not Connected,".format(input_name, input_name)
            )
            logger.exception("Detailed error information")


if __name__ == "__main__":
    exit_code = CiscoCatalystCenterReports().run(sys.argv)
    sys.exit(exit_code)
