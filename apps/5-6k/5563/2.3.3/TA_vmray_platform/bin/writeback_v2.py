import json
import logging

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from splunklib.modularinput import Event
from vmraylib.summary_v2 import SummaryV2

if TYPE_CHECKING:
    from splunklib.modularinput.event_writer import EventWriter  # pylint: disable=ungrouped-imports


def remove_if_exists(data: Dict, key: str) -> Dict:
    try:
        del data[key]
    except KeyError:
        pass
    return data


def rename_if_exists(data: Dict, key: str, new_key: str) -> Dict:
    try:
        data[new_key] = data[key]
        del data[key]
    except KeyError:
        pass
    return data


def remove_references(data: Dict) -> Dict:
    for key in list(data):
        if key.startswith("ref_"):
            del data[key]
    return data


def flatten(data: Dict, key: str, new_key_prefix="") -> Dict:
    if not key in data or not isinstance(data[key], dict):
        return data

    for subkey, value in data[key].items():
        if not subkey.startswith("_"):
            data[new_key_prefix + subkey] = value
    del data[key]

    return data


def strip_vti_match(data: Dict) -> Dict:
    data = remove_if_exists(data, "ref_gfncalls")
    data = flatten(data, "technique_meta_info")
    data = rename_if_exists(data, "ref_mitre_attack_techniques", "mitre_attack_techniques")
    return data


def strip_vti_match_artifacts(data: Dict) -> Dict:
    # remove empty lists
    for key in list(data):
        value = data[key]
        if isinstance(value, list) and not value:
            del data[key]
    return data


def strip_vti_match_artifact(data: Dict) -> Dict:
    # flatten the artifact reference
    if "ref_artifact" in data and isinstance(data["ref_artifact"], dict):
        data.update(strip_dict(data["ref_artifact"]))
        del data["ref_artifact"]

    # remove some process attributes which we don't need for vti matches
    data = remove_if_exists(data, "code_modifications")
    data = remove_if_exists(data, "iat_modifications")

    return data


def strip_mutex(data: Dict) -> Dict:
    return remove_references(data)


def strip_domain(data: Dict) -> Dict:
    data = remove_references(data)
    data = remove_if_exists(data, "whois")
    data = remove_if_exists(data, "sources")
    return data


def strip_url(data: Dict) -> Dict:
    return remove_references(data)


def strip_file(data: Dict) -> Dict:
    # flatten hash_values
    if "hash_values" in data:
        hashes = data["hash_values"]
        for key in ("md5", "sha1", "sha256", "ssdeep"):
            if key in hashes and hashes[key]:
                data[key] = hashes[key]
        del data["hash_values"]

    # flatten filenames
    if "ref_filenames" in data:
        filenames = []
        for filename in data["ref_filenames"]:
            if "filename" in filename:
                filenames.append(filename["filename"])
        data["filenames"] = filenames
        del data["ref_filenames"]
    data = remove_references(data)
    data = remove_if_exists(data, "archive_path")
    return data


def strip_ip_address(data: Dict) -> Dict:
    return remove_references(data)


def strip_registry_record(data: Dict) -> Dict:
    return remove_references(data)


def strip_process(data: Dict) -> Dict:
    data = remove_references(data)
    data = remove_if_exists(data, "regions")
    return data


def strip_process_code_modification(data: Dict) -> Dict:
    return remove_references(data)


def strip_process_iat_modification(data: Dict) -> Dict:
    return remove_references(data)


def strip_mitre_attack_v4_technique(data: Dict) -> Dict:
    return remove_references(data)


def strip_yara_match(data: Dict) -> Dict:
    data = rename_if_exists(data, "ref_file", "file")
    return data


def strip_anti_virus_match(data: Dict) -> Dict:
    data = rename_if_exists(data, "ref_file", "file")
    # flatten threat info
    data = flatten(data, "threat", "threat_")
    return data


def strip_network_dns_query(data: Dict) -> Dict:
    return remove_references(data)


def strip_network_http_request(data: Dict) -> Dict:
    data = remove_references(data)
    if "message" in data:
        if "size" in data["message"]:
            data["request_size"] = data["message"]["size"]
        del data["message"]
    return data


def strip_network_http_response(data: Dict) -> Dict:
    data = remove_references(data)
    if "message" in data:
        if "size" in data["message"]:
            data["response_size"] = data["message"]["size"]
        del data["message"]
    return data


def strip_network_session(data: Dict) -> Dict:
    data = remove_references(data)
    if "connection" in data and isinstance(data["connection"], dict):
        data.update(strip_dict(data["connection"]))
        del data["connection"]

    data = remove_if_exists(data, "received_message")
    data = remove_if_exists(data, "transmitted_message")
    return data


def strip_network_session_connection(data: Dict) -> Dict:
    for key in ("ref_local_ip_address", "ref_remote_ip_address"):
        if key not in data or "ip_address" not in data[key]:
            continue
        data[key[4:]] = data[key]["ip_address"]
        del data[key]

    return remove_references(data)


def strip_reputation_file(data: Dict) -> Dict:
    data = rename_if_exists(data, "ref_file", "file")
    return data


def strip_reputation_url(data: Dict) -> Dict:
    data = rename_if_exists(data, "ref_url", "url")
    return data


def strip_reputation_ip_address(data: Dict) -> Dict:
    data = rename_if_exists(data, "ref_ip", "ip")
    return data


def strip_email_address(data: Dict) -> Dict:
    return remove_references(data)


def strip_email(data: Dict) -> Dict:
    return remove_references(data)


def strip_filename(data: Dict) -> Dict:
    data = remove_references(data)

    # flatten original_filenames
    if "original_filenames" in data:
        filenames = []
        for filename in data["original_filenames"]:
            if "filename" in filename:
                filenames.append(filename["filename"])
        data["original_filenames"] = filenames
    return data


def strip_virtual_machine(data: Dict) -> Dict:
    data = remove_if_exists(data, "randomly_created_artifacts")
    data = remove_if_exists(data, "custom_created_artifacts")
    return data


STRIP_HANDLERS: Dict[str, Callable[[Dict], Dict]] = {
    "analysis_metadata": lambda x: x,
    "analysis_metadata.platform_information": lambda x: x,
    "anti_virus.match": strip_anti_virus_match,
    "domain": strip_domain,
    "email": strip_email,
    "email_address": strip_email_address,
    "file": strip_file,
    "filename": strip_filename,
    "ip_address": strip_ip_address,
    "ip_address.location": lambda x: x,
    "registry": strip_registry_record,
    "registry_record": strip_registry_record,
    "mitre_attack.v4.technique": strip_mitre_attack_v4_technique,
    "mutex": strip_mutex,
    "network.dns.query": strip_network_dns_query,
    "network.dns.record": lambda x: x,
    "network.http.request": strip_network_http_request,
    "network.http.response": strip_network_http_response,
    "network.session": strip_network_session,
    "network.session.connection": strip_network_session_connection,
    "process": strip_process,
    "process.code_modification": strip_process_code_modification,
    "process.iat_modification": strip_process_iat_modification,
    "remark": lambda x: x,
    "reputation.file": strip_reputation_file,
    "reputation.threat": lambda x: x,
    "reputation.url": strip_reputation_url,
    "reputation.ip_address": strip_reputation_ip_address,
    "virtual_machine.software_details": lambda x: x,
    "url": strip_url,
    "virtual_machine": strip_virtual_machine,
    "vti.match": strip_vti_match,
    "vti.match.artifact": strip_vti_match_artifact,
    "vti.match.artifacts": strip_vti_match_artifacts,
    "yara.match": strip_yara_match,
}


def strip(data: Any, force=False) -> Any:
    if isinstance(data, dict):
        return strip_dict(data, force=force)
    if isinstance(data, list):
        return strip_list(data, force=force)
    return data


def strip_dict(data: Dict, force=False) -> Dict:
    if "_type" in data:
        if data["_type"] == "reference":
            # somehow a reference got until here (maybe it's invalid?) -> just return empty dict
            return {}
        if data["_type"] in STRIP_HANDLERS:
            data = STRIP_HANDLERS[data["_type"]](data)
            del data["_type"]
        elif force:
            # strip the _type anyway
            del data["_type"]

    # strip members recursively
    for key in data:
        data[key] = strip(data[key], force=force)

    return data


def strip_list(data: list, force=False) -> list:
    return list(map(lambda x: strip(x, force=force), data))


class SummaryV2EventWriter:
    def __init__(self, import_vti_match=False, import_yara_match=False, import_av_match=False,
                 import_network=False, import_reputation_lookup=False, import_artifacts=False,
                 import_iocs_only=False, import_analysis_details=False, import_remark=False,
                 import_static_data=False):
        self.import_vti_match = import_vti_match
        self.import_yara_match = import_yara_match
        self.import_av_match = import_av_match
        self.import_network = import_network
        self.import_reputation_lookup = import_reputation_lookup
        self.import_artifacts = import_artifacts
        self.import_iocs_only = import_iocs_only
        self.import_analysis_details = import_analysis_details
        self.import_remark = import_remark
        self.import_static_data = import_static_data

        # will be set in each __call__
        self.summary: Optional[SummaryV2] = None
        self.event_writer: Optional["EventWriter"] = None
        self.analysis: Dict[str, Any] = {}
        self.extended_analysis_info: Dict[str, Any] = {}
        self.def_event_attributes: Dict[str, Any] = {}

    def __call__(self, ev_writer: "EventWriter", stanza: str, _time: int, index: str,
                 sourcetype: Optional[str], data: dict):
        analysis_data = data.get("analysis")
        summary_data = data.get("summary_v2")

        if analysis_data is None:
            logging.warning("Could not write summary event because data is missing")
            return

        if summary_data is None:
            if analysis_data["analysis_result_code"] == 1:
                logging.error("Could not write summary event because data is missing, even though analysis was"
                              " successful. analysis_id %d", analysis_data["analysis_id"])
            return

        # keep in mind that the event writer object persists across mutliple events
        # but we re-set these attributes on every call
        self.summary = SummaryV2(summary_data, ignored_fields={
            # ignore some fields which we would strip out later anyway
            # all unnecessary fields which can contain a significant amount of data should be added here
            "file": {
                "ref_static_data",
                "ref_vti_matches",
                "ref_gfncalls",
            },
            "filename": {
                "ref_gfncalls",
            },
            "process": {
                "ref_extracted_files",
                "ref_extracted_function_strings_file",
                "ref_gfncalls",
                "ref_memory_dumps",
                "ref_vti_matches",
                "regions",
            },
            "registry_record": {
                "ref_gfncalls",
            },
            "vti.match": {"ref_gfncalls"},
            "domain": {"whois", "sources"},
            "network.session": {"received_message", "transmitted_message"},
            "virtual_machine": {"randomly_created_artifacts"},
            "mitre_attack.v4.technique": {"ref_vti_matches"},
        })
        self.analysis = analysis_data

        self.extended_analysis_info = data.get("extended_analysis_info", {})
        if self.extended_analysis_info is None:
            self.extended_analysis_info = {}

        self.event_writer = ev_writer
        self.def_event_attributes = {
            "stanza": stanza,
            "time": _time,
            "index": index
        }

        if self.import_vti_match:
            self.write_vti_matches()

        if self.import_yara_match:
            self.write_yara_matches()

        if self.import_av_match:
            self.write_av_matches()

        if self.import_network:
            self.write_network()

        if self.import_reputation_lookup:
            self.write_reputation_lookups()

        if self.import_artifacts:
            self.write_artifacts()

        if self.import_analysis_details:
            self.write_analysis_details()

        if self.import_remark:
            self.write_remarks()

        if self.import_static_data:
            self.write_static_data()

    def add_generic_properties(self, data: Dict) -> Dict:
        for dest_key, source_key in (
            ("analysis_id", "analysis_id"),
            ("sample_id", "analysis_sample_id"),
            ("submission_id", "analysis_submission_id"),
            ("sample_type", "analysis_jobrule_sampletype"),
            ("sample_sha256", "analysis_sample_sha256"),
            ("vm_name", "analysis_vm_name"),
            ("configuration_name", "analysis_configuration_name"),
            ("platform", "analysis_platform"),
        ):
            # some attributes have only been introduced in newer version or are stripped due to import restrictions
            if source_key in self.analysis:
                data[dest_key] = self.analysis[source_key]

        return data

    def write_event(self, event_data: dict, sourcetype: str):
        event_data = self.add_generic_properties(event_data)
        event = Event(**self.def_event_attributes, sourcetype=sourcetype)
        event.data = json.dumps(event_data, sort_keys=True)
        logging.debug("Writing summary_v2 event %s analysis_id=%d", sourcetype, self.analysis.get("analysis_id", -1))
        assert self.event_writer
        self.event_writer.write_event(event)

    def write_vti_matches(self):
        vti_node = self.summary.get("vti", {}, recurse_allow={
            "domain",
            "email",
            "email_address",
            "file",
            "filename",
            "ip_address",
            "mitre_attack.v4.technique",
            "mutex",
            "process",
            "registry_record",
            "url",
        })

        if "matches" not in vti_node:
            return

        for _, match_ in vti_node["matches"].items():
            stripped = strip_dict(match_)
            stripped["built_in_rules_version"] = vti_node.get("built_in_rules_version")
            stripped["score_type"] = vti_node.get("score_type")
            stripped.update(self.extended_analysis_info)
            self.write_event(stripped, "vmray:vti_match")

    def write_yara_matches(self):
        yara_node = self.summary.get("yara", {}, recurse_allow={"file", "filename"})

        if "matches" not in yara_node:
            return

        for _, match_ in yara_node["matches"].items():
            stripped = strip_dict(match_)
            stripped["built_in_ruleset_version"] = yara_node.get("built_in_ruleset_version")
            stripped.update(self.extended_analysis_info)
            self.write_event(stripped, "vmray:yara_match")

    def write_av_matches(self):
        av_node = self.summary.get("anti_virus", {}, recurse_allow={"file", "filename"})

        for engine_name, data in av_node.items():
            if "matches" not in data:
                continue

            for match_ in data["matches"].values():
                stripped = strip_dict(match_)
                stripped["av_engine"] = engine_name
                stripped.update(self.extended_analysis_info)
                self.write_event(stripped, "vmray:av_match")

    def write_network(self):
        network_node = self.summary.get("network", {}, recurse_allow={"ip_address"}, max_depth=1)

        for key, sourcetype in (
            ("dns", "vmray:dns_query"),
            ("http", "vmray:http_request"),
            ("tcp", "vmray:tcp_session"),
            # ("tls", "vmray:tls_session"), TLS sessions have no interesting values yet
            ("udp", "vmray:udp_stream")
        ):
            if key in network_node:
                for element in network_node[key].values():
                    stripped = strip_dict(element)
                    stripped.update(self.extended_analysis_info)
                    self.write_event(stripped, sourcetype)

    def write_reputation_lookups(self):
        reputation_node = self.summary.get("reputation", {}, recurse_allow={
            "file",
            "filename",
            "ip_address",
            "url"
        })

        for engine_name, data in reputation_node.items():
            for type_ in ("files", "urls", "ip_addresses"):
                if type_ not in data:
                    continue

                for match_ in data[type_].values():
                    stripped = strip_dict(match_)
                    stripped["reputation_engine"] = engine_name
                    stripped.update(self.extended_analysis_info)
                    self.write_event(stripped, "vmray:reputation_lookup")

    def write_artifacts(self):
        artifacts_node = self.summary.get("artifacts", {}, recurse_allow={
            "domain",
            "email",
            "email_address",
            "file",
            "filename",
            "ip_address",
            "mitre_attack.v4.technique",
            "mutex",
            "process",
            "registry_record",
            "url",
        })

        for key, sourcetype in (
            ("ref_domains", "vmray:domain_artifact"),
            ("ref_email_addresses", "vmray:email_address_artifact"),
            ("ref_emails", "vmray:email_artifact"),
            ("ref_filenames", "vmray:filename_artifact"),
            ("ref_files", "vmray:file_artifact"),
            ("ref_ip_addresses", "vmray:ip_address_artifact"),
            ("ref_mutexes", "vmray:mutex_artifact"),
            ("ref_processes", "vmray:process_artifact"),
            ("ref_registry_records", "vmray:registry_record_artifact"),
            ("ref_urls", "vmray:url_artifact"),
        ):
            if key in artifacts_node:
                for element in artifacts_node[key]:
                    if "is_ioc" not in element:
                        continue
                    if self.import_iocs_only and not element["is_ioc"]:
                        continue
                    stripped = strip_dict(element)
                    stripped = remove_if_exists(stripped, "is_artifact")
                    stripped.update(self.extended_analysis_info)
                    self.write_event(stripped, sourcetype)

    def write_analysis_details(self):
        analysis_details = self.summary.get("analysis_metadata", {})
        if not analysis_details:
            return
        analysis_details = strip_dict(analysis_details)
        analysis_details.update(self.extended_analysis_info)
        analysis_details["vm_info"] = strip_dict(self.summary.get("virtual_machine", {}))
        self.write_event(analysis_details, "vmray:analysis_details")

    def write_remarks(self):
        remarks_node = self.summary.get("remarks", {})
        for key, type_ in (
            ("errors", "error"),
            ("infos", "info"),
            ("warnings", "warning")
        ):
            if key not in remarks_node:
                continue
            for remark in remarks_node[key]:
                stripped = strip_dict(remark)
                stripped["type"] = type_
                stripped.update(self.extended_analysis_info)
                self.write_event(stripped, "vmray:remark")

    def write_static_data(self):
        static_data_node = self.summary.get("static_data", {})

        for data_elem in static_data_node.values():
            # the static data will be dumped as is, but let's strip the "_type" field
            stripped = strip_dict(data_elem, force=True)
            stripped.update(self.extended_analysis_info)
            self.write_event(stripped, "vmray:static_data")
