# File: awsinspector_connector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# Phantom App imports
import ast
import datetime
import json
import sys

import phantom.app as phantom

# Usage of the consts file is recommended
import requests
from boto3 import Session, client
from botocore.config import Config
from dateutil.tz import tzlocal
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from awsinspector_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AwsInspectorConnector(BaseConnector):
    def __init__(self):
        """
        The constructor for AwsInspectorConnector class.
        """

        # Call the BaseConnectors init first
        super().__init__()

        self._state = None
        self._region = None
        self._access_key = None
        self._secret_key = None
        self._session_token = None
        self._proxy = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS.
        """

        self._state = self.load_state()

        config = self.get_config()

        self._region = AWSINSPECTOR_REGION_DICT.get(config[AWSINSPECTOR_JSON_REGION])

        self._proxy = {}
        env_vars = config.get("_reserved_environment_variables", {})
        if "HTTP_PROXY" in env_vars:
            self._proxy["http"] = env_vars["HTTP_PROXY"]["value"]
        if "HTTPS_PROXY" in env_vars:
            self._proxy["https"] = env_vars["HTTPS_PROXY"]["value"]

        if config.get("use_role"):
            credentials = self._handle_get_ec2_role()
            if not credentials:
                return self.set_status(phantom.APP_ERROR, AWSINSPECTOR_ROLE_CREDENTIALS_FAILURE_MSG)
            self._access_key = credentials.access_key
            self._secret_key = credentials.secret_key
            self._session_token = credentials.token

            return phantom.APP_SUCCESS

        self._access_key = config.get("access_key")
        self._secret_key = config.get("secret_key")

        if not (self._access_key and self._secret_key):
            return self.set_status(phantom.APP_ERROR, AWSINSPECTOR_BAD_ASSET_CONFIG_MSG)

        return phantom.APP_SUCCESS

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _handle_get_ec2_role(self):
        session = Session(region_name=self._region)
        credentials = session.get_credentials()
        return credentials

    def _create_client(self, action_result, param=None):
        """This function is used to create a client which is necessary for Boto call

        :param action_result: Object of ActionResult class
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        boto_config = None
        if self._proxy:
            boto_config = Config(proxies=self._proxy)

        # Try getting and using temporary assume role credentials from parameters
        temp_credentials = dict()
        if param and "credentials" in param:
            try:
                temp_credentials = ast.literal_eval(param["credentials"])
                self._access_key = temp_credentials.get("AccessKeyId", "")
                self._secret_key = temp_credentials.get("SecretAccessKey", "")
                self._session_token = temp_credentials.get("SessionToken", "")

                self.save_progress("Using temporary assume role credentials for action")
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, f"Failed to get temporary credentials:{e}")

        try:
            if self._access_key and self._secret_key:
                self.debug_print("Creating boto3 client with API keys")
                self._client = client(
                    "inspector",
                    region_name=self._region,
                    aws_access_key_id=self._access_key,
                    aws_secret_access_key=self._secret_key,
                    aws_session_token=self._session_token,
                    config=boto_config,
                )
            else:
                self.debug_print("Creating boto3 client without API keys")
                self._client = client("inspector", region_name=self._region, config=boto_config)

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Could not create boto3 client: {e}")

        return phantom.APP_SUCCESS

    def _make_boto_call(self, action_result, method, **kwargs):
        """This function is used to make the Boto call.

        :param action_result: Object of ActionResult class
        :param method: Name of the method which is to be called in Boto call
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR) and response data of Boto call
        """

        try:
            boto_func = getattr(self._client, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), None)

        try:
            resp_json = boto_func(**kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "boto3 call to Inspector failed", e), None)

        return phantom.APP_SUCCESS, resp_json

    def _handle_test_connectivity(self, param):
        """This function is used to handle the test connectivity action.

        :param param: Dictionary of input parameters
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        ret_val, response = self._make_boto_call(action_result, "list_assessment_targets", maxResults=1)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return ret_val

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_targets(self, param):
        """This function is used to fetch targets of specific AWS account.

        :param param: Dictionary of input parameters
        :return: list of targets and their info for the specific AWS account
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        target_name = param.get("target_name")
        limit = param.get("limit")

        if (limit and not str(limit).isdigit()) or limit == 0:
            return action_result.set_status(phantom.APP_ERROR, AWSINSPECTOR_INVALID_LIMIT)

        filter = {}
        if target_name:
            filter["assessmentTargetNamePattern"] = target_name

        kwargs = {}
        kwargs["filter"] = filter

        list_targets = self._paginator("list_assessment_targets", limit, action_result, **kwargs)

        if list_targets is None:
            return action_result.get_status()

        tz = tzlocal()
        self.debug_print(tz)

        for target in list_targets:
            ret_val, res = self._make_boto_call(action_result, "describe_assessment_targets", assessmentTargetArns=[target])

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if res.get("assessmentTargets"):
                assessment_target = res.get("assessmentTargets")[0]
            else:
                failure_code = res.get("failedItems", {}).get(target, {}).get("failureCode")
                error_message = failure_code if failure_code else "Unknown error"
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error occurred while fetching the details of the assessment target: {target}. Error: {error_message}",
                )

            for key, value in list(assessment_target.items()):
                if isinstance(value, datetime.datetime):
                    assessment_target[key] = str(value)

            action_result.add_data(assessment_target)

        summary = action_result.update_summary({})
        summary["total_targets"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_templates(self, param):
        """This function is used to fetch templates that correspond to the assessment targets.

        :param param: Dictionary of input parameters
        :return: list of templates and their info for the specific AWS account
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        target_arns = param.get("target_arns")
        if param.get("target_arns"):
            target_arns = [target_arn.strip() for target_arn in target_arns.split(",")]
            target_arns = " ".join(target_arns).split()

        template_name = param.get("template_name")
        limit = param.get("limit")

        if (limit and not str(limit).isdigit()) or limit == 0:
            return action_result.set_status(phantom.APP_ERROR, AWSINSPECTOR_INVALID_LIMIT)

        filter = {}
        kwargs = {}

        if target_arns:
            kwargs["assessmentTargetArns"] = target_arns

        if template_name:
            filter["namePattern"] = template_name
        kwargs["filter"] = filter

        list_templates = self._paginator("list_assessment_templates", limit, action_result, **kwargs)

        if list_templates is None:
            return action_result.get_status()

        for template in list_templates:
            ret_val, res = self._make_boto_call(action_result, "describe_assessment_templates", assessmentTemplateArns=[template])

            if res.get("assessmentTemplates"):
                assessment_template = res.get("assessmentTemplates")[0]
            else:
                failure_code = res.get("failedItems", {}).get(template, {}).get("failureCode")
                error_message = failure_code if failure_code else "Unknown error"
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error occurred while fetching the details of the assessment template: {template}. Error: {error_message}",
                )

            for key, value in list(assessment_template.items()):
                if isinstance(value, datetime.datetime):
                    assessment_template[key] = str(value)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            action_result.add_data(assessment_template)

        summary = action_result.update_summary({})
        summary["total_templates"] = action_result.get_data_size()

        self.save_progress("Handle list templates succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_target(self, param):
        """This function is used to create a new assessment target to the specific AWS account.

        :param param: Dictionary of input parameters
        :return: ARN of the assessment target that is created by this action.
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        target_name = param["target_name"]
        resource_group_arn = param.get("resource_group_arn")

        kwargs = {}
        kwargs["assessmentTargetName"] = target_name

        if param.get("resource_group_arn"):
            kwargs["resourceGroupArn"] = resource_group_arn

        ret_val, response = self._make_boto_call(action_result, "create_assessment_target", **kwargs)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            del response["ResponseMetadata"]
        except:
            pass

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["total_target_arn"] = action_result.get_data_size()

        self.save_progress("Handle add target succeeded")
        return action_result.set_status(phantom.APP_SUCCESS, "Target successfully added")

    def _handle_run_assessment(self, param):
        """This function is used to start the assessment run specified by the ARN of the assessment template.

        :param param: Dictionary of input parameters
        :return: ARN of the assessment run and their information
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        template_arn = param["template_arn"]
        assessment_run_name = param.get("assessment_run_name")

        kwargs = {}
        kwargs["assessmentTemplateArn"] = template_arn

        if param.get("assessment_run_name"):
            kwargs["assessmentRunName"] = assessment_run_name

        ret, assessment_run = self._make_boto_call(action_result, "start_assessment_run", **kwargs)
        if phantom.is_fail(ret):
            return action_result.get_status()

        assessment_run_arn = assessment_run.get("assessmentRunArn")

        if not assessment_run_arn:
            return action_result.get_status()

        # for arn in assessment_run_arns:
        ret_val, res = self._make_boto_call(action_result, "describe_assessment_runs", assessmentRunArns=[assessment_run_arn])

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if res.get("assessmentRuns"):
            assessment_run = res.get("assessmentRuns")[0]
        else:
            failure_code = res.get("failedItems", {}).get(assessment_run_arn, {}).get("failureCode")
            error_message = failure_code if failure_code else "Unknown error"
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Error occurred while fetching the details of the assessment run: {assessment_run_arn}. Error: {error_message}",
            )

        for key, value in list(assessment_run.items()):
            if isinstance(value, datetime.datetime):
                assessment_run[key] = str(value)
            if isinstance(value, list):
                for val in value:
                    if isinstance(val, dict):
                        for k1, v1 in val.items():
                            if isinstance(v1, datetime.datetime):
                                val[k1] = str(v1)

        try:
            del res["ResponseMetadata"]
        except:
            pass

        action_result.add_data(assessment_run)

        summary = action_result.update_summary({})
        summary["assessment_run_arn"] = assessment_run_arn

        self.save_progress("Handle run assessment succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_findings(self, param):
        """This function is used to fetch findings that are generated by the assessment runs.

        :param param: Dictionary of input parameters
        :return: list of findings and their information
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        filter = {}

        assessment_run_arns = param.get("assessment_run_arns")

        if param.get("assessment_run_arns"):
            assessment_run_arns = [assessment_run_arn.strip() for assessment_run_arn in assessment_run_arns.split(",")]
            assessment_run_arns = " ".join(assessment_run_arns).split()

        severities = param.get("severities")
        if param.get("severities"):
            severities = [severity.strip() for severity in severities.split(",")]
            severities = " ".join(severities).split()
            filter.update({"severities": severities})

        limit = param.get("limit")

        if (limit and not str(limit).isdigit()) or limit == 0:
            return action_result.set_status(phantom.APP_ERROR, AWSINSPECTOR_INVALID_LIMIT)

        kwargs = {}
        if param.get("assessment_run_arns"):
            kwargs["assessmentRunArns"] = assessment_run_arns
        kwargs["filter"] = filter

        list_findings = self._paginator("list_findings", limit, action_result, **kwargs)

        if list_findings is None:
            return action_result.get_status()

        while list_findings:
            ret_val, res = self._make_boto_call(action_result, "describe_findings", findingArns=list_findings[: min(10, len(list_findings))])

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            findings = res.get("findings")
            if findings:
                for finding in findings:
                    for key, value in list(finding.items()):
                        if isinstance(value, datetime.datetime):
                            finding[key] = str(value)
            else:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error occurred while fetching the details of the findings: {list_findings[: min(10, len(list_findings))]!s}",
                )

            for finding_detail in findings:
                action_result.add_data(finding_detail)

            del list_findings[: min(10, len(list_findings))]

        summary = action_result.update_summary({})
        summary["total_findings"] = action_result.get_data_size()

        self.save_progress("Handle get findings succeeded")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_target(self, param):
        """This function is used to delete the existing assessment target from the specific AWS account.

        :param param: Dictionary of input parameters
        :return: Status (phantom.APP_ERROR/phantom.APP_SUCCESS), target is deleted successfully
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        if phantom.is_fail(self._create_client(action_result, param)):
            return action_result.get_status()

        target_arn = param["target_arn"]

        kwargs = {}
        kwargs["assessmentTargetArn"] = target_arn

        ret_val, response = self._make_boto_call(action_result, "delete_assessment_target", **kwargs)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            del response["ResponseMetadata"]
        except:
            pass

        action_result.add_data(response)

        self.save_progress("Handle delete target succeeded")
        return action_result.set_status(phantom.APP_SUCCESS, "Target is deleted successfully")

    def _paginator(self, method_name, limit, action_result, **kwargs):
        """
        This action is used to create an iterator that will paginate through responses from called methods.

        :param method_name: Name of method whose response is to be paginated
        :param action_result: Object of ActionResult class
        :param **kwargs: Dictionary of Input parameters
        """

        list_items = list()
        next_token = None
        dic_map = {
            "list_targets": "assessmentTargetArns",
            "list_templates": "assessmentTemplateArns",
            "get_findings": "findingArns",
            "delete_target": "assessmentTargetArns",
        }

        set_name = dic_map.get(self.get_action_identifier())

        while True:
            if next_token:
                ret_val, response = self._make_boto_call(
                    action_result, method_name, nextToken=next_token, maxResults=AWSINSPECTOR_MAX_PER_PAGE_LIMIT, **kwargs
                )
            else:
                ret_val, response = self._make_boto_call(action_result, method_name, maxResults=AWSINSPECTOR_MAX_PER_PAGE_LIMIT, **kwargs)

            if phantom.is_fail(ret_val):
                return None

            if response.get(set_name):
                list_items.extend(response.get(set_name))

            if limit and len(list_items) >= limit:
                return list_items[:limit]

            next_token = response.get("nextToken")
            if not next_token:
                break

        return list_items

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: Dictionary which contains information about the actions to be executed
        :return: Status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.debug_print("action_id", self.get_action_identifier())
        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_targets": self._handle_list_targets,
            "list_templates": self._handle_list_templates,
            "add_target": self._handle_add_target,
            "delete_target": self._handle_delete_target,
            "run_assessment": self._handle_run_assessment,
            "get_findings": self._handle_get_findings,
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            response = requests.get(login_url, verify=verify, timeout=AWSINSPECTOR_DEFAULT_TIMEOUT)
            csrftoken = response.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = f"csrftoken={csrftoken}"
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=AWSINSPECTOR_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AwsInspectorConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
