import splunk.rest as rest
import os
import json
import csv
import re

ERROR_MSG_REGEX = r'.+\"REST Error \[[\d]+\]:\s+.+\s+--\s+([\s\S]*)\"\.\s*See splunkd\.log(\/python.log)? for more details\.'  # noqa 501
INDEX_BLACKLIST_REGEX = r"^_.*$"
NAME_REGEX = r"^[a-zA-Z]\w*$"
SYS_TYPE_HEADER = "system_type"
ACC_TYPE_HEADER = "account_type"
SYS_HEADER = "system"
GLOBAL_ACC_HEADER = "global_account"
CONFIG_SYS = "system"
ACC_TYPE_MAPPING = {"flashblade": "flash_blade_account", "flasharray": "flash_array_account"}
SYSTEM_HEADERS = ["name", ACC_TYPE_HEADER, "api_token", "server_address"]
INPUT_HEADERS = ["name", "interval", "index", "input_type", GLOBAL_ACC_HEADER, "start_date"]
ALL_INPUT_HEADERS = ["name", "interval", "index", "input_type", GLOBAL_ACC_HEADER, "start_date", "historical_data"]
CREATE_ACC_ENDPOINT = "TA_purestorage_unified_account"
CREATE_INPUT_ENDPOINT = "TA_purestorage_unified_purestorage_unified_input"
INPUT_NAME_LEN = 100
SYS_NAME_LEN = 50
APP_NAME = __file__.split(os.sep)[-3]


class BatchCreate(rest.BaseRestHandler):
    """Batch update the system/Input configurations."""

    def validate_headers(self, config_type, headers):
        """Function to validate headers."""
        missing_headers = []
        incorrect_headers = []
        if config_type == CONFIG_SYS:
            expected_headers = SYSTEM_HEADERS
            mandatory_headers = SYSTEM_HEADERS
        else:
            expected_headers = INPUT_HEADERS
            mandatory_headers = ALL_INPUT_HEADERS
        for each in headers:
            if each not in mandatory_headers:
                incorrect_headers.append(each)
        for each in expected_headers:
            if each not in headers:
                missing_headers.append(each)

        if (len(missing_headers) > 0 or len(incorrect_headers) > 0):
            err_msg = ""
            if len(missing_headers):
                err_msg += "Headers : {} is/are missing from CSV file.\t".format(",".join(missing_headers))
            if len(incorrect_headers):
                err_msg += "Headers : {} is/are incorrect.".format(",".join(incorrect_headers))
            raise Exception(err_msg)

    def parse_validate_payload(self, payload):
        """Parsing and validating the pauload."""
        # Parse raw payload
        lines = payload.split("\n")
        start = lines.index("\r")
        config_type = lines[-3].strip()
        end = len(lines) - 6
        lines = lines[start + 1:end]
        if len(lines) == 1:
            raise Exception("The uploaded CSV file contains only headers and no corresponding data.")
        if config_type == CONFIG_SYS:
            lines[0] = lines[0].replace(SYS_TYPE_HEADER, ACC_TYPE_HEADER)
        else:
            lines[0] = lines[0].replace(SYS_HEADER, GLOBAL_ACC_HEADER)
        headers_list = lines[0].strip("\r").split(",")
        headers_list = [i.strip("\"").strip("'").strip() for i in headers_list]
        for i in range(1, len(lines)):
            lines[i] = str(i + 1) + "," + lines[i]

        lines[0] = "line_num," + ",".join(headers_list)
        csv_data = csv.DictReader(lines, restkey="extra", restval="")
        csv_reader = (dict((k, v.strip()) for k, v in row.items() if (v and k != "extra")) for row in csv_data)
        self.validate_headers(config_type, headers_list)
        return config_type, csv_reader

    def get_accounts_list(self):
        """Get list of configured system for the app."""
        try:
            resp, content = rest.simpleRequest(
                "/servicesNS/nobody/{}/properties/ta_purestorage_unified_account".format(
                    APP_NAME),
                self.sessionKey,
                getargs={"output_mode": "json"},
                method="GET",
                raiseAllErrors=True,
            )
            if resp.status in [200, 201]:
                acc_data_list = json.loads(content.decode("utf-8")).get("entry")
                accounts_list = []
                for each in acc_data_list:
                    accounts_list.append(each.get("name"))
                return accounts_list
            else:
                raise Exception("Response status : {}".format(resp.status))
        except Exception as e:
            message = "Some error occurred while obtaining list of systems : {}".format(str(e))
            raise Exception(message)

    def validate_name(self, name, config_type):
        """Validates name of the inputs/systems."""
        if (config_type == CONFIG_SYS):
            if name is None or (len(name) > SYS_NAME_LEN) and (len(name) <= 0):
                raise Exception("Length of Name should be between 1 and {}".format(str(SYS_NAME_LEN)))
        else:
            if name is None or (len(name) > INPUT_NAME_LEN) and (len(name) <= 0):
                raise Exception("Length of Name should be between 1 and {}".format(str(INPUT_NAME_LEN)))
        regex = re.compile(NAME_REGEX)
        if not regex.match(name):
            raise Exception("Name must start with a letter and followed by alphabetic letters, digits or underscores.")

    def parse_error(self, err_msg):
        """Parsing array to get the error message only."""
        match = re.search(ERROR_MSG_REGEX, err_msg)
        if match:
            err_msg = match.group(1)
            try:
                error_dict = json.loads(err_msg)
                if error_dict.get("messages"):
                    err_msg = error_dict.get("messages")[0].get("text")
            except Exception:
                pass
            return err_msg
        return err_msg

    def batch_create(self, config_type, csv_dict):
        """Creating the inputs/systems sequentially."""
        err_msg = []
        self.err_flag = 0
        self.resp_flag = 0
        if config_type == CONFIG_SYS:
            endpoint = "{}/".format(CREATE_ACC_ENDPOINT)
        else:
            accounts_list = self.get_accounts_list()
            endpoint = "{}/".format(CREATE_INPUT_ENDPOINT)
        for each in csv_dict:
            try:
                self.line_num = each.get("line_num")
                del each["line_num"]
                if not any(each.values()):
                    continue
                self.validate_name(each.get("name"), config_type)
                if config_type == CONFIG_SYS:
                    each[ACC_TYPE_HEADER] = ACC_TYPE_MAPPING.get(each.get(ACC_TYPE_HEADER, None),
                                                                 each.get(ACC_TYPE_HEADER, None))
                else:
                    if each.get(GLOBAL_ACC_HEADER) is None:
                        raise Exception("The following required arguments are missing: {}".format(SYS_HEADER))
                    if each.get(GLOBAL_ACC_HEADER) not in accounts_list:
                        raise Exception("System {} not present".format(each.get(GLOBAL_ACC_HEADER)))
                    # If you don't give historical_data, then error comes while hitting inputs endpoint
                    # historical_data is needed only for inputs and not account tab
                    if not each.get("historical_data"):
                        each["historical_data"] = "0"
                    if each.get("historical_data").lower() not in ["0", "1", "true", "false", "yes", "no"]:
                        raise Exception("The value of historical_data should be from 0, 1, true, false, yes, no")
                    if each.get("historical_data").lower() in ["0", "false", "no"]:
                        each["historical_data"] = "0"
                    if each.get("historical_data").lower() in ["1", "true", "yes"]:
                        each["historical_data"] = "1"
                resp, content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/{}".format(
                        APP_NAME, endpoint),
                    self.sessionKey,
                    postargs=each,
                    method="POST",
                    timeout=180,
                    raiseAllErrors=True,
                )
                if resp.status in [200, 201]:
                    self.resp_flag = 1
                else:
                    raise Exception("Some unexpected error occurred. Response status : {}".format(resp.status))
            except Exception as err:
                self.err_flag = 1
                identifier = "on line no.{}".format(self.line_num)
                error_message = self.parse_error(str(err))
                error_message = error_message.replace(ACC_TYPE_HEADER, SYS_TYPE_HEADER)
                err_msg.append("{} {} : {}".format(config_type.capitalize(), identifier, str(error_message)))
        if self.err_flag == 1:
            raise Exception(json.dumps(err_msg))

    def handle_POST(self):
        """POST the data to create configurations."""
        try:
            payload = self.request["payload"]
            config_type, csv_data = self.parse_validate_payload(payload)
            self.batch_create(config_type, csv_data)
        except Exception as e:
            raise Exception(str(e))
        if self.resp_flag == 1:
            self.response.setHeader('content-type', 'application/json')
            response = json.dumps(
                '{"message":"Batch creation completed successfull"}')
            self.response.write(response)
        else:
            raise Exception("The uploaded CSV file contains only headers and no corresponding data.")

    handle_GET = handle_POST
