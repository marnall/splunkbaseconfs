import json
import logging
import re

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from vmraylib.summary_v2 import SummaryV2

if TYPE_CHECKING:
    from vmraylib.rest_cmds import VMRay


class EngineType(Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"
    WEB = "web"


ENGINE_MAP = {
    "default": EngineType.DYNAMIC,
    "documents": EngineType.DYNAMIC,
    "scripts": EngineType.DYNAMIC,
    "browser": EngineType.WEB,
    "msi": EngineType.DYNAMIC,
    "static": EngineType.STATIC,
}


def get_analysis_engine_type(score_type: str, analysis_id: int) -> Optional[str]:
    try:
        return ENGINE_MAP[score_type].value
    except KeyError:
        logging.error("Could not determine engine type for analysis %d.", analysis_id)

    return None


def get_extended_analysis_info(vmray_api: "VMRay", analysis: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
    submission = vmray_api.get_submission(analysis["analysis_submission_id"])

    extended_analysis_info = {
        "submission_sample_type": analysis.get("analysis_sample_type"),
        "submission_sample_verdict": submission.get("submission_sample_verdict"),
        "submission_verdict_reason_code": submission.get("submission_sample_verdict_reason_code"),
        "analysis_sample_verdict": analysis.get("analysis_sample_verdict"),
        "analysis_sample_verdict_reason_code": analysis.get("analysis_sample_verdict_reason_code"),
        "analysis_verdict": analysis.get("analysis_verdict"),
        "analysis_verdict_reason_code": analysis.get("analysis_verdict_reason_code"),
        "analysis_user_account_id": analysis.get("analysis_user_account_id"),
        "analysis_user_account_name": analysis.get("analysis_user_account_name"),
        "analysis_user_account_type": analysis.get("analysis_user_account_type"),
        "analysis_type": analysis_type,
    }

    return {"extended_analysis_info": extended_analysis_info}


def get_timing(vmray_api: "VMRay", analysis_id: int):
    timing = vmray_api.get_timing(analysis_id)

    if timing is None:
        return {}

    return {"timing": json.loads(timing.read())}


def get_size(vmray_api: "VMRay", analysis_id: int):
    size = vmray_api.get_size(analysis_id)

    if size is None:
        return {}

    return {"size": json.loads(size.read())}


def get_submission(submission: Dict[str, Any], sample_info: Dict[str, Any]) -> Dict[str, Any]:
    additional_info = {
        "submission_sample_type": sample_info["sample_type"],
        "submission_sample_filesize": sample_info["sample_filesize"],
    }
    submission.update(additional_info)

    submission_id = submission["submission_id"]
    submission_comment = submission.get("submission_comment", None)
    if submission_comment is not None:
        # hopefully this will change soon but at the
        # moment this is how it is implemented
        try:
            match = re.match(r"#sample_info# (\{.*?\})", submission_comment)
        except TypeError:
            logging.exception("WORKER submission_id=%d unanticipated submission_comment.", submission_id)
            return {"submission": submission}

        if match is None:
            return {"submission": submission}

        try:
            feed_info = json.loads(match.group(1))
        except ValueError:
            logging.exception("WORKER submission_id=%d Error loading json from submission_comment", submission_id)
            return {"submission": submission}

        submission["feed_info"] = feed_info

    return {"submission": submission}


def download_sample_info(vmray_api: "VMRay", sample_id: int):
    logging.debug("download_sample_info for sample #%s", sample_id)
    return {"sample": vmray_api.get_sample(sample_id)}


def get_sample_info(sample: Dict[str, Any]) -> Dict[str, Any]:
    if "sample" not in sample:
        raise ValueError("No sample information found")
    return sample


def get_summary(vmray_api: "VMRay", analysis_id: int):
    logging.debug("get_summary for analysis #%s", analysis_id)
    return {"summary": vmray_api.get_summary(analysis_id)}


def download_summary_v2(vmray_api: "VMRay", analysis_id: int):
    logging.debug("download_summary_v2 for analysis #%s", analysis_id)
    return {"summary_v2": vmray_api.get_summary_v2(analysis_id)}


def get_summary_v2(summary_v2: Dict[str, Any]) -> Dict[str, Any]:
    if "summary_v2" not in summary_v2:
        raise ValueError("No summary v2 found")
    return summary_v2


def get_extracted_strings(vmray_api: "VMRay", analysis_id: int, summary_v2: Dict[str, Any]):
    logging.debug("get_extracted_strings for analysis #%s", analysis_id)
    processes = SummaryV2(summary_v2).get("processes", {})
    result: List[Dict[str, Any]] = []

    for process in processes.values():
        file = process.get("ref_extracted_function_strings_file", None)
        if not file:
            continue

        # check for required attributes
        if "archive_path" not in file or "image_name" not in process or "monitor_id" not in process:
            continue
        response = vmray_api.get_file_from_archive(analysis_id, file["archive_path"])
        all_strings = response.read().decode("utf-8", errors="ignore").splitlines()

        if not all_strings:
            continue

        result.append({
            "process_image_name": process["image_name"],
            "process_monitor_id": process["monitor_id"],
            "strings": all_strings
        })

    return {"extracted_strings": result}


def enrich_analysis_info(vmray_api: "VMRay", analysis: Dict[str, Any]) -> Dict[str, Any]:
    sample_info = vmray_api.get_sample(analysis["analysis_sample_id"])
    additional_info = {
        "analysis_sample_type": sample_info.get("sample_type"),
        "analysis_sample_verdict": sample_info.get("sample_verdict"),
        "analysis_sample_verdict_reason_code": sample_info.get("sample_verdict_reason_code"),
        "analysis_sample_filesize": sample_info.get("sample_filesize"),
    }

    if "analysis_user_config_config" in analysis:
        config = analysis["analysis_user_config_config"]
        if isinstance(config, str):
            user_config = json.loads(config)
        elif isinstance(config, dict):
            user_config = config
        else:
            user_config = {}
            analysis_id = analysis["analysis_sample_id"]
            logging.error(f"Unsupported user config type {type(config)} for analysis #{analysis_id}")

        net_scheme_id = user_config.get("net_scheme_id")
        user_config_len = len(user_config) - 1 if net_scheme_id is not None else len(user_config)
        additional_info["analysis_user_config_len"] = user_config_len
        additional_info["analysis_user_net_scheme_id"] = net_scheme_id

    if not vmray_api.restricted_mode:
        additional_info["analysis_sample_verdict_reason_description"] = sample_info.get(
            "sample_verdict_reason_description"
        )

    return additional_info


def get_analysis(vmray_api: "VMRay", analysis: Dict[str, Any]) -> Dict[str, Any]:
    additional_info = enrich_analysis_info(vmray_api, analysis)
    analysis.update(additional_info)

    return {"analysis": analysis}


def get_malware_configuration(vmray_api: "VMRay", analysis_id: int, summary_v2: Dict[str, Any]):
    logging.debug("get_malware_configuration for analysis #%s", analysis_id)
    malware_configs = SummaryV2(summary_v2).get("malware_configurations", {})
    result: List[Dict[str, Any]] = []

    for config in malware_configs.values():
        file = config.get("ref_file")
        if not file:
            continue

        # check for required attributes
        if "archive_path" not in file:
            continue

        response = vmray_api.get_file_from_archive(analysis_id, file["archive_path"])
        malware_config = json.load(response)

        if not malware_config:
            continue

        result.append({"config": malware_config})

    return {"malware_configurations": result}
