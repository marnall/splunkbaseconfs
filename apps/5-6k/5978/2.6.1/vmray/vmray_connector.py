# File: vmray_connector.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
import base64
import io
import os
import time
import zipfile
from typing import Any, BinaryIO, Optional, Union

# pylint: disable=import-error
import phantom.app as phantom
import phantom.rules as phantom_rules
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from rest_api import VMRayRESTAPIError  # pylint: disable=wrong-import-order, import-error
from rest_cmds import SummaryV2, VMRay  # pylint: disable=wrong-import-order
from vmray_consts import (
    ACTION_ID_VMRAY_DETONATE_FILE,
    ACTION_ID_VMRAY_DETONATE_URL,  # pylint: disable=wrong-import-order
    ACTION_ID_VMRAY_GET_FILE,
    ACTION_ID_VMRAY_GET_INFO,
    ACTION_ID_VMRAY_GET_IOCS,
    ACTION_ID_VMRAY_GET_REPORT,
    ACTION_ID_VMRAY_GET_SCREENSHOTS,
    ACTION_ID_VMRAY_GET_VTIS,
    DEFAULT_TIMEOUT,
    INDEX_LOG_DELIMITER,
    INDEX_LOG_FILE_NAME_POSITION,
    SAMPLE_TYPE_MAPPING,
    VMRAY_DEFAULT_PASSWORD,
    VMRAY_ERROR_ADD_VAULT,
    VMRAY_ERROR_CODE_MSG,
    VMRAY_ERROR_CONNECTIVITY_TEST,
    VMRAY_ERROR_DOWNLOAD_FAILED,
    VMRAY_ERROR_EXTRACTING_SCREENSHOTS,
    VMRAY_ERROR_FILE_EXISTS,
    VMRAY_ERROR_GET_IOCS,
    VMRAY_ERROR_GET_SUBMISSION,
    VMRAY_ERROR_GET_VTIS,
    VMRAY_ERROR_IOCS_NOT_FINISHED,
    VMRAY_ERROR_MALFORMED_ZIP,
    VMRAY_ERROR_MSG_UNAVAILABLE,
    VMRAY_ERROR_MULTIPART,
    VMRAY_ERROR_NO_SUBMISSIONS,
    VMRAY_ERROR_OPEN_ZIP,
    VMRAY_ERROR_REST_API,
    VMRAY_ERROR_SAMPLE_NOT_FOUND,
    VMRAY_ERROR_SERVER_CONNECTION,
    VMRAY_ERROR_SERVER_RES,
    VMRAY_ERROR_SUBMISSION_NOT_FINISHED,
    VMRAY_ERROR_SUBMIT_FILE,
    VMRAY_ERROR_UNSUPPORTED_HASH,
    VMRAY_ERROR_VTIS_NOT_FINISHED,
    VMRAY_INVALID_INTEGER_ERROR_MSG,
    VMRAY_JSON_API_KEY,
    VMRAY_JSON_DISABLE_CERT,
    VMRAY_JSON_SERVER,
    VMRAY_NEGATIVE_INTEGER_ERROR_MSG,
    VMRAY_PARSE_ERROR_MSG,
    VMRAY_SUCC_CONNECTIVITY_TEST,
)


# pylint: enable=import-error


class VMRayConnector(BaseConnector):
    def __init__(self) -> None:
        # Call the BaseConnectors init first
        super().__init__()
        self._api: VMRay = None

    @staticmethod
    def _validate_integer(action_result, parameter, key):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return (
                        action_result.set_status(phantom.APP_ERROR, VMRAY_INVALID_INTEGER_ERROR_MSG.format(key)),
                        None,
                    )

                parameter = int(parameter)
            except Exception:  # pylint: disable=broad-except
                return (
                    action_result.set_status(phantom.APP_ERROR, VMRAY_INVALID_INTEGER_ERROR_MSG.format(key)),
                    None,
                )

            if parameter < 0:
                return (
                    action_result.set_status(phantom.APP_ERROR, VMRAY_NEGATIVE_INTEGER_ERROR_MSG.format(key)),
                    None,
                )

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, exception):
        """This method is used to get appropriate error messages from the exception.
        :param exception: Exception object
        :return: error message
        """

        try:
            if exception.args:
                if len(exception.args) > 1:
                    error_code = exception.args[0]
                    error_msg = exception.args[1]
                elif len(exception.args) == 1:
                    error_code = VMRAY_ERROR_CODE_MSG
                    error_msg = exception.args[0]
            else:
                error_code = VMRAY_ERROR_CODE_MSG
                error_msg = VMRAY_ERROR_MSG_UNAVAILABLE
        except Exception:  # pylint: disable=broad-except
            error_code = VMRAY_ERROR_CODE_MSG
            error_msg = VMRAY_ERROR_MSG_UNAVAILABLE

        try:
            if error_code in VMRAY_ERROR_CODE_MSG:
                error_text = f"Error Message: {error_msg}"
            else:
                error_text = f"Error Code: {error_code}. Error Message: {error_msg}"
        except Exception:  # pylint: disable=broad-except
            self.debug_print("Error occurred while parsing error message")
            error_text = VMRAY_PARSE_ERROR_MSG

        return error_text

    def _test_connectivity(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))
        config = self.get_config()

        # get the server
        server = config.get(VMRAY_JSON_SERVER)
        api_key = config.get(VMRAY_JSON_API_KEY)
        disable_cert = config.get(VMRAY_JSON_DISABLE_CERT)

        self.save_progress("Querying server to check connectivity")

        # Progress
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES.format(server))

        try:
            VMRay(server, api_key, not disable_cert)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            self.save_progress(VMRAY_ERROR_CONNECTIVITY_TEST)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_CONNECTION.format(error_message))

        self.save_progress(VMRAY_SUCC_CONNECTIVITY_TEST)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_api(self, action_result) -> tuple[bool, VMRay]:
        if self._api is not None:
            return (phantom.APP_SUCCESS, self._api)

        config = self.get_config()

        # get the server
        server = config.get(VMRAY_JSON_SERVER)
        api_key = config.get(VMRAY_JSON_API_KEY)
        disable_cert = config.get(VMRAY_JSON_DISABLE_CERT)

        try:
            self._api = VMRay(server, api_key, not disable_cert)
            return (phantom.APP_SUCCESS, self._api)
        except Exception as exc:  # pylint: disable=broad-except
            self._api = None
            error_message = self._get_error_message_from_exception(exc)
            action_result.set_status(phantom.APP_ERROR, f"Error connecting to server. Details: {error_message}")
            return (action_result.get_status(), None)

    @staticmethod
    def _get_timeout(param: dict[str, Any]) -> int:
        try:
            timeout = int(param.get("timeout", DEFAULT_TIMEOUT))
            if timeout < 0:
                timeout = DEFAULT_TIMEOUT
        except (KeyError, TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT

        return timeout

    def _get_sample_by_hash(self, action_result, api: VMRay, hsh: str) -> tuple[bool, list[dict[str, Any]]]:
        self.save_progress(f"Searching for {hsh}")

        if len(hsh) == 32:
            res = api.get_sample_by_md5(hsh)
        elif len(hsh) == 40:
            res = api.get_sample_by_sha1(hsh)
        elif len(hsh) == 64:
            res = api.get_sample_by_sha256(hsh)
        else:
            return (
                action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_UNSUPPORTED_HASH),
                [],
            )

        if len(res) == 0:
            return (
                action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SAMPLE_NOT_FOUND),
                [],
            )

        return phantom.APP_SUCCESS, res

    def _iocs_finished_within_timeout(self, api: VMRay, sample_id: int, timeout: int, time_to_wait_min: int = 30) -> bool:
        seconds_waited = 0

        while api.get_sample_iocs(sample_id).get("status", "") != "finished":
            if timeout == 0 or seconds_waited >= timeout:
                return False

            self.send_progress("IOCs are not finished yet")
            time_to_wait = min(time_to_wait_min, timeout - seconds_waited)
            seconds_waited += time_to_wait
            self.send_progress(f"Waited {seconds_waited}/{timeout} seconds for IOCs")
            time.sleep(time_to_wait)

        return True

    def _vtis_finished_within_timeout(self, api: VMRay, sample_id: int, timeout: int, time_to_wait_min: int = 30) -> bool:
        seconds_waited = 0

        while api.get_sample_threat_indicators(sample_id).get("status", "") != "finished":
            if timeout == 0 or seconds_waited >= timeout:
                return False

            self.send_progress("VTIs are not finished yet")
            time_to_wait = min(time_to_wait_min, timeout - seconds_waited)
            seconds_waited += time_to_wait
            self.send_progress(f"Waited {seconds_waited}/{timeout} seconds for VTIs")
            time.sleep(time_to_wait)

        return True

    def _submission_finished_within_timeout(self, api: VMRay, submission_id: int, timeout: int) -> bool:
        seconds_waited = 0

        while not api.is_submission_finished(submission_id):
            if timeout == 0 or seconds_waited >= timeout:
                return False

            self.send_progress("Submission is not finished yet")
            time_to_wait = min(30, timeout - seconds_waited)
            seconds_waited += time_to_wait
            self.send_progress(f"Waited {seconds_waited}/{timeout} seconds for Submission")
            time.sleep(time_to_wait)

        return True

    def _handle_get_file(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))
        status, api = self._get_api(action_result)
        if api is None:
            return status

        self.debug_print("param", param)
        hsh = param["hash"]

        try:
            status, res = self._get_sample_by_hash(action_result, api, hsh)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Error occurred: {VMRAY_ERROR_SAMPLE_NOT_FOUND}. Details: {error_message}",
            )

        if phantom.is_fail(status):
            return action_result.get_status()

        try:
            if "sample_id" not in res[0]:
                return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SAMPLE_NOT_FOUND)

            if res[0]["sample_is_multipart"]:
                return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_MULTIPART)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        self.save_progress("Downloading file")

        vault_tmp_folder = Vault.get_vault_tmp_dir()
        zip_file_location = os.path.join(vault_tmp_folder, f"{hsh}.zip")
        file_location = os.path.join(vault_tmp_folder, hsh)
        if os.path.exists(zip_file_location) or os.path.exists(file_location):
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_FILE_EXISTS)

        with api.get_sample_file(res[0]["sample_id"]) as data:
            with open(zip_file_location, "wb") as fobj:
                fobj.write(data.read())

        try:
            zifi = zipfile.ZipFile(zip_file_location, "r")
        except Exception as exc:  # pylint: disable=broad-except
            os.remove(zip_file_location)
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_OPEN_ZIP}. {error_message}")

        zf_names = zifi.namelist()

        if len(zf_names) != 1:
            zifi.close()
            os.remove(zip_file_location)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_MALFORMED_ZIP)

        self.save_progress("Extracting file")

        try:
            with zifi.open(zf_names[0], "r", VMRAY_DEFAULT_PASSWORD) as ifobj:
                with open(file_location, "wb") as ofobj:
                    ofobj.write(ifobj.read())

        except Exception as exc:  # pylint: disable=broad-except
            if os.path.exists(file_location):
                os.remove(file_location)
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_MALFORMED_ZIP}. {error_message}")

        finally:
            zifi.close()
            os.remove(zip_file_location)

        try:
            vmray_sampletypes = [x["sample_type"] for x in res]
            phantom_sampletypes = []
            for sample_type in vmray_sampletypes:
                # sample type could be `custom` or `unknown`
                if sample_type not in SAMPLE_TYPE_MAPPING.keys():
                    continue

                phantom_sampletypes.append(SAMPLE_TYPE_MAPPING[sample_type])

            phantom_sampletypes = list(set(phantom_sampletypes))
            self.debug_print("phantom_sampletypes", phantom_sampletypes)

            self.save_progress("Adding file to vault")
            vlt_res = Vault.add_attachment(
                file_location,
                self.get_container_id(),
                file_name=res[0]["sample_filename"],
                metadata={
                    "size": res[0]["sample_filesize"],
                    "contains": phantom_sampletypes,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        if not vlt_res["succeeded"]:
            try:
                os.remove(file_location)
            except FileNotFoundError:
                pass

            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_ADD_VAULT)

        action_result.add_data({"vault_id": vlt_res["vault_id"]})
        action_result.update_summary({"vault_id": vlt_res["vault_id"]})

        self.save_progress("Finished")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_file(self, param: dict[str, Any]):
        action_result = self.add_action_result(ActionResult(dict(param)))
        status, api = self._get_api(action_result)
        if api is None:
            return status

        vault_id = param["vault_id"]
        file_name = param.get("file_name")
        try:
            _, _, vault_info = phantom_rules.vault_info(
                vault_id=vault_id,
                file_name=file_name,
            )
        except Exception:  # pylint: disable=broad-except
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Error while getting vault info for vault_id {vault_id}",
            )

        if len(vault_info) > 1:
            self.save_progress(f"Found multiple files for vault_id {vault_id}. Using the first one.")

        if len(vault_info) == 0:
            return action_result.set_status(phantom.APP_ERROR, f"No sample found for vault_id {vault_id}")

        vault_info = vault_info[0]

        file_path = vault_info.get("path")
        if not file_path:
            return action_result.set_status(phantom.APP_ERROR, f"Cannot find a path for vault id {vault_id}")

        self.save_progress(f"Submitting file {vault_id}")

        params = {}
        if param.get("comment"):
            params["comment"] = param.get("comment")
        if param.get("tags"):
            params["tags"] = param.get("tags")
        if param.get("type"):
            params["sample_type"] = param.get("type")
        if param.get("config"):
            params["user_config"] = param.get("config")
        if param.get("jobrules"):
            params["jobrule_entries"] = param.get("jobrules")

        if file_name:
            params["sample_filename_b64enc"] = base64.b64encode(file_name.encode()).decode()
        elif vault_info.get("name"):
            params["sample_filename_b64enc"] = base64.b64encode(vault_info["name"].encode()).decode()

        try:
            res = api.submit_file(file_path, params=params)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_SUBMIT_FILE}. Details: {error_message}")

        try:
            if res["errors"]:
                errors = [error.get("error_msg", "NO_ERROR_MSG_GIVEN") for error in res["errors"]]
                return action_result.set_status(phantom.APP_ERROR, ";".join(errors))

            submission_id = res["submissions"][0]["submission_id"]
            submission_url = res["submissions"][0]["submission_webif_url"]
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        submission_finished = True

        iocs_only = param.get("ioc_only", True)
        timeout = self._get_timeout(param)
        status, report = self._get_report(action_result, submission_id, timeout, iocs_only)
        if phantom.is_fail(status):
            if report:
                error_msg, _exc = report
                if error_msg == VMRAY_ERROR_SUBMISSION_NOT_FINISHED:
                    submission_finished = False
                else:
                    return action_result.set_status(phantom.APP_ERROR, f"{error_msg}, {_exc}")
                report = None
            else:
                return action_result.get_status()
        try:
            if report:
                for analysis in report["analyses"]:
                    action_result.add_data({"analysis": analysis})
                if report["reputation_lookup"]:
                    action_result.add_data({"reputation_lookup": report["reputation_lookup"][0]})
                action_result.update_summary(
                    {
                        "billing_type": report["billing_type"],
                        "recursive_submission_ids": report["recursive_submission_ids"],
                        "verdict": report["verdict"],
                    }
                )
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        action_result.update_summary(
            {
                "submission_id": submission_id,
                "url": submission_url,
                "submission_finished": submission_finished,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_url(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))
        status, api = self._get_api(action_result)
        if api is None:
            return status

        url = param["url"]

        self.save_progress(f"Submitting url {url}")

        params = {}
        if param.get("comment"):
            params["comment"] = param.get("comment")
        if param.get("tags"):
            params["tags"] = param.get("tags")
        if param.get("config"):
            params["user_config"] = param.get("config")
        if param.get("jobrules", "") != "":
            params["jobrule_entries"] = param.get("jobrules")

        try:
            res = api.submit_url(url, params=params)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_SUBMIT_FILE}. Details: {error_message}")

        try:
            if res["errors"]:
                errors = [error.get("error_msg", "NO_ERROR_MSG_GIVEN") for error in res["errors"]]
                return action_result.set_status(phantom.APP_ERROR, ";".join(errors))

            submission_id = res["submissions"][0]["submission_id"]
            submission_url = res["submissions"][0]["submission_webif_url"]
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        submission_finished = True

        iocs_only = param.get("ioc_only", True)
        timeout = self._get_timeout(param)
        status, report = self._get_report(action_result, submission_id, timeout, iocs_only)
        if phantom.is_fail(status):
            if report:
                error_msg, _exc = report
                if error_msg == VMRAY_ERROR_SUBMISSION_NOT_FINISHED:
                    submission_finished = False
                else:
                    return action_result.set_status(phantom.APP_ERROR, f"{error_msg}, {_exc}")
                report = None
            else:
                return action_result.get_status()
        try:
            if report:
                for analysis in report["analyses"]:
                    action_result.add_data({"analysis": analysis})
                if report["reputation_lookup"]:
                    action_result.add_data({"reputation_lookup": report["reputation_lookup"][0]})
                action_result.update_summary(
                    {
                        "billing_type": report["billing_type"],
                        "recursive_submission_ids": report["recursive_submission_ids"],
                        "verdict": report["verdict"],
                    }
                )
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        action_result.update_summary(
            {
                "submission_id": submission_id,
                "url": submission_url,
                "submission_finished": submission_finished,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_iocs(
        self, api: VMRay, sample_id: int, timeout: int, all_artifacts: bool = False
    ) -> Union[
        tuple[bool, Optional[tuple[str, Optional[Exception]]]],
        tuple[bool, dict[str, Any]],
    ]:
        try:
            if not self._iocs_finished_within_timeout(api, sample_id, timeout):
                return (phantom.APP_ERROR, (VMRAY_ERROR_IOCS_NOT_FINISHED, None))
        except VMRayRESTAPIError:
            return (phantom.APP_ERROR, (f"No sample found with ID '{sample_id}'.", None))

        self.save_progress("IOCs are finished")

        iocs: list = {}
        try:
            iocs = api.get_sample_iocs(sample_id, all_artifacts=all_artifacts).get("iocs", {})
        except Exception as exc:  # pylint: disable=broad-except
            return (phantom.APP_ERROR, (VMRAY_ERROR_GET_IOCS, exc))

        return (
            phantom.APP_SUCCESS,
            {
                "iocs": iocs,
                "sample_id": sample_id,
            },
        )

    def _handle_get_iocs(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))

        status, api = self._get_api(action_result)
        if api is None:
            return (status, None)

        ret_val, sample_id = self._validate_integer(action_result, param["sample_id"], "'sample_id' action parameter")
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        timeout = self._get_timeout(param)
        all_artifacts = param.get("all_artifacts", False)

        status, res = self._get_iocs(api, sample_id, timeout, all_artifacts=all_artifacts)
        if phantom.is_fail(status):
            if res:
                error_msg, exc = res
                action_result.set_status(phantom.APP_ERROR, error_msg, exc)
            return action_result.get_status()
        try:
            iocs = res["iocs"]
        except KeyError as exc:
            error = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error))

        try:
            sample_info = api.get_sample(sample_id)
        except Exception as exc:  # pylint: disable=broad-except
            return action_result.set_status(phantom.APP_ERROR, (VMRAY_ERROR_REST_API, exc))

        # convert severity to verdict
        if "sample_verdict" not in sample_info:
            verdict = SummaryV2.to_verdict(sample_info["sample_severity"])
            sample_info["sample_verdict"] = verdict

        action_result.add_data({"iocs": iocs, "sample_verdict": sample_info["sample_verdict"]})

        action_result.update_summary(
            {
                "sample_verdict": sample_info["sample_verdict"],
                "sample_id": sample_id,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_vtis(
        self, api: VMRay, sample_id: int, timeout: int
    ) -> Union[
        tuple[bool, Optional[tuple[str, Optional[Exception]]]],
        tuple[bool, dict[str, Any]],
    ]:
        try:
            if not self._vtis_finished_within_timeout(api, sample_id, timeout):
                return (phantom.APP_ERROR, (VMRAY_ERROR_VTIS_NOT_FINISHED, None))
        except VMRayRESTAPIError:
            return (phantom.APP_ERROR, (f"No sample found with ID '{sample_id}'.", None))

        self.save_progress("VTIs are finished")

        try:
            vtis = api.get_sample_threat_indicators(sample_id).get("threat_indicators", [])
        except Exception as exc:  # pylint: disable=broad-except
            return (phantom.APP_ERROR, (VMRAY_ERROR_GET_VTIS, exc))

        return (
            phantom.APP_SUCCESS,
            {
                "vtis": vtis,
                "sample_id": sample_id,
            },
        )

    def _handle_get_vtis(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))

        status, api = self._get_api(action_result)
        if api is None:
            return (status, None)

        ret_val, sample_id = self._validate_integer(action_result, param["sample_id"], "'sample_id' action parameter")
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        timeout = self._get_timeout(param)

        status, res = self._get_vtis(api, sample_id, timeout)
        if phantom.is_fail(status):
            if res:
                error_msg, exc = res
                action_result.set_status(phantom.APP_ERROR, error_msg, exc)
            return action_result.get_status()
        try:
            vtis = res["vtis"]
        except Exception as exc:  # pylint: disable=broad-except
            error = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error))

        try:
            sample_info = api.get_sample(sample_id)
        except Exception as exc:  # pylint: disable=broad-except
            return action_result.set_status(phantom.APP_ERROR, (VMRAY_ERROR_REST_API, exc))

        # convert severity to verdict
        if "sample_verdict" not in sample_info:
            verdict = SummaryV2.to_verdict(sample_info["sample_severity"])
            sample_info["sample_verdict"] = verdict

        action_result.add_data({"vtis": vtis, "sample_verdict": sample_info["sample_verdict"]})

        action_result.update_summary(
            {
                "vtis": vtis,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_report(
        self, action_result, submission_id: int, timeout: int, iocs_only: bool = True
    ) -> Union[
        tuple[bool, Optional[tuple[str, Optional[Exception]]]],
        tuple[bool, dict[str, Any]],
    ]:
        status, api = self._get_api(action_result)
        if api is None:
            return (status, None)

        try:
            if not self._submission_finished_within_timeout(api, submission_id, timeout):
                return (phantom.APP_ERROR, (VMRAY_ERROR_SUBMISSION_NOT_FINISHED, None))
        except VMRayRESTAPIError:
            return (phantom.APP_ERROR, (f"No submission found with ID '{submission_id}'.", None))

        self.save_progress("Submission is finished")

        submission: dict = {}
        submission_url: str = ""
        billing_type: str = ""
        sample_id: str = ""
        analyses: list = []
        try:
            submission = api.get_submission(submission_id)
            submission_url = submission["submission_webif_url"]
            billing_type = submission["submission_billing_type"]
            sample_id = submission["submission_sample_id"]
            self.save_progress("Getting results")
            analyses = api.get_analyses_by_submission_id(submission_id)
        except Exception as exc:  # pylint: disable=broad-except
            return (phantom.APP_ERROR, (VMRAY_ERROR_GET_SUBMISSION, exc))

        try:
            for analysis in analyses:
                # convert severity to verdict
                if "analysis_verdict" not in analysis:
                    verdict = SummaryV2.to_verdict(analysis["analysis_severity"])
                    analysis["analysis_verdict"] = verdict

                summary = {}
                if analysis.get("analysis_result_code", -1) == 1:
                    try:
                        # Skip verdict only quotas.
                        if analysis.get("analysis_billing_type") == "analyzer":
                            summary = api.get_report(analysis["analysis_id"], iocs_only)
                    except VMRayRESTAPIError:
                        continue

                    analysis["summary"] = summary
        except Exception as exc:  # pylint: disable=broad-except
            return (phantom.APP_ERROR, ("Error processing server response", exc))

        try:
            reputation_lookup = api.get_reputation_by_submission(submission_id)
        except Exception:  # pylint: disable=broad-except
            self.save_progress("Reputation lookup failed")
            reputation_lookup = None

        try:
            verdict = api.get_verdict_by_sample_id(sample_id)
        except Exception:  # pylint: disable=broad-except
            self.save_progress("Failed to fetch verdict")
            verdict = "n/a"

        try:
            recursive_submission_ids = api.get_child_submissions(submission_id)
        except Exception:  # pylint: disable=broad-except
            self.save_progress("Failed to fetch recursive submissions")
            recursive_submission_ids = None

        return (
            phantom.APP_SUCCESS,
            {
                "analyses": analyses,
                "billing_type": billing_type,
                "reputation_lookup": reputation_lookup,
                "verdict": verdict,
                "submission_url": submission_url,
                "recursive_submission_ids": recursive_submission_ids,
            },
        )

    def _handle_get_report(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, submission_id = self._validate_integer(action_result, param["submission_id"], "'submission_id' action parameter")
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        timeout = self._get_timeout(param)

        iocs_only = param.get("ioc_only", True)
        status, res = self._get_report(action_result, submission_id, timeout, iocs_only)
        if phantom.is_fail(status):
            if res:
                error_msg, exc = res
                action_result.set_status(phantom.APP_ERROR, error_msg, exc)
            return action_result.get_status()
        try:
            analyses = res["analyses"]
            billing_type = res["billing_type"]
            recursive_submission_ids = res["recursive_submission_ids"]
            reputation_lookup = res["reputation_lookup"]
            verdict = res["verdict"]
            submission_url = res["submission_url"]
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        for analysis in analyses:
            action_result.add_data({"analysis": analysis})

        if reputation_lookup:
            action_result.add_data({"reputation_lookup": reputation_lookup[0]})

        action_result.update_summary(
            {
                "verdict": verdict,
                "submission_id": submission_id,
                "url": submission_url,
                "billing_type": billing_type,
                "recursive_submission_ids": recursive_submission_ids,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_info(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))
        status, api = self._get_api(action_result)
        if api is None:
            return status

        self.debug_print("param", param)
        timeout = self._get_timeout(param)

        try:
            status, res = self._get_sample_by_hash(action_result, api, param["hash"])
        except Exception:  # pylint: disable=broad-except
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SAMPLE_NOT_FOUND)

        if phantom.is_fail(status):
            return action_result.get_status()

        self.save_progress("Check for finished submissions")

        try:
            sample_id = res[0]["sample_id"]
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SERVER_RES.format(error_message))

        has_finished_submission = False
        seconds_waited = 0
        while True:
            submissions = api.call("GET", f"/rest/submission/sample/{sample_id}")
            if not submissions:
                return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_NO_SUBMISSIONS)

            has_finished_submission = any([sub.get("submission_finished", False) for sub in submissions])

            if has_finished_submission or timeout == 0:
                break
            if seconds_waited >= timeout:
                break

            self.send_progress("No submission finished yet")
            time_to_wait = min(30, timeout - seconds_waited)
            seconds_waited += time_to_wait
            self.send_progress(f"Waited {seconds_waited}/{timeout} seconds")
            time.sleep(time_to_wait)

        if not has_finished_submission:
            return action_result.set_status(phantom.APP_ERROR, VMRAY_ERROR_SUBMISSION_NOT_FINISHED)

        try:
            sample_info = api.get_sample(sample_id)
        except Exception as exc:  # pylint: disable=broad-except
            return action_result.set_status(phantom.APP_ERROR, (VMRAY_ERROR_REST_API, exc))

        try:
            recursive_sample_ids = api.get_recursive_samples(sample_id)
        except Exception as exc:  # pylint: disable=broad-except
            return action_result.set_status(phantom.APP_ERROR, (VMRAY_ERROR_REST_API, exc))

        # convert severity to verdict
        if "sample_verdict" not in sample_info:
            verdict = SummaryV2.to_verdict(sample_info["sample_severity"])
            sample_info["sample_verdict"] = verdict

        action_result.add_data(sample_info)
        action_result.update_summary(
            {
                "recursive_sample_ids": recursive_sample_ids,
                "score": sample_info["sample_score"],
                "verdict": sample_info["sample_verdict"],
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_ordered_screenshot_file_names(self, action_result: "ActionResult", archive: "zipfile.ZipFile") -> tuple[bool, Optional[list[str]]]:
        """
        Return a list with screenshot file names ordered by the order they have been taken in during the analysis.
        """
        ordered_screenshots = []
        try:
            with archive.open("screenshots/index.log") as index_log:
                for line in io.TextIOWrapper(index_log, "utf-8"):
                    file_name = line.split(INDEX_LOG_DELIMITER)[INDEX_LOG_FILE_NAME_POSITION].strip()
                    ordered_screenshots.append(file_name)
        except Exception as exc:
            error_message = self._get_error_message_from_exception(exc)
            return (action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_EXTRACTING_SCREENSHOTS}. {error_message}"), None)
        return phantom.APP_SUCCESS, ordered_screenshots

    def _convert_to_vault_file_name(self, file_name: str, analysis_id: int, index: int) -> str:
        """
        Converts the file name from the internal format to the format we want to show in the vault.
        Example:
            analysis_2_screenshot_3.png
            The above is a screenshot from an analysis with the ID 2. It is the 4th screenshot that has been taken
            during that analysis.
        """
        return f"analysis_{analysis_id}_screenshot_{index}{os.path.splitext(file_name)[1]}"

    def _download_screenshots(self, action_result: "ActionResult", analysis_id: int) -> tuple[bool, Optional[BinaryIO]]:
        status, api = self._get_api(action_result)
        if api is None:
            return status, None
        try:
            screenshots_zip_file = api.get_screenshots(analysis_id)
        except Exception as exc:  # pylint: disable=broad-except
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_DOWNLOAD_FAILED}. {error_message}"), None
        return phantom.APP_SUCCESS, screenshots_zip_file

    def _add_screenshots_to_vault(self, action_result: "ActionResult", screenshots_zip_file: BinaryIO, analysis_id: int) -> bool:
        try:
            with zipfile.ZipFile(screenshots_zip_file) as screenshots_archive:
                ret_val, ordered_screenshots = self._get_ordered_screenshot_file_names(action_result, screenshots_archive)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                for index, file_name in enumerate(ordered_screenshots):
                    screenshot_data = screenshots_archive.read(os.path.join("screenshots", file_name))
                    vault_file_name = self._convert_to_vault_file_name(file_name, analysis_id, index)
                    resp = Vault.create_attachment(screenshot_data, self.get_container_id(), file_name=vault_file_name)
                    action_result.add_data({"vault_id": resp.get("vault_id"), "file_name": vault_file_name})
                action_result.update_summary({"downloaded_screenshots": len(ordered_screenshots)})
        except Exception as exc:
            error_message = self._get_error_message_from_exception(exc)
            return action_result.set_status(phantom.APP_ERROR, f"{VMRAY_ERROR_EXTRACTING_SCREENSHOTS}. {error_message}")
        return phantom.APP_SUCCESS

    def _handle_get_screenshots(self, param: dict[str, Any]) -> bool:
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, analysis_id = self._validate_integer(action_result, param["analysis_id"], "'analysis_id' action parameter")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Downloading screenshots")
        ret_val, screenshots_zip_file = self._download_screenshots(action_result, analysis_id)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Extracting screenshots and adding them to the vault")
        ret_val = self._add_screenshots_to_vault(action_result, screenshots_zip_file, analysis_id)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Finished")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param: dict[str, Any]) -> bool:
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        elif action_id == ACTION_ID_VMRAY_GET_FILE:
            ret_val = self._handle_get_file(param)
        elif action_id == ACTION_ID_VMRAY_DETONATE_FILE:
            ret_val = self._handle_detonate_file(param)
        elif action_id == ACTION_ID_VMRAY_DETONATE_URL:
            ret_val = self._handle_detonate_url(param)
        elif action_id == ACTION_ID_VMRAY_GET_VTIS:
            ret_val = self._handle_get_vtis(param)
        elif action_id == ACTION_ID_VMRAY_GET_IOCS:
            ret_val = self._handle_get_iocs(param)
        elif action_id == ACTION_ID_VMRAY_GET_REPORT:
            ret_val = self._handle_get_report(param)
        elif action_id == ACTION_ID_VMRAY_GET_INFO:
            ret_val = self._handle_get_info(param)
        elif action_id == ACTION_ID_VMRAY_GET_SCREENSHOTS:
            ret_val = self._handle_get_screenshots(param)

        return ret_val
