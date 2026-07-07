"""Rest handler that saves uploaded csv files."""
import os
import re
import json
import csv
import splunk
from splunk import rest
from .passivetotal_utils import APP_NAME, CSV_STORAGE_PATH, CSV_EXTENSION

INDICATORS_INPUT = "indicators"
FILENAME_REGEX = r"^[a-zA-Z]\w*$"
FILENAME_EXTRACT_REGEX = r"filename=\"(.*)\""


class Indicators(splunk.rest.BaseRestHandler):
    """Class for getting UI validation message through custom endpoint."""

    def parse_and_save_csv(self, payload):
        """Save uploaded csv files to local/indicators folder."""
        try:
            # Validate filename and check for duplicate files
            is_valid = True
            file_group = re.search(FILENAME_EXTRACT_REGEX, payload)
            all_files = []
            is_exist = os.path.exists(CSV_STORAGE_PATH)
            if not is_exist:
                os.makedirs(CSV_STORAGE_PATH)
            all_files = os.listdir(CSV_STORAGE_PATH)

            if not file_group:
                error_message = "No file uploaded. Please upload a csv file."
                is_valid = False
                raise Exception(error_message)

            self.filename = file_group.group(1)
            self.filename_without_ext = os.path.splitext(self.filename)[0]

            if self.filename in all_files:
                error_message = "File with the same name already exists. Please choose a different file."
                is_valid = False

            elif not self.filename.endswith(CSV_EXTENSION):
                error_message = "Please upload a valid csv file."
                is_valid = False

            elif not re.match(FILENAME_REGEX, self.filename_without_ext):
                error_message = "File name must start with a letter and followed by alphabetic letters,\
                 digits or underscores."
                is_valid = False

            if not is_valid:
                raise Exception(error_message)

            # Sample Uploaded CSV Format
            """
            Indicators
            abc.com
            pqr.com
            1.x.x.1
            """

            # Sample Received Payload
            """
            ------WebKitFormBoundary1DLSYGhIBHUFCBDg\r
            Content-Disposition: form-data; name="file"; filename="indicators.csv"\r
            Content-Type: application/octet-stream\r
            \r
            Indicators\r
            abc.com\r
            pqr.com\r
            1.x.x.1\r
            \r
            ------WebKitFormBoundary1DLSYGhIBHUFCBDg--\r
            """

            # Parse raw payload
            lines = payload.split("\n")
            start = lines.index("\r")
            end = len(lines) - 2
            lines = lines[start + 1:end]
            for i in range(len(lines)):
                lines[i] = lines[i].strip()
                lines[i] = list(filter(None, lines[i].split(",")))

            # Write to a csv file
            self.csv_file_path = os.path.join(CSV_STORAGE_PATH, self.filename)
            with open(self.csv_file_path, 'w') as file:
                writer = csv.writer(file)
                writer.writerows(lines)

        except Exception as err:
            raise Exception(err)

    def create_modular_input(self):
        """Create a modular input."""
        indicators_input_stanza = {
            "name": "{}://{}".format(INDICATORS_INPUT, self.filename_without_ext),
            "disabled": "true",
            "file_name": self.filename
        }
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/{}/configs/conf-inputs".format(
                    APP_NAME),
                self.sessionKey,
                postargs=indicators_input_stanza,
                method="POST",
                raiseAllErrors=True,
            )

        except Exception as err:
            if "409" in str(err):
                err = "Input is already created for this file. Try changing the file name."
            os.remove(self.csv_file_path)
            raise Exception(err)

    def handle_POST(self):
        """Handle POST requests from frontend."""
        try:
            payload = self.request["payload"]
            self.parse_and_save_csv(payload)
            self.create_modular_input()

        except Exception as err:
            raise Exception(err)

        finally:
            self.response.setHeader('content-type', 'application/json')
            response = json.dumps(
                '{"message":"File upload successful. Navigate to the Inputs dashboard to enable the data collection."}')
            self.response.write(response)

    # handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
