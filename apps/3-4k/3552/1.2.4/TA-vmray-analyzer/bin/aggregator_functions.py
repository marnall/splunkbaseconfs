# pylint: disable=invalid-name
import json
import logging
import re


def get_timing(vmray_api=None, analysis_id=None):
    try:
        timing = vmray_api.get_timing(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d error while fetching timing",
            analysis_id
        )
        return None

    if timing is None:
        logging.warning(
            "WORKER analysis_id=%d analysis without timing",
            analysis_id
        )
        return None

    try:
        timing = timing.read()
        timing = json.loads(timing)
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d exception while reading timing",
            analysis_id
        )
        return None
    except ValueError:
        logging.exception(
            "WORKER analysis_id=%d exception while loading timing json",
            analysis_id
        )
        return None

    return {"timing": timing}


def get_size(vmray_api=None, analysis_id=None):
    try:
        size = vmray_api.get_size(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d exception while receivin size",
            analysis_id
        )
        return None

    if size is None:
        logging.debug(
            "WORKER analysis_id=%d analysis without size",
            analysis_id
        )
        return None

    try:
        size = size.read()
        size = json.loads(size)
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d exception while reading size",
            analysis_id
        )
        return None
    except ValueError:
        logging.exception(
            "WORKER analysis_id=%d exception while loading size json",
            analysis_id
        )
        return None

    return {"size": size}


def get_submission(submission=None):
    my_submission = dict(submission)
    submission_id = my_submission["submission_id"]
    submission_comment = my_submission.get("submission_comment", None)
    if submission_comment is not None:
        # hopefully this will change soon but at the
        # moment this is how it is implemented
        try:
            match = re.match(
                r"#sample_info# (\{.*?\})",
                submission_comment
            )
        except TypeError:
            logging.exception(
                "WORKER submission_id=%d unanticipated submission_comment.",
                submission_id
            )
            return {"submission": my_submission}

        if match is None:
            return {"submission": my_submission}

        try:
            feed_info = json.loads(match.group(1))
        except ValueError:
            logging.exception(
                "WORKER submission_id=%d Error loading json "
                "from submission_comment",
                submission_id
            )
            return {"submission": my_submission}

        my_submission["feed_info"] = feed_info

    return {"submission": my_submission}


def get_sample(vmray_api=None, sample_id=None):
    try:
        sample = vmray_api.get_sample(sample_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER sample_id=%d exception while receiving sample",
            sample_id
        )
        return None
    return {"sample": sample}


def get_export_file_intel(vmray_api=None, analysis=None):
    my_analysis = dict(analysis)
    submission_id = my_analysis["analysis_submission_id"]
    try:
        submission = vmray_api.get_submission(submission_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER submission_id=%d exception while receiving sample",
            submission_id
        )
        return None
    my_analysis["submission"] = submission
    return {"export_file_intel": my_analysis}


def get_vti_result(vmray_api=None, analysis_id=None):
    try:
        vti_result = vmray_api.get_vti_result(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d exception while receiving vti_result",
            analysis_id
        )
        return None

    if vti_result is None:
        logging.debug(
            "WORKER analysis_id=%d analysis without vti_result",
            analysis_id
        )
        return None

    try:
        vti_result = vti_result.read()
        vti_result = json.loads(vti_result)
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d exception while reading vti_result",
            analysis_id
        )
        return None
    except ValueError:
        logging.exception(
            "WORKER analysis_id=%d exception while loading vti_result json",
            analysis_id
        )
        return None

    return {"vti_result": vti_result}


def get_stix(vmray_api=None, analysis_id=None):
    try:
        stix = vmray_api.get_stix(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d Error receiving stix file",
            analysis_id
        )
        return None

    if stix is None:
        logging.debug(
            "WORKER analysis_id=%d analysis without stix file",
            analysis_id
        )
        return None

    try:
        stix = stix.read()
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d Error reading stix file",
            analysis_id
        )
        return None

    return {"stix": stix}


def get_glog(vmray_api=None, analysis_id=None):
    try:
        glog = vmray_api.get_glog(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d Error receiving glog file",
            analysis_id
        )
        return None

    if glog is None:
        logging.debug(
            "WORKER analysis_id=%d analysis without glog file",
            analysis_id
        )
        return None

    try:
        glog = glog.read()
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d Error reading glog file",
            analysis_id
        )
        return None

    return {"glog": glog}


def get_yara(vmray_api=None, analysis_id=None):
    try:
        yara = vmray_api.get_yara(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d exception while receivin yara",
            analysis_id
        )
        return None

    if yara is None:
        logging.debug(
            "WORKER analysis_id=%d analysis without yara",
            analysis_id
        )
        return None

    try:
        yara = yara.read()
        yara = json.loads(yara)
    except IOError:
        logging.exception(
            "WORKER analysis_id=%d exception while reading yara",
            analysis_id
        )
        return None
    except ValueError:
        logging.exception(
            "WORKER analysis_id=%d exception while loading yara json",
            analysis_id
        )
        return None

    return {"yara": yara}


def get_summary(vmray_api=None, analysis_id=None):
    logging.debug("get_summary for analysis #%s", analysis_id)
    try:
        summary = vmray_api.get_summary(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d exception while receiving summary",
            analysis_id
        )
        return None

    return {"summary": summary}


def get_extracted_strings(vmray_api=None, analysis_id=None):
    logging.debug("get_extracted_strings for analysis #%s", analysis_id)
    try:
        summary = vmray_api.get_summary(analysis_id)
    except Exception:  # pylint: disable=broad-except
        logging.exception(
            "WORKER analysis_id=%d exception while receiving summary",
            analysis_id
        )
        return None

    extracted_strings_files = summary.get("extracted_strings_files", [])

    result = {}
    for extracted_strings_file in extracted_strings_files:
        file_name = extracted_strings_file["archive_path"]
        try:
            response = vmray_api.get_file_from_archive(analysis_id, file_name)
            all_strings = unicode(response.read().decode('utf-8', errors="ignore"))
        except Exception:  # pylint: disable=broad-except
            logging.exception(
                "WORKER analysis_id=%d exception while receiving extracted_strings",
                analysis_id
            )
            return None
        result[extracted_strings_file["id"]] = all_strings

    return {"extracted_strings": result}


def get_analysis(data=None):
    return {"analysis": dict(data)}
