"""REST handler for Feed Management."""

import sys
import os
import traceback
import json
import splunk
import csv
from io import StringIO

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "..", "lib"))
from silent_push_helpers.logger_manager import setup_logging  # noqa: #402
from silent_push_helpers.constants import Endpoints  # noqa: #402
from silent_push_helpers.rest_helper import RestHelper  # noqa: #402
from silent_push_helpers.conf_helper import get_credentials  # noqa: #402
from silent_push_helpers.utils import check_indicator_type  # noqa: #402


logger = setup_logging("ta_silent_push_feed_management")

FEED_INPUT = "silent_push_feed"
FILENAME_REGEX = r"^[a-zA-Z]\w*$"
FILENAME_EXTRACT_REGEX = r"filename=\"(.*)\""
SUCCESS_MESSAGE = "Indicators added to feed successfully."
MAX_INDICATOR_PER_REQUEST = 100


class SilentPushFeedConfiguration(splunk.rest.BaseRestHandler):
    """Class for handling Feed Management through custom endpoint."""

    def _validate_csv_payload(self, payload):
        """Validate CSV payload and return content and column name."""
        if not payload.get("file"):
            raise Exception("No file uploaded. Please upload a CSV file.")

        if not payload.get("file", {}).get("content"):
            raise Exception("The uploaded CSV file is empty.")

        content = payload.get("file").get("content")
        indicator_column_name = payload.get("indicator_column_name", "").strip()
        return content, indicator_column_name

    def _detect_csv_format(self, content):
        """Detect if CSV has multiple columns."""
        sample_lines = content.split("\n")[:1]
        return "," in sample_lines[0].strip()

    def _validate_multicolumn_csv(self, content, indicator_column_name):
        """Validate multi-column CSV and return csv_reader."""
        if not indicator_column_name:
            columns = [col.strip() for col in content.split("\n")[0].strip().split(",")]
            error_message = (
                "Multi-column CSV detected. Please specify the indicator field name."
            )
            error_message += f" Available fields: {', '.join(columns)}"
            raise Exception(error_message)

        csv_file = StringIO(content)
        csv_reader = csv.DictReader(csv_file)

        if indicator_column_name not in csv_reader.fieldnames:
            available_columns = (
                ", ".join(csv_reader.fieldnames) if csv_reader.fieldnames else "None"
            )
            error_message = f"Field '{indicator_column_name}' not found in CSV."
            error_message += f" Available fields: {available_columns}"
            raise Exception(error_message)

        return csv_reader

    def _clean_and_validate_indicator(self, indicator_value):
        """Clean and validate a single indicator."""
        cleaned_indicator = indicator_value.replace("[", "").replace("]", "").strip()
        indicator_type = check_indicator_type(cleaned_indicator)
        return cleaned_indicator, indicator_type

    def _process_indicator(self, cleaned_indicator, indicator_type, row_identifier):
        """Process a single indicator and categorize it."""
        if indicator_type in ["ipv4"]:
            self.ip_indicators.add(cleaned_indicator)
        elif indicator_type == "domain":
            self.domain_indicators.add(cleaned_indicator)
        else:
            invalid_entry = cleaned_indicator
            self.invalid_indicators.append(invalid_entry)
            logger.warning(
                f"Invalid indicator at {row_identifier.lower()}: {cleaned_indicator}"
            )

    def _process_multicolumn_csv(self, csv_reader, indicator_column_name):
        """Process multi-column CSV data."""
        for row_num, row in enumerate(csv_reader, start=2):
            indicator_value = row.get(indicator_column_name, "").strip()
            if not indicator_value:
                continue

            cleaned_indicator, indicator_type = self._clean_and_validate_indicator(
                indicator_value
            )
            self._process_indicator(cleaned_indicator, indicator_type, f"Row {row_num}")

    def _process_singlecolumn_csv(self, content):
        """Process single-column CSV data."""
        lines = content.split("\n")
        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            cleaned_indicator, indicator_type = self._clean_and_validate_indicator(line)
            self._process_indicator(
                cleaned_indicator, indicator_type, f"Line {line_num}"
            )

    def _validate_parsing_results(self):
        """Validate that parsing found valid indicators."""
        if not self.ip_indicators and not self.domain_indicators:
            if self.invalid_indicators:
                error_message = "No valid indicators found in the uploaded file."
                error_message += (
                    f" Found {len(self.invalid_indicators)} invalid indicators."
                )
            else:
                error_message = "No indicators found in the uploaded file."
                error_message += (
                    " Please ensure the file contains valid IP addresses or domains."
                )
            raise Exception(error_message)

    def parse_csv(self, payload):
        """Parse the uploaded CSV and extract the indicators."""
        try:
            # Initialize indicator collections
            self.ip_indicators = set()
            self.domain_indicators = set()
            self.invalid_indicators = []

            # Validate payload and extract content
            content, indicator_column_name = self._validate_csv_payload(payload)

            # Detect CSV format and process accordingly
            has_multiple_columns = self._detect_csv_format(content)

            if has_multiple_columns:
                csv_reader = self._validate_multicolumn_csv(
                    content, indicator_column_name
                )
                self._process_multicolumn_csv(csv_reader, indicator_column_name)
            else:
                self._process_singlecolumn_csv(content)

            # Validate results
            self._validate_parsing_results()

            # Log success
            logger.info(
                f"Successfully parsed CSV: {len(self.ip_indicators)} IP indicators, "
                f"{len(self.domain_indicators)} domain indicators, "
                f"{len(self.invalid_indicators)} invalid indicators"
            )

        except Exception as err:
            logger.error(f"Error parsing CSV: {str(err)}")
            if "NoneType" not in str(err):
                raise Exception(str(err))
            raise Exception("Error parsing CSV file. Please check the file format and upload a valid CSV.")

    def get_uuid_from_response(self, all_feeds, feed_name):
        """Get uuid from response."""
        for feed in all_feeds:
            if feed.get("name") == feed_name:
                self.feed_type = feed.get("type")  # ip or domain
                return feed.get("uuid", None)
        return None

    def create_new_feed(self, feed_name, feed_description, feed_creation_type):
        """Create new feed."""
        try:
            response = self.rest_helper_obj.post(
                Endpoints.SILENT_PUSH_FEEDS_URL,
                platform="api",
                silent_push_version="v1",
                payload={
                    "name": feed_name,
                    "feed_description": feed_description,
                    "type": feed_creation_type,
                },
            )
            return response
        except Exception as err:
            logger.error(f"Error creating feed: {str(err)}")
            return None

    def fetch_feed_name_uuid(self, feed_name):
        """Fetch feed name uuid."""
        response = self.rest_helper_obj.get(
            Endpoints.SILENT_PUSH_FEEDS_URL,
            platform="api",
            silent_push_version="v1",
        )
        total_pages = response.get("metadata", {}).get("pages", 1)
        all_feeds = response.get("data", [])
        uuid = self.get_uuid_from_response(all_feeds, feed_name)
        if uuid:
            return uuid
        for i in range(2, total_pages + 1):
            response = self.rest_helper_obj.get(
                Endpoints.SILENT_PUSH_FEEDS_URL,
                platform="api",
                silent_push_version="v1",
                params={"page": i},
            )
            all_feeds = response.get("data", [])
            uuid = self.get_uuid_from_response(all_feeds, feed_name)
            if uuid:
                return uuid
        return None

    def send_indicator_to_feed(self, indicators):
        """Send indicators to feed."""
        try:
            logger.info("Started Adding indicators to feed")
            if len(indicators) > MAX_INDICATOR_PER_REQUEST:
                response = {}
                for ind in range(0, len(indicators), MAX_INDICATOR_PER_REQUEST):
                    ind_list = indicators[ind:ind + MAX_INDICATOR_PER_REQUEST]
                    res = self.rest_helper_obj.post(
                        endpoint=Endpoints.SILENT_PUSH_INDICATOR_ADD_URL.format(
                            self.feed_name_uuid
                        ),
                        platform="api",
                        silent_push_version="v1",
                        payload={"indicators": ind_list},
                    )
                    self.created_or_updated.extend(res.get("created_or_updated", []))
                    response = self.merge_with_previous_response(response, res)

                return response
            else:
                response = self.rest_helper_obj.post(
                    endpoint=Endpoints.SILENT_PUSH_INDICATOR_ADD_URL.format(
                        self.feed_name_uuid
                    ),
                    platform="api",
                    silent_push_version="v1",
                    payload={"indicators": indicators},
                )
                self.created_or_updated = response.get("created_or_updated", [])
                return response
        except Exception as err:
            logger.error(f"Error adding indicators to feed: {str(err)}")

    def add_tags_to_feed(self):
        """Add tags to feed."""
        try:
            logger.info("Started Adding tags to feed")
            response = self.rest_helper_obj.post(
                endpoint=Endpoints.SILENT_PUSH_FEED_TAGS_ADD_URL.format(
                    self.feed_name_uuid
                ),
                platform="api",
                silent_push_version="v1",
                payload={"tags": self.feed_tags},
            )
            return response
        except Exception as err:
            logger.error(f"Error adding tags to feed: {str(err)}")

    def add_tags_to_indicators(self):
        """Add tags to indicators."""
        try:
            # GET all the indicators with tags
            response = self.rest_helper_obj.get(
                endpoint=Endpoints.SILENT_PUSH_INDICATOR_ADD_URL.format(
                    self.feed_name_uuid
                ),
                platform="api",
                silent_push_version="v1",
            )
            total_pages = response.get("metadata", {}).get("pages", 1)
            all_indicators = response.get("data", [])
            for i in range(2, total_pages + 1):
                response = self.rest_helper_obj.get(
                    endpoint=Endpoints.SILENT_PUSH_INDICATOR_ADD_URL.format(
                        self.feed_name_uuid
                    ),
                    platform="api",
                    silent_push_version="v1",
                    params={"page": i},
                )
                all_indicators.extend(response.get("data", []))
            name_tag_dict = {}
            for indicator in all_indicators:
                name_tag_dict[indicator["name"]] = indicator["tags"]

            # POST all the indicator tags
            logger.info("Started Adding tags to indicators")
            self.indicator_tags = ", ".join(self.indicator_tags)
            if self.created_or_updated:
                for indicator in self.created_or_updated:
                    if (
                        indicator["name"] in name_tag_dict
                        and name_tag_dict[indicator["name"]] != ""
                    ):
                        indicator_tags = (
                            self.indicator_tags
                            + ", "
                            + name_tag_dict[indicator["name"]]
                        )
                    else:
                        indicator_tags = self.indicator_tags
                    response = self.rest_helper_obj.put(
                        endpoint=Endpoints.SILENT_PUSH_INDICATOR_TAGS_ADD_URL.format(
                            self.feed_name_uuid, indicator["name"]
                        ),
                        platform="api",
                        silent_push_version="v1",
                        payload={"tags": indicator_tags},
                    )
                    logger.info(
                        f"Tag {indicator_tags} added to Indicator {indicator['name']}"
                    )

        except Exception as err:
            logger.error(f"Error adding tags to indicators: {str(err)}")

    def merge_with_previous_response(self, previous_response, new_response):
        """Merge two dictionaries."""
        # Merge keys from both dictionaries
        result = {}
        has_value = set(previous_response) | set(new_response)
        if has_value:
            for key in set(previous_response) | set(new_response):
                if key in previous_response and key in new_response:
                    # If both are lists, merge them
                    if isinstance(previous_response[key], list) and isinstance(
                        new_response[key], list
                    ):
                        result[key] = previous_response[key] + new_response[key]
                    else:
                        # Otherwise
                        result[key] = new_response[key]
                elif key in previous_response:
                    result[key] = previous_response[key]
                else:
                    result[key] = new_response[key]
            return result

    def _setup_new_feed(self, payload):
        """Set up a new feed and return its UUID."""
        feed_name = payload.get("new_feed_name")
        feed_description = payload.get("feed_description")
        feed_creation_type = payload.get("feed_creation_type")
        self.feed_type = payload.get("feed_creation_type")

        create_feed_response = self.create_new_feed(
            feed_name, feed_description, feed_creation_type
        )
        logger.info(f"Feed {feed_name} created on Silent Push Platform")

        if not create_feed_response:
            error_msg = f'A feed "{feed_name}" with the same name already exists. Please choose a different feed name.'
            logger.error(error_msg)
            raise Exception(error_msg)

        return create_feed_response.get("uuid")

    def _setup_existing_feed(self, payload):
        """Set up connection to existing feed and return its UUID."""
        feed_name = payload.get("existing_feed_name")
        feed_uuid = self.fetch_feed_name_uuid(feed_name)

        if not feed_uuid:
            error_msg = f'Feed "{feed_name}" not found on Silent Push Platform'
            logger.error(error_msg)
            raise Exception(error_msg)

        return feed_uuid

    def _determine_feed_uuid(self, payload):
        """Determine feed UUID based on feed type."""
        if payload.get("feed_type") == "create_new":
            return self._setup_new_feed(payload)
        else:
            return self._setup_existing_feed(payload)

    def _process_manual_indicators(self, payload):
        """Process manually entered indicators."""
        indicators = payload.get("indicator_value", "").split(",")

        for indicator in indicators:
            indicator = indicator.strip()
            indicator_type = check_indicator_type(indicator)

            if indicator_type in ["ipv4"]:
                self.ip_indicators.append(indicator)
            elif indicator_type == "domain":
                self.domain_indicators.append(indicator)
            else:
                self.invalid_indicators.append(indicator)
                logger.warning(f"Invalid indicator: {indicator}")

    def _send_indicators_to_feed(self):
        """Send all indicators to feed and return combined response."""
        response = {}
        self.created_or_updated = []

        if self.ip_indicators:
            response = self.send_indicator_to_feed(self.ip_indicators)

        if self.domain_indicators:
            domain_response = self.send_indicator_to_feed(self.domain_indicators)
            if response:
                response = self.merge_with_previous_response(response, domain_response)
            else:
                response = domain_response

        return response

    def _build_csv_response_message(self, response):
        """Build response message for CSV processing."""
        if not response:
            raise Exception("Error occurred while adding the Indicators.")
        if hasattr(self, "invalid_indicators") and self.invalid_indicators:
            response.update({"invalid_indicators": self.invalid_indicators})
            total_invalid = len(self.invalid_indicators)
            invalid_ind_list = self.invalid_indicators
            if self.feed_type == 'ip':
                total_valid = len(self.ip_indicators)
                valid_ind_list = self.ip_indicators
                total_invalid += len(self.domain_indicators)
                invalid_ind_list += self.domain_indicators
            else:
                total_valid = len(self.domain_indicators)
                valid_ind_list = self.domain_indicators
                total_invalid += len(self.ip_indicators)
                invalid_ind_list += self.ip_indicators
            msg = f"Posting indicators completed. {total_valid} valid indicator(s) added to the feed."
            msg += f" {total_invalid} invalid indicator(s) skipped."
            new_msg = f"Posted indicators: {valid_ind_list}. Invalid indicators: {list(set(invalid_ind_list))}."
            response.update({"message": msg})
            logger.info(msg)
            logger.debug(new_msg)
        else:
            total_invalid = len(self.invalid_indicators)
            invalid_ind_list = self.invalid_indicators
            if self.feed_type == 'ip':
                total_valid = len(self.ip_indicators)
                valid_ind_list = self.ip_indicators
                total_invalid += len(self.domain_indicators)
                invalid_ind_list += self.domain_indicators
                self.invalid_indicators.extend(self.domain_indicators)
            else:
                total_valid = len(self.domain_indicators)
                valid_ind_list = self.domain_indicators
                total_invalid += len(self.ip_indicators)
                invalid_ind_list += self.ip_indicators
                self.invalid_indicators.extend(self.ip_indicators)
            msg = f"Posting indicators completed. {total_valid} valid indicator(s) added to the feed."
            msg += f" {total_invalid} invalid indicator(s) skipped."
            new_msg = f"Posted indicators: {valid_ind_list}. Invalid indicators: {list(set(invalid_ind_list))}."
            response.update({"message": msg})
            logger.info(msg)
            logger.debug(new_msg)

        return response

    def _process_csv_indicators(self):
        """Process CSV indicators and return response."""
        # Convert sets to lists for CSV processing
        self.ip_indicators = list(self.ip_indicators)
        self.domain_indicators = list(self.domain_indicators)

        response = self._send_indicators_to_feed()
        return self._build_csv_response_message(response)

    def _process_manual_indicators_flow(self, payload):
        """Process manual indicators flow and return response."""
        self.invalid_indicators = []
        self._process_manual_indicators(payload)
        response = self._send_indicators_to_feed()
        invalid_indicators = response.get("invalid_indicators", [])
        invalid_indicators_list = list(set(self.invalid_indicators + invalid_indicators))
        response.update({"invalid_indicators": invalid_indicators_list})
        msg = f"Posting indicators completed. {len(response.get('created_or_updated', []))} valid indicator(s) added"
        msg += f" to the feed. {len(invalid_indicators_list)} invalid indicator(s) skipped."
        new_msg = f"Posted indicators: {response.get('created_or_updated', [])}."
        new_msg += f" Invalid indicators: {invalid_indicators_list}."
        response.update({"message": msg})
        logger.info(msg)
        logger.debug(new_msg)
        return response

    def create_feed_input(self, payload):
        """Create or update a Silent Push feed input."""
        try:
            # Setup feed UUID
            self.feed_name_uuid = self._determine_feed_uuid(payload)

            # Process indicators based on ingestion type
            if payload.get("ingestion_type") == "indicators":
                return self._process_manual_indicators_flow(payload)
            else:  # CSV upload
                return self._process_csv_indicators()

        except Exception as err:
            logger.error(
                f"Silent Push Error: Error occurred while creating feed input: {err}"
            )
            raise Exception(str(err))

    def _extract_boundary_from_payload(self, payload):
        """Extract boundary string from multipart payload."""
        boundary_index = payload.find("--")
        if boundary_index == -1:
            return None

        boundary_end_index = payload.find("\n", boundary_index)
        return payload[boundary_index:boundary_end_index].strip()

    def _split_payload_into_parts(self, payload, boundary):
        """Split payload into individual parts using boundary."""
        return payload.split(boundary)

    def _normalize_and_split_part(self, part):
        """Normalize line endings and split part into headers and content."""
        if not part.strip():
            return None, None

        # Normalize line endings
        part = part.replace("\r\n", "\n")
        # Split headers from content
        parts_split = part.lstrip().split("\n\n", 1)
        if len(parts_split) < 2:
            return None, None

        headers, content = parts_split
        return headers, content.strip()

    def _extract_filename_from_headers(self, headers):
        """Extract filename from headers if present."""
        if "filename=" not in headers:
            return None

        return headers.split('filename="')[1].split('"')[0]

    def _extract_field_name_from_headers(self, headers):
        """Extract form field name from headers."""
        if 'name="' not in headers:
            return None

        return headers.split('name="')[1].split('"')[0]

    def _convert_content_type(self, content):
        """Convert content to appropriate data type."""
        if content.isdigit():
            return int(content)
        elif content.lower() == "false":
            return False
        elif content.lower() == "true":
            return True
        return content

    def _process_file_part(self, headers, content):
        """Process file part and return file data."""
        filename = self._extract_filename_from_headers(headers)
        if filename is None:
            return None

        return {"filename": filename, "content": content}

    def _process_form_field_part(self, headers, content):
        """Process form field part and return field name and converted content."""
        field_name = self._extract_field_name_from_headers(headers)
        if field_name is None:
            return None, None

        converted_content = self._convert_content_type(content)
        return field_name, converted_content

    def _process_single_part(self, part, parsed_data):
        """Process a single multipart form data part."""
        headers, content = self._normalize_and_split_part(part)
        if headers is None or content is None:
            return

        # Check if this part contains a file
        if "filename=" in headers:
            file_data = self._process_file_part(headers, content)
            if file_data:
                parsed_data["file"] = file_data
        else:
            # Process as form field
            field_name, converted_content = self._process_form_field_part(
                headers, content
            )
            if field_name is not None:
                parsed_data[field_name] = converted_content

    def parse_formdata(self, payload):
        """Parse formdata and return dict."""
        try:
            # Extract boundary from payload
            boundary = self._extract_boundary_from_payload(payload)
            if boundary is None:
                return {}

            # Split payload into parts
            parts = self._split_payload_into_parts(payload, boundary)

            # Process each part
            parsed_data = {}
            for part in parts:
                self._process_single_part(part, parsed_data)

            return parsed_data
        except Exception as err:
            logger.error(f"Error parsing form data: {err}")
            return {}

    def validate_fields(self, payload):
        """Validate required fields."""
        if not payload.get("silent_push_account"):
            raise Exception("Silent Push Account is required.")

        if not payload.get("feed_type"):
            raise Exception("Feed Type is required.")

        if not payload.get("ingestion_type"):
            raise Exception("Data Ingestion Type is required.")

    def handle_POST(self):
        """Handle POST requests from frontend."""
        try:
            logger.info("Silent Push Info: Started feed configuration process.")
            payload = self.request["payload"]
            payload = self.parse_formdata(payload)

            # Validate required fields
            self.validate_fields(payload)

            silent_push_config = {
                "session_key": self.sessionKey,
            }
            self.account_name = payload.get("silent_push_account", "")
            account_info = get_credentials(self.account_name, self.sessionKey)
            silent_push_config.update(account_info)
            self.rest_helper_obj = RestHelper(silent_push_config, logger)
            self.domain_indicators = []
            self.ip_indicators = []
            self.invalid_indicators = []

            # Process based on ingestion type
            if payload.get("ingestion_type") == "add_csv":
                self.parse_csv(payload)
            elif payload.get("ingestion_type") == "indicators":
                # Single indicator will be validated in create_feed_input
                pass
            else:
                raise Exception("Invalid ingestion type.")

            # Create the feed input
            response_message = self.create_feed_input(payload)

            # Extract tag parameters
            tags_to_feed = payload.get("tags_to_feed", "")
            tags_to_indicators = payload.get("tags_to_indicators", "")
            self.feed_tags = []
            self.indicator_tags = []

            # Add tags to feed if provided
            if tags_to_feed:
                # Convert comma-separated string to list and clean up whitespace
                tags_list = [
                    tag.strip() for tag in tags_to_feed.split(",") if tag.strip()
                ]
                if tags_list:
                    self.feed_tags = tags_list
                    self.add_tags_to_feed()
            else:
                logger.info("Tags for feed are not provided. Skipping adding tags to feed.")

            # Add tags to indicators if provided
            if tags_to_indicators:
                # Convert comma-separated string to list and clean up whitespace
                tags_list = [
                    tag.strip() for tag in tags_to_indicators.split(",") if tag.strip()
                ]
                if tags_list:
                    self.indicator_tags = tags_list
                    self.add_tags_to_indicators()
            else:
                logger.info("Tags for indicators are not provided. Skipping adding tags to indicators.")

            logger.info("Silent Push Info: Completed feed configuration process.")

        except Exception as err:
            logger.error(
                f"Silent Push Error: Error occurred while configuring feed: {err}"
            )
            logger.debug(
                f"Silent Push Debug: Error occurred while configuring feed: {traceback.format_exc()}"
            )
            raise Exception(str(err))

        finally:
            self.response.setHeader("content-type", "application/json")
            if "response_message" in locals():
                response = json.dumps(response_message)
            else:
                response = json.dumps({"message": SUCCESS_MESSAGE})
            self.response.write(response)

    # Handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
