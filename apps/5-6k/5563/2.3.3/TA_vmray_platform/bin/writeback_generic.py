""" Writeback functions for all generic events (not depending on summary v1/v2)"""

import json
import logging

from typing import Any, Dict

import splunklib.modularinput as smi


def write_analysis_event(ev_writer=None, stanza=None, _time=None, index=None,
                         sourcetype=None, data=None):

    data_to_write = data.get("analysis", None)
    if data_to_write is None:
        logging.warning("Could not write analysis event because data is missing")
        return

    extended_analysis_info = get_extended_analysis_info(data, "analysis")
    data_to_write.update(extended_analysis_info)

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing analysis event analysis_id=%d", data_to_write.get("analysis_id", -1))
    ev_writer.write_event(event)


def write_submission_event(ev_writer=None, stanza=None, _time=None, index=None,
                           sourcetype=None, data=None):

    data_to_write = data.get("submission", None)
    if data_to_write is None:
        logging.warning("Could not write submission event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing submission event submission_id=%d", data_to_write.get("submission_id", -1))
    ev_writer.write_event(event)


def write_sample_event(ev_writer=None, stanza=None, _time=None, index=None,
                       sourcetype=None, data=None):

    data_to_write = data.get("sample", None)
    if data_to_write is None:
        logging.warning("Could not write sample event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing sample event sample_id=%d", data_to_write.get("sample_id", -1))
    ev_writer.write_event(event)


def write_timing_event(ev_writer=None, stanza=None, _time=None, index=None,
                       sourcetype=None, data=None):
    analysis_data = data.get("analysis")
    extended_analysis_info = get_extended_analysis_info(data, "timing")
    timing_data = data.get("timing")
    if analysis_data is None or timing_data is None:
        logging.warning("Could not write timing event because data is missing")
        return

    event_data = {
        "analysis_id": analysis_data["analysis_id"],
        "timing": timing_data,
        **extended_analysis_info,
    }
    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(event_data)

    logging.debug("Writing timing event analysis_id=%d", analysis_data.get("analysis_id", -1))
    ev_writer.write_event(event)


def write_size_event(ev_writer=None, stanza=None, _time=None, index=None,
                     sourcetype=None, data=None):

    analysis_data = data.get("analysis", None)
    extended_analysis_info = get_extended_analysis_info(data, "size")
    size_data = data.get("size", None)
    if analysis_data is None or size_data is None:
        logging.warning("Could not write size event because data is missing")
        return

    event_data = {
        "analysis_id": analysis_data["analysis_id"],
        "size": size_data,
        **extended_analysis_info,
    }
    event = smi.Event(stanza=stanza, time=_time, index=index,
                      sourcetype=sourcetype)
    event.data = json.dumps(event_data)

    logging.debug("Writing size event analysis_id=%d", analysis_data.get("analysis_id", -1))
    ev_writer.write_event(event)


def write_extracted_strings_event(ev_writer=None, stanza=None, _time=None, index=None,
                                  sourcetype=None, data=None):

    analysis = data.get("analysis", None)
    extended_analysis_info = get_extended_analysis_info(data, "extracted_strings")
    extracted_strings = data.get("extracted_strings", None)

    if extracted_strings is None or analysis is None:
        logging.warning("Could not write extracted strings event because data is missing")
        return

    for event_data in extracted_strings:
        enrich_event_data(event_data, analysis)
        event_data.update(extended_analysis_info)

        event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
        event.data = json.dumps(event_data)

        logging.debug("Writing extracted strings event analysis_id=%d", analysis.get("analysis_id", -1))
        ev_writer.write_event(event)


def write_malware_configuration_event(ev_writer=None, stanza=None, _time=None, index=None,
                                  sourcetype=None, data=None):

    analysis = data.get("analysis")
    extended_analysis_info = get_extended_analysis_info(data, "malware_configuration")
    malware_configs = data.get("malware_configurations")

    if malware_configs is None or analysis is None:
        logging.warning("Could not write malware configuration event because data is missing")
        return

    for event_data in malware_configs:
        enrich_event_data(event_data, analysis)
        event_data.update(extended_analysis_info)

        event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
        event.data = json.dumps(event_data)

        logging.debug("Writing malware configuration event analysis_id=%d", analysis.get("analysis_id", -1))
        ev_writer.write_event(event)


def enrich_event_data(event_data, analysis):
    # some attributes have only been introduced in newer version, therefore always use .get()
    event_data["analysis_id"] = analysis.get("analysis_id")
    event_data["sample_id"] = analysis.get("analysis_sample_id")
    event_data["submission_id"] = analysis.get("analysis_submission_id")
    event_data["sample_type"] = analysis.get("analysis_jobrule_sampletype")
    event_data["sample_sha256"] = analysis.get("analysis_sample_sha256")
    event_data["vm_name"] = analysis.get("analysis_vm_name")
    event_data["configuration_name"] = analysis.get("analysis_configuration_name")
    event_data["platform"] = analysis.get("analysis_platform")


def get_extended_analysis_info(data: Dict[str, Any], event_name: str) -> Dict[str, Any]:
    extended_analysis_info = data.get("extended_analysis_info", {})
    if extended_analysis_info is None:
        logging.warning("Could not extend `%s` event because data is missing", event_name)
        return {}

    return extended_analysis_info
