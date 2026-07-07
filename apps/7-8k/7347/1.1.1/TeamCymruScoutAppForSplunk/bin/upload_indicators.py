"""Rest handler that saves uploaded csv files."""
import sys
import os
import traceback
import re
import json
import splunk
from splunk import rest
from requests.compat import quote_plus


BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "..", "lib"))
from cymru_helpers.constants import APP_NAME, DOMAIN_REGEX, IPV4_IPV6_REGEX  # noqa:E402
from cymru_helpers.logger_manager import setup_logging  # noqa:E402
logger = setup_logging("ta_team_cymru_scout_upload_indicators")

INDICATORS_INPUT = "cymru_indicator"
FILENAME_REGEX = r"^[a-zA-Z]\w*$"
FILENAME_EXTRACT_REGEX = r"filename=\"(.*)\""


class Indicators(splunk.rest.BaseRestHandler):
    """Class for getting UI validation message through custom endpoint."""

    def parse_csv(self, payload):
        """Parse the uploaded csv and extract the domains and ips."""
        try:
            # Validate filename and check for duplicate files
            is_valid = True
            self.ips = set()
            self.domains = set()

            if not payload.get("file"):
                error_message = "No file uploaded. Please upload a csv file."
                is_valid = False
                raise Exception(error_message)
            if not payload.get("file", {}).get("content"):
                error_message = "The uploaded CSV file is empty."
                is_valid = False
                raise Exception(error_message)

            if "," in payload.get("file").get("content"):
                error_message = "The uploaded CSV file contains more than one column."
                is_valid = False
                raise Exception(error_message)

            lines = payload.get("file").get("content").split("\n")
            for i in range(len(lines)):
                temp_line = lines[i].replace("[", "").replace("]", "")
                if re.search(IPV4_IPV6_REGEX, temp_line):
                    self.ips.add(lines[i])
                elif re.search(DOMAIN_REGEX, temp_line):
                    self.domains.add(lines[i])

            if not is_valid:
                raise Exception(error_message)

        except Exception as err:
            raise Exception(err)

    def fetch_data(self, input_stanza, ip=None):
        """Fetch indicators parameter from modular input."""
        try:
            _, response = rest.simpleRequest("/servicesNS/nobody/{}/configs/conf-inputs/{}?output_mode=json".format(
                APP_NAME, input_stanza),
                self.sessionKey,
                method="GET",
                raiseAllErrors=True,
            )
            response = json.loads(response)
            indicators = response.get("entry", [])[0].get("content", {}).get("indicators", "")
            if ip:
                indicators = indicators.split(",")
                indicators.extend(self.ips)
                return "{}".format(",".join(set(indicators)))
            else:
                indicators = indicators.split(",")
                indicators.extend(self.domains)
                return "{}".format(",".join(set(indicators)))
        except Exception as err:
            raise Exception(err)

    def update_domain_modular_input(self, payload, input_stanza, domain_indicators_input_stanza):
        """Update domain modular input."""
        try:
            if not payload.get("file_overwrite"):
                updated_domains = self.fetch_data(quote_plus(input_stanza))
                domain_indicators_input_stanza["indicators"] = updated_domains
            domain_indicators_input_stanza.pop("disabled")
            domain_indicators_input_stanza.pop("name")
            rest.simpleRequest(
                "/servicesNS/nobody/{}/configs/conf-inputs/{}".format(
                    APP_NAME, quote_plus(input_stanza)),
                self.sessionKey,
                postargs=domain_indicators_input_stanza,
                method="POST",
                raiseAllErrors=True,
            )
        except Exception as err:
            raise Exception(err)

    def update_ip_modular_output(self, payload, input_stanza, ip_indicators_input_stanza):
        """Update ip modular input."""
        try:
            if not payload.get("file_overwrite"):
                updated_ips = self.fetch_data(quote_plus(input_stanza), ip="ip")
                ip_indicators_input_stanza["indicators"] = updated_ips
            ip_indicators_input_stanza.pop("disabled")
            ip_indicators_input_stanza.pop("name")
            rest.simpleRequest(
                "/servicesNS/nobody/{}/configs/conf-inputs/{}".format(
                    APP_NAME, quote_plus(input_stanza)),
                self.sessionKey,
                postargs=ip_indicators_input_stanza,
                method="POST",
                raiseAllErrors=True,
            )
        except Exception as err:
            raise Exception(err)

    def create_modular_input(self, payload):
        """Create a modular input."""
        if self.domains:
            api_type = "details"
            input_stanza = "{}://team_cymru_{}_{}_domain".format(
                INDICATORS_INPUT, payload.get("account_name"), api_type
            )
            domain_indicators_input_stanza = {
                "name": input_stanza,
                "disabled": "true",
                "interval": payload.get("interval"),
                "index": payload.get("index"),
                "global_account": payload.get("account_name"),
                "api_type": api_type,
                "indicator_type": "domain",
                "indicators": ",".join(self.domains)
            }
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-inputs".format(
                        APP_NAME),
                    self.sessionKey,
                    postargs=domain_indicators_input_stanza,
                    method="POST",
                    raiseAllErrors=True,
                )
                logger.info(f"Team Cymru Scout Info: Created '{input_stanza}' input.")
            except Exception as err:
                if "409" in str(err):
                    self.update_domain_modular_input(payload, input_stanza, domain_indicators_input_stanza)
                    logger.info(f"Team Cymru Scout Info: Updated '{input_stanza}' input.")

        if self.ips:
            input_stanza = "{}://team_cymru_{}_{}_ip".format(
                INDICATORS_INPUT, payload.get("account_name"), payload.get("api_type")
            )
            ip_indicators_input_stanza = {
                "name": input_stanza,
                "disabled": "true",
                "interval": payload.get("interval"),
                "index": payload.get("index"),
                "global_account": payload.get("account_name"),
                "api_type": payload.get("api_type"),
                "indicator_type": "ip",
                "indicators": ",".join(self.ips)
            }
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-inputs".format(
                        APP_NAME),
                    self.sessionKey,
                    postargs=ip_indicators_input_stanza,
                    method="POST",
                    raiseAllErrors=True,
                )
                logger.info(f"Team Cymru Scout Info: Created '{input_stanza}' input.")
            except Exception as err:
                if "409" in str(err):
                    self.update_ip_modular_output(payload, input_stanza, ip_indicators_input_stanza)
                    logger.info(f"Team Cymru Scout Info: Updated '{input_stanza}' input.")

    def parse_formdata(self, payload):
        """Parse formdata and return dict."""
        boundary_index = payload.find("--")
        boundary_end_index = payload.find("\n", boundary_index)
        boundary = payload[boundary_index:boundary_end_index].strip()
        parts = payload.split(boundary)
        # Parse each part into a dictionary
        parsed_data = {}
        for part in parts:
            # Skip any empty parts
            if not part.strip():
                continue

            # Normalize line endings
            part = part.replace('\r\n', '\n')
            # Split headers from content
            parts_split = part.lstrip().split("\n\n", 1)
            if len(parts_split) < 2:
                continue  # Skip any part that does not have both headers and content
            headers, content = parts_split
            content = content.strip()

            # Determine if the part contains a file
            if 'filename=' in headers:
                # Extract the file name
                filename = headers.split('filename="')[1].split('"')[0]
                # Add the file details to the dictionary
                parsed_data['file'] = {'filename': filename, 'content': content}
            else:
                # Extract the name of the form field
                name = headers.split('name="')[1].split('"')[0]
                # Convert "false" to False and try to convert numerical values to integers
                if content.isdigit():
                    content = int(content)
                elif content.lower() == 'false':
                    content = False
                elif content.lower() == 'true':
                    content = True
                # Add the form field to the dictionary
                parsed_data[name] = content

        return parsed_data

    def handle_POST(self):
        """Handle POST requests from frontend."""
        try:
            logger.info("Team Cymru Scout Info: Started creating modular input.")
            payload = self.request["payload"]
            payload = self.parse_formdata(payload)
            logger.debug("Team Cymru Scout Info: Converted formdata to json.")
            self.parse_csv(payload)
            logger.debug("Team Cymru Scout Info: Parsed csv file to get domains and ips.")
            if not self.domains and not self.ips:
                raise Exception("No IP/Domain found in the uploaded file.")  # noqa: E501
            self.create_modular_input(payload)
            logger.info("Team Cymru Scout Info: Completed creation of modular input.")

        except Exception as err:
            logger.error("Team Cymru Scout Error: Error Occured While Creating Modular Input: {}".format(err))
            logger.debug(
                "Team Cymru Scout Debug: Error Occured While Creating Modular Input: {}"
                .format(traceback.format_exc())
            )
            raise Exception(err)

        finally:
            self.response.setHeader('content-type', 'application/json')
            if payload.get("api_type") == "foundation" and self.domains:
                response = json.dumps(
                    '{"message":"File upload successful. Domains are detected in the file. so search API will be used to collect the details for the domains. Navigate to the Inputs dashboard to enable the data collection."}'  # noqa: E501
                )
            else:
                response = json.dumps(
                    '{"message":"File upload successful. Navigate to the Inputs dashboard to enable the data collection."}')  # noqa: E501
            self.response.write(response)

    # handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
