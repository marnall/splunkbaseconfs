# pylint: disable=invalid-name

############################################################################
# Writeback functions. Assemble the info per event and write it to splunk
############################################################################

import copy
import json
import logging

import splunklib.modularinput as smi


def write_analysis_event(ev_writer=None, stanza=None, _time=None, index=None,
                         sourcetype=None, data=None):

    data_to_write = data.get("analysis", None)
    if data_to_write is None:
        logging.warning("Could not write analysis event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing analysis event")
    ev_writer.write_event(event)


def write_submission_event(ev_writer=None, stanza=None, _time=None, index=None,
                           sourcetype=None, data=None):

    data_to_write = data.get("submission", None)
    if data_to_write is None:
        logging.warning("Could not write submission event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing submission event")
    ev_writer.write_event(event)


def write_sample_event(ev_writer=None, stanza=None, _time=None, index=None,
                       sourcetype=None, data=None):

    data_to_write = data.get("sample", None)
    if data_to_write is None:
        logging.warning("Could not write sample event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(data_to_write)

    logging.debug("Writing sample event")
    ev_writer.write_event(event)


def write_extracted_strings_event(ev_writer=None, stanza=None, _time=None, index=None,
                                  sourcetype=None, data=None):

    summary_data = data.get("summary", None)
    analysis_data = data.get("analysis", None)
    extracted_strings = data.get("extracted_strings", None)

    if summary_data is None or extracted_strings is None or analysis_data is None:
        logging.warning("Could not write extracted strings event because data is missing")
        return

    output_extracted_strings = {
        "extracted_strings_files": copy.deepcopy(summary_data["extracted_strings_files"]),
        "analysis_id": analysis_data["analysis_id"],
        "sample_id": summary_data["sample_details"]["id"],
        "sha256_hash": summary_data["sample_details"].get("sha256_hash", None)
        }

    strip_type_version(output_extracted_strings)
    strip(output_extracted_strings, ["archive_path"])

    # Process
    for el in output_extracted_strings.get("extracted_strings_files", []):
        el["extracted_strings"] = extracted_strings.get(el["id"], "").splitlines()

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(output_extracted_strings)

    logging.debug("Writing extracted strings event")
    ev_writer.write_event(event)


def write_stix_event(ev_writer=None, stanza=None, _time=None, index=None,
                     sourcetype=None, data=None):

    data_to_write = data.get("stix", None)
    if data_to_write is None:
        logging.warning("Could not write stix event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = data_to_write

    logging.debug("Writing stix event")
    ev_writer.write_event(event)


def write_glog_event(ev_writer=None, stanza=None, _time=None, index=None,
                     sourcetype=None, data=None):

    data_to_write = data.get("glog", None)
    if data_to_write is None:
        logging.warning("Could not write glog event because data is missing")
        return

    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = data_to_write

    logging.debug("Writing glog event")
    ev_writer.write_event(event)


def write_timing_event(ev_writer=None, stanza=None, _time=None, index=None,
                       sourcetype=None, data=None):
    analysis_data = data.get("analysis", None)
    timing_data = data.get("timing", None)
    if analysis_data is None or timing_data is None:
        logging.warning("Could not write timing event because data is missing")
        return

    event_data = {
        "analysis_id": analysis_data["analysis_id"],
        "timing": timing_data
    }
    event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
    event.data = json.dumps(event_data)

    logging.debug("Writing timing event")
    ev_writer.write_event(event)


def write_size_event(ev_writer=None, stanza=None, _time=None, index=None,
                     sourcetype=None, data=None):

    analysis_data = data.get("analysis", None)
    size_data = data.get("size", None)
    if analysis_data is None or size_data is None:
        logging.warning("Could not write size event because data is missing")
        return

    event_data = {
        "analysis_id": analysis_data["analysis_id"],
        "size": size_data
    }
    event = smi.Event(stanza=stanza, time=_time, index=index,
                      sourcetype=sourcetype)
    event.data = json.dumps(event_data)

    logging.debug("Writing size event")
    ev_writer.write_event(event)


def write_vti_result_event(ev_writer=None, stanza=None, _time=None,
                           index=None, sourcetype=None, data=None):

    analysis_data = data.get("analysis", None)
    vti_result_data = data.get("vti_result", None)
    if analysis_data is None:
        logging.error("Could not write vti_result event because json data is missing")
        return

    if vti_result_data is None:
        if analysis_data["analysis_result_code"] == 1:
            logging.error(
                (
                    "Could not write vti_result event because data is missing, "
                    "even though analysis was successful. analysis_id %d"
                ),
                analysis_data["analysis_id"]
            )
        return

    output_dict = copy.deepcopy(vti_result_data)
    output_dict["analysis_id"] = analysis_data["analysis_id"]

    # clean up the dict it is of the new format analyzer version 2.0.1
    if "vti_rule_matches" in output_dict:
        for elem in output_dict["vti_rule_matches"]:
            del elem["artifacts"]
            del elem["ref_gfncalls"]
            # the meaning of type and version fields changed so we remove all of them
        strip_type_version(output_dict)

    event = smi.Event(stanza=stanza, time=_time, index=index,
                      sourcetype=sourcetype)
    event.data = json.dumps(output_dict)

    logging.debug("Writing vti_result event")
    ev_writer.write_event(event)


def write_yara_event(ev_writer=None, stanza=None, _time=None, index=None,
                     sourcetype=None, data=None):

    analysis_data = data.get("analysis", None)
    yara_data = data.get("yara", None)
    if analysis_data is None:
        logging.warning("Could not write yara event because data is missing")
        return

    if yara_data is None:
        if analysis_data["analysis_result_code"] == 1:
            logging.error(
                (
                    "Could not write yara event because data is missing, "
                    "even though analysis was successful. analysis_id %d"
                ),
                analysis_data["analysis_id"]
            )
        return

    output_dict = copy.deepcopy(yara_data)
    strip_type_version(output_dict)
    output_dict["analysis_id"] = analysis_data["analysis_id"]
    event = smi.Event(stanza=stanza, time=_time, index=index,
                      sourcetype=sourcetype)
    event.data = json.dumps(output_dict)

    logging.debug("Writing yara event")
    ev_writer.write_event(event)


def strip(obj, keys):
    """delete keys from dict recursively, also through lists"""
    if isinstance(obj, dict):
        for _key in keys:
            if _key in obj:
                del obj[_key]
        for _, val in obj.items():
            strip(val, keys)
    elif isinstance(obj, list):
        for elem in obj:
            strip(elem, keys)


def strip_type_version(dic):
    strip(dic, ["version", "type"])


class SummaryEventWriter(object):  # pylint:disable=useless-object-inheritance

    @staticmethod
    def _write_event_generic(meta_data, sub_dict, ev_writer=None,
                             stanza=None, _time=None, index=None, sourcetype=None, strip_keys=None):
        if sub_dict:
            output_dict = copy.deepcopy(sub_dict)
            strip_type_version(output_dict)
            strip(output_dict, ["sha1_hash", "md5_hash"])
            if strip_keys:
                strip(output_dict, strip_keys)
            output_dict.update(meta_data)
            event = smi.Event(stanza=stanza, time=_time, index=index, sourcetype=sourcetype)
            event.data = json.dumps(output_dict)

            logging.debug("Writing generic event")
            ev_writer.write_event(event)
        else:
            logging.warning("No data available for source type: %s" % sourcetype)

    @staticmethod
    def _write_event_artifacts(analysis_data, summary_data, ev_writer=None,
                               stanza=None, _time=None, index=None):
        output_artifacts = {"artifacts": copy.deepcopy(summary_data["artifacts"])}
        output_artifacts["analysis_id"] = analysis_data["analysis_id"]
        output_artifacts["sample_id"] = summary_data["sample_details"]["id"]
        output_artifacts["sha256_hash"] = summary_data["sample_details"].get("sha256_hash", None)
        # output_artifacts["sha1_hash"] = summary_data["sample_details"]["sha1_hash"]
        # output_artifacts["md5_hash"] = summary_data["sample_details"]["md5_hash"]
        strip_type_version(output_artifacts)
        strip(output_artifacts, ["sha1_hash", "md5_hash"])
        event_artifact = smi.Event(stanza=stanza, time=_time, index=index,
                                   sourcetype="vmray:artifacts")
        event_artifact.data = json.dumps(output_artifacts)
        logging.debug("Writing summary artifacts")
        ev_writer.write_event(event_artifact)

    @staticmethod
    def _write_event_extracted_files(analysis_data, summary_data, ev_writer=None,
                                     stanza=None, _time=None, index=None):
        output_extfiles = {"extracted_files": copy.deepcopy(summary_data["extracted_files"])}
        output_extfiles["analysis_id"] = analysis_data["analysis_id"]
        output_extfiles["sample_id"] = summary_data["sample_details"]["id"]
        output_extfiles["sha256_hash"] = summary_data["sample_details"].get("sha256_hash", None)
        # output_extfiles["sha1_hash"] = summary_data["sample_details"]["sha1_hash"]
        # output_extfiles["md5_hash"] = summary_data["sample_details"]["md5_hash"]
        strip_type_version(output_extfiles)
        strip(output_extfiles, ["archive_path", "file_type",
                                "sha1_hash", "md5_hash"])
        event_extracted_files = smi.Event(stanza=stanza, time=_time, index=index,
                                          sourcetype="vmray:extracted_files")
        event_extracted_files.data = json.dumps(output_extfiles)
        logging.debug("Writing summary extracted_files")
        ev_writer.write_event(event_extracted_files)

    @staticmethod
    def _write_event_static_data(analysis_data, summary_data, ev_writer=None,
                                 stanza=None, _time=None, index=None):
        output_static_data = {
            "static_data": copy.deepcopy(summary_data['static_data']),
            "analysis_id": analysis_data["analysis_id"],
            "sample_id": summary_data["sample_details"]["id"],
            "sha256": summary_data["sample_details"].get("sha256_hash", None)
        }

        strip_type_version(output_static_data)

        extracted_files = {}
        for extracted_file in summary_data["extracted_files"]:
            extracted_files[extracted_file["id"]] = extracted_file

        for el in output_static_data["static_data"]:
            ref = el["ref_file"]["ref_id"]

            extracted_file = extracted_files.get(ref)
            if not extracted_file:
                logging.error("Referenced extracted file not found")
                extracted_file = {}

            el["norm_filename"] = extracted_file.get("norm_filename")
            el["sha256_hash"] = extracted_file.get("sha256_hash")
            el["size"] = extracted_file.get("size")

            if not el["pe"]:
                # Execlude static_data without pe data (e.g. MacOS)
                continue

            pe_imports_copy = copy.deepcopy(el["pe"].get("imports", []))
            el["pe"]["imports"] = []

            for _import in pe_imports_copy:
                for api in _import.get("apis", []):
                    value = api["api"]["name"] if api["api"]["name"] else str(api["api"]["ordinal"])
                    el["pe"]["imports"].append(value)

            pe_exports_copy = copy.deepcopy(el["pe"].get("exports", []))
            el["pe"]["exports"] = []
            for _export in pe_exports_copy:
                value = _export["api"]["name"] if _export["api"]["name"] else str(_export["api"]["ordinal"])
                el["pe"]["exports"].append(value)

        event_static_data = smi.Event(stanza=stanza, time=_time, index=index,
                                      sourcetype="vmray:static_data")
        event_static_data.data = json.dumps(output_static_data)
        logging.debug("Writing summary static_data")
        ev_writer.write_event(event_static_data)

    def __init__(self,
                 import_vti=False,
                 import_yara=False,
                 import_local_av=False,
                 import_mitre_attack=False,
                 import_network=False,
                 import_reputation=False,
                 import_whois=False,
                 import_artifacts=False,
                 import_artifact_operations=False,
                 import_extracted_files=False,
                 import_processes=False,
                 import_vm_and_analyzer=False,
                 import_remarks=False,
                 import_static_data=False
                 ):
        self.import_vti = import_vti
        self.import_yara = import_yara
        self.import_local_av = import_local_av
        self.import_mitre_attack = import_mitre_attack
        self.import_network = import_network
        self.import_reputation = import_reputation
        self.import_whois = import_whois
        self.import_artifacts = import_artifacts
        self.import_artifact_operations = import_artifact_operations
        self.import_extracted_files = import_extracted_files
        self.import_processes = import_processes
        self.import_vm_and_analyzer = import_vm_and_analyzer
        self.import_remarks = import_remarks
        self.import_static_data = import_static_data

    @staticmethod
    def _get_wrapped(dic, key):
        sub_dict = dic.get(key, None)

        if sub_dict and not isinstance(sub_dict, dict):
            sub_dict = {key: sub_dict}

        return sub_dict

    def __call__(self, ev_writer=None, stanza=None, _time=None, index=None,
                 sourcetype=None, data=None):
        assert sourcetype is None
        analysis_data = data.get("analysis", None)
        summary_data = data.get("summary", None)
        if analysis_data is None:
            logging.warning("Could not write summary event because data is missing")
            return

        if summary_data is None:
            if analysis_data["analysis_result_code"] == 1:
                logging.error(
                    (
                        "Could not write summary event because data is missing, "
                        "even though analysis was successful. analysis_id %d"
                    ),
                    analysis_data["analysis_id"]
                )
            return

        meta_data = {
            "analysis_id": analysis_data["analysis_id"],
            "sample_id": summary_data["sample_details"]["id"],
            "sha256_hash": summary_data["sample_details"].get("sha256_hash")
        }

        if self.import_vti:
            sub_dict = self._get_wrapped(summary_data, "vti")
            sourcetype = "vmray:vti_result"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_yara:
            sub_dict = self._get_wrapped(summary_data, "yara")
            sourcetype = "vmray:yara"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_local_av:
            sub_dict = self._get_wrapped(summary_data, "local_av")
            sourcetype = "vmray:local_av"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_mitre_attack:
            sub_dict = self._get_wrapped(summary_data, "mitre_attack")
            sourcetype = "vmray:mitre_attack"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_network:
            sub_dict = self._get_wrapped(summary_data, "network")
            sourcetype = "vmray:network"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_reputation:
            sub_dict = self._get_wrapped(summary_data, "reputation")
            sourcetype = "vmray:reputation"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_whois:
            sub_dict = self._get_wrapped(summary_data, "whois")
            sourcetype = "vmray:whois"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_artifacts:
            self._write_event_artifacts(
                analysis_data, summary_data, ev_writer, stanza, _time, index)

        if self.import_artifact_operations:
            sub_dict = self._get_wrapped(summary_data, "artifact_operations")
            sourcetype = "vmray:artifact_operations"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_extracted_files:
            self._write_event_extracted_files(
                analysis_data, summary_data, ev_writer, stanza, _time, index)

        if self.import_processes:
            sub_dict = self._get_wrapped(summary_data, "processes")
            sourcetype = "vmray:processes"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype, strip_keys=["regions"])

        if self.import_vm_and_analyzer:
            sub_dict = self._get_wrapped(summary_data, "vm_and_analyzer_details")
            sourcetype = "vmray:vm_and_analyzer"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_remarks:
            sub_dict = self._get_wrapped(summary_data, "remarks")
            sourcetype = "vmray:remarks"
            self._write_event_generic(
                meta_data, sub_dict, ev_writer, stanza, _time, index, sourcetype)

        if self.import_static_data:
            self._write_event_static_data(
                analysis_data, summary_data, ev_writer, stanza, _time, index)
