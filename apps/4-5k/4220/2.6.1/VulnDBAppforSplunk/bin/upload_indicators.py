"""Rest handler that saves uploaded csv files."""
import os
import re
import json
import sys
import csv
import splunk
from splunk import rest
from splunk.clilib.bundle_paths import make_splunkhome_path

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
CSV_EXTENSION = ".csv"
CSV_STORAGE_PATH = make_splunkhome_path(
    ["etc", "apps", APP_NAME, "local", "bulk"])

APP_BIN_PATH = make_splunkhome_path(
    ["etc", "apps", APP_NAME, "bin"])

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or APP_NAME in path]
new_paths.insert(0, APP_BIN_PATH)
sys.path = new_paths

import vulndb_logger_manager

FILENAME_REGEX = r"^[a-zA-Z]\w*$"
FILENAME_EXTRACT_REGEX = r"filename=\"(.*)\""


class Indicators(splunk.rest.BaseRestHandler):
    """Class for getting UI validation message through custom endpoint."""

    def chunk_data(self, csvReader, chunk_size, collection):
        """Returns the data in chunks."""
        if collection == "InstalledProducts_to_VulnDB_ProductID_collection":
            collection_field = "InstalledProductID"
        else:
            collection_field = "AssetID"
        data = []
        for row in csvReader:
            if len(data) == chunk_size:
                yield data
                data = []
            row['_key'] = row.get(collection_field)
            data.append(row)
        yield data

    def get_field_list(self, collection_token):
        """Get the list of allowed fields in Lookup."""
        fieldset = {
            "DiscoveredAssets_General_collection": [
                "AssetID",
                "Name",
                "Description",
                "Class",
                "Type",
                "Business_Function",
                "Support_Status",
                "Operational_Status",
                "Environment",
                "First_Discovered_Date",
                "Last_Discovered_Date",
            ],
            "DiscoveredAssets_Risk_collection": [
                "AssetID",
                "Average_CVSS",
                "DateAdded",
                "DateModified",
                "Max_CVSS",
                "Value",
                "Threat_Likelihood",
                "Vulnerability_Exposure",
                "Vulns_Count",
                "First_Discovered_Date",
                "Last_Discovered_Date",
                "ExactVersionMatch",
            ],
            "DiscoveredAssets_Tech_collection": [
                "Active",
                "Amazon_EC2_ID",
                "AssetID",
                "Collector",
                "DNS_Domain",
                "DateAdded",
                "FQDN",
                "Hostname",
                "IP_Address",
                "IPv6",
                "Last_Booted",
                "Last_Seen",
                "MAC_Address",
                "Model",
                "Netbios",
                "Network",
                "Operating_System",
                "Origin",
                "URL",
                "Vendor",
                "First_Discovered_Date",
                "Last_Discovered_Date",
            ],
            "InstalledProducts_to_VulnDB_ProductID_collection": [
                "InstalledProductID",
                "Product_Name",
                "Product_Vendor",
                "Collector",
                "VulnDB_ProductID",
                "Verified",
                "DateAdded",
                "VulnDB_ProductName",
                "First_Discovered_Date",
                "Last_Discovered_Date",
                "Product_Version",
            ],
        }
        return fieldset[collection_token]

    def get_post_data(self, chunk, old_data_chunk, list_of_fields):
        """
        Function to modify the data to be posted.

        Keeping the old value as it is , in case user adds blank value
        Keeping the old value as it is , in case user does not add the field in CSV.
        """
        for field in list_of_fields:
            if (not chunk.get(field)) and field in old_data_chunk:
                chunk[field] = old_data_chunk[field]
        return chunk

    def get_old_data(self, rest_endpoint):
        """Get the old data of lookup."""
        response, content = rest.simpleRequest(
            rest_endpoint, sessionKey=self.sessionKey, method='GET', raiseAllErrors=True)
        content = content.decode('utf-8')
        source_data = json.loads(content)
        for source in source_data:
            del source["_user"]
        return source_data

    def field_validation(self, chunk_data_list, collection):
        """Function to validate the AssetID and InstalledProductID field."""
        if collection == "InstalledProducts_to_VulnDB_ProductID_collection":
            collection_field = "InstalledProductID"
        else:
            collection_field = "AssetID"
        for chunk in chunk_data_list:
            if len(chunk[collection_field]) == 0 or not chunk[collection_field].isdigit():
                return False, collection_field
        return True, collection_field

    def parse_and_save_csv(self, payload, logger):
        """Save uploaded csv files to local/bulk folder."""
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
            Content-Disposition: form-data; name="token"\r
            \r
            DiscoveredAssets_General_collection\r    #Collection(Lookup) Name
            ------WebKitFormBoundarygjRKNK6yjzMeHNsK--

            """
            # Parse raw payload
            lines = payload.split("\n")
            start = lines.index("\r")
            end = len(lines) - 6
            collection_token = lines[len(lines) - 3]
            lines = lines[start + 1:end]

            if len(collection_token) == 0:
                raise Exception("Please choose a Lookup from the dropdown ")

            new_list = []
            for i in range(len(lines)):
                lines[i] = lines[i].strip()
                if len(lines[i]) != 0:
                    new_list.append(lines[i])

            for i in range(len(new_list)):
                new_list[i] = list(map(lambda a: a.strip('"'), list(new_list[i].split(","))))

            replaced_header = []
            list_of_fields = self.get_field_list(collection_token.strip())

            # Modify the field : Remove space from fields in Pascal Case and add replace space with '_'
            for field in new_list[0]:
                if field.strip() in ("Exact Version Match", "Date Added", "Date Modified"):
                    field = "".join(field.split())
                field = "_".join(field.split())
                if field not in list_of_fields:
                    raise Exception("Invalid header/s in the attached CSV file. \
                        Please correct the valid headers as listed below.")
                replaced_header.append(field)

            new_list[0] = replaced_header

            if collection_token.strip() == "InstalledProducts_to_VulnDB_ProductID_collection":
                if "InstalledProductID" not in new_list[0]:
                    raise Exception("There is no column header named InstalledProductID in the attached CSV.")
            else:
                if "AssetID" not in new_list[0]:
                    raise Exception("There is no column header named AssetID in the attached CSV.")

            # Write to a csv file
            self.csv_file_path = os.path.join(CSV_STORAGE_PATH, self.filename)
            with open(self.csv_file_path, 'w') as file:
                writer = csv.writer(file)
                writer.writerows(new_list)

            rest_endpoint = '/servicesNS/nobody/' + APP_NAME + \
                            '/storage/collections/data/' + collection_token.strip()

            old_data = self.get_old_data(rest_endpoint)
            old_data_dict = {}
            for data in old_data:
                old_data_dict[data["_key"]] = data

            with open(self.csv_file_path) as csvf:
                csvReader = csv.DictReader(csvf)
                # Convert each row into a dictionary
                for chunk_data_list in self.chunk_data(csvReader, 2, collection_token.strip()):
                    validate, collection_field = self.field_validation(chunk_data_list, collection_token.strip())
                    if not validate:
                        raise Exception("The value/s in field " + collection_field + " must be of numeric type.")

                    if len(old_data) > 0:
                        for chunk in chunk_data_list:
                            if chunk["_key"] in old_data_dict:
                                if chunk != old_data_dict[chunk["_key"]]:
                                    post_data = self.get_post_data(chunk, old_data_dict[chunk["_key"]], list_of_fields)
                                    try:
                                        response, content = rest.simpleRequest(
                                            rest_endpoint + "/" + post_data["_key"],
                                            sessionKey=self.sessionKey,
                                            jsonargs=json.dumps(post_data),
                                            method='POST',
                                            raiseAllErrors=True
                                        )
                                    except Exception as err:
                                        raise Exception(err)
                            else:
                                old_keys_data = self.get_old_data(rest_endpoint)
                                old_datakeys = []
                                for data in old_keys_data:
                                    old_datakeys.append(data["_key"])
                                if chunk["_key"] not in old_datakeys:
                                    try:
                                        response, content = rest.simpleRequest(
                                            rest_endpoint,
                                            sessionKey=self.sessionKey,
                                            jsonargs=json.dumps(chunk),
                                            method='POST',
                                            raiseAllErrors=True
                                        )
                                    except Exception as err:
                                        raise Exception(err)
                    else:
                        try:
                            rest_endpoint = rest_endpoint + '/batch_save'
                            rest.simpleRequest(
                                rest_endpoint,
                                sessionKey=self.sessionKey,
                                method='POST',
                                jsonargs=json.dumps(chunk_data_list),
                                raiseAllErrors=True)
                        except Exception as err:
                            raise Exception(err)
            os.remove(self.csv_file_path)
        except Exception as err:
            all_files = []
            all_files = os.listdir(CSV_STORAGE_PATH)
            if self.filename in all_files:
                self.csv_file_path = os.path.join(CSV_STORAGE_PATH, self.filename)
                os.remove(self.csv_file_path)
            raise Exception(err)

    def handle_POST(self):
        """Handle POST requests from frontend."""
        try:
            logger = vulndb_logger_manager.setup_logging("vulndb_app_logger", self.sessionKey)
            logger.info("Started updating the Lookup table")
            payload = self.request["payload"]
            self.parse_and_save_csv(payload, logger)
            logger.info("Lookup table updated successfully.")
        except Exception as err:
            raise Exception(err)

        finally:
            self.response.setHeader('content-type', 'application/json')
            response = json.dumps(
                '{"message":"Lookup table updated successfully"}')
            self.response.write(response)

    # handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
