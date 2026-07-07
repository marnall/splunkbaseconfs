#!/usr/bin/env python

import os
import sys
import base64
import tempfile
import atexit
import logging
import logging.handlers
import traceback
from ReversingLabs.SDK.ticloud import FileReputation, FileAnalysis, NetworkReputation, resolve_hash_type
from splunklib.searchcommands import StreamingCommand, Configuration, Option, validators, dispatch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


def _setup_app_logging():
    """Configure a single RotatingFileHandler shared by all relevant loggers.

    Called once at module load time so every log statement — including those
    inside splunklib and the requests/urllib3 stack — goes to the same file
    that Splunk monitors and indexes.
    """
    splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
    log_path = os.path.join(splunk_home, "var", "log", "splunk", "reversinglabs.log")

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=25 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(fmt)

    # (logger_name, level) — set all to DEBUG for maximum verbosity
    targets = [
        ("ReversingLabsCommand", logging.DEBUG),
        ("splunklib",            logging.DEBUG),
        ("requests",             logging.DEBUG),
        ("urllib3",              logging.DEBUG),
    ]
    for name, level in targets:
        lgr = logging.getLogger(name)
        # Avoid duplicate handlers if the module is somehow reloaded
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in lgr.handlers):
            lgr.setLevel(level)
            lgr.addHandler(handler)
        lgr.propagate = False  # prevent splunkd's stderr handler from duplicating output


_setup_app_logging()

HOST = "https://data.reversinglabs.com"
USERNAME = None
PASSWORD = None
PROXY = None
CERT_PATH = None
_CERT_TEMP_FILE = None


def _cleanup_cert_temp_file():
    if _CERT_TEMP_FILE and os.path.exists(_CERT_TEMP_FILE):
        try:
            os.unlink(_CERT_TEMP_FILE)
        except Exception:
            pass


atexit.register(_cleanup_cert_temp_file)
VERSION = "v1.0.2"
USER_AGENT = f"ReversingLabs Search Extension for Splunk {VERSION}"

REPORT_TYPES = ["file_reputation_hash", "file_analysis_hash", "network_reputation_location"]

OUTPUT_FIELDS = {
	"file_reputation_hash": [
		"RL_status", "RL_sha1", "RL_threat_level", "RL_platform", "RL_subplatform", "RL_type",
		"RL_is_generic", "RL_family_name", "RL_scanner_percent", "RL_threat_name", "RL_scanner_match", "RL_last_seen",
		"RL_reason", "RL_scanner_count", "RL_first_seen", "RL_sha256", "RL_trust_factor", "RL_md5",
		"RL_cve_is_candidate", "RL_cve_number", "RL_cve_year"
	],
	"file_analysis_hash": [
		"RL_sha1", "RL_md5", "RL_sha256", "RL_sha384", "RL_sha512", "RL_ripemd160", "RL_ssdeep", "RL_sample_size",
		"RL_first_seen", "RL_last_seen", "RL_sample_type", "RL_story", "RL_file_type", "RL_file_subtype",
		"RL_identification_name", "RL_message"
	],
	"network_reputation_location": [
		"RL_requested_network_location", "RL_type", "RL_first_seen", "RL_last_seen", "RL_classification", "RL_reason",
		"RL_associated_malware", "RL_third_party_reputations_total", "RL_third_party_reputations_undetected",
		"RL_third_party_reputations_malicious", "RL_third_party_reputations_clean"
	]
}


class SplunkJobTerminatedException(Exception):
	def __init__(self, state):
		self.state = state


class CustomCommandTimeoutException(Exception):
	def __init__(self, runtime):
		self.runtime = runtime


def _query_file_reputation(hashes):
	log = logging.getLogger("ReversingLabsCommand")
	log.info("file_reputation query start: hash_count=%d proxy=%r cert_path=%r", len(hashes), PROXY, CERT_PATH)
	mwp = FileReputation(
		host=HOST,
		username=USERNAME,
		password=PASSWORD,
		user_agent=USER_AGENT,
		proxies={"http": PROXY, "https": PROXY} if PROXY else None,
		verify=CERT_PATH if CERT_PATH else True,
	)

	try:
		response = mwp.get_file_reputation(hash_input=hashes)
	except Exception as e:
		log.error("file_reputation query failed:\n%s", traceback.format_exc())
		raise Exception("Request failed: " + traceback.format_exc()) from e

	out = {}

	resp_json = response.json()
	entries = resp_json.get("rl", {}).get("entries", [])
	hash_type = resolve_hash_type(sample_hashes=hashes)
	log.info("file_reputation query done: entry_count=%d http_status=%d", len(entries), response.status_code)

	for entry in entries:
		o = out[entry.get("query_hash").get(hash_type)] = {}

		o["RL_status"] = entry.get("status", "")
		o["RL_threat_name"] = entry.get("threat_name", "")
		o["RL_threat_level"] = entry.get("threat_level", "")
		o["RL_trust_factor"] = entry.get("trust_factor", "")
		classification_dict = entry.get("classification", {})
		o["RL_platform"] = classification_dict.get("platform", "")
		o["RL_type"] = classification_dict.get("type", "")
		o["RL_is_generic"] = classification_dict.get("is_generic", "")
		o["RL_family_name"] = classification_dict.get("family_name", "")
		o["RL_subplatform"] = classification_dict.get("subplatform", "")
		cve_dict = classification_dict.get("cve", {})
		o["RL_cve_is_candidate"] = cve_dict.get("is_candidate", "")
		o["RL_cve_number"] = cve_dict.get("number", "")
		o["RL_cve_year"] = cve_dict.get("year", "")
		o["RL_scanner_percent"] = entry.get("scanner_percent", "")
		o["RL_scanner_match"] = entry.get("scanner_match", "")
		o["RL_scanner_count"] = entry.get("scanner_count", "")
		o["RL_reason"] = entry.get("reason", "")
		o["RL_last_seen"] = entry.get("last_seen", "")
		o["RL_first_seen"] = entry.get("first_seen", "")
		o["RL_sha1"] = entry.get("sha1", "")
		o["RL_sha256"] = entry.get("sha256", "")
		o["RL_md5"] = entry.get("md5", "")

	return out


def _query_file_analysis(hashes):
	log = logging.getLogger("ReversingLabsCommand")
	log.info("file_analysis query start: hash_count=%d proxy=%r cert_path=%r", len(hashes), PROXY, CERT_PATH)
	rldata = FileAnalysis(
		host=HOST,
		username=USERNAME,
		password=PASSWORD,
		user_agent=USER_AGENT,
		proxies={"http": PROXY, "https": PROXY} if PROXY else None,
		verify=CERT_PATH if CERT_PATH else True,
	)

	try:
		response = rldata.get_analysis_results(hash_input=hashes)
	except Exception as e:
		log.error("file_analysis query failed:\n%s", traceback.format_exc())
		raise Exception("Request failed: " + traceback.format_exc()) from e

	out = {}

	resp_json = response.json()
	entries = resp_json.get("rl", {}).get("entries", [])

	num_of_unknown = len(resp_json.get("rl", {}).get("unknown_hashes", []))
	log.info("file_analysis query done: entry_count=%d unknown_count=%d http_status=%d",
	         len(entries), num_of_unknown, response.status_code)

	for entry in entries:
		o = out[entry.get("sha1")] = {}

		o["RL_sha1"] = entry.get("sha1", "")
		o["RL_md5"] = entry.get("md5", "")
		o["RL_sha256"] = entry.get("sha256", "")
		o["RL_sha384"] = entry.get("sha384", "")
		o["RL_sha512"] = entry.get("sha512", "")
		o["RL_ripemd160"] = entry.get("ripemd160", "")
		o["RL_ssdeep"] = entry.get("ssdeep", "")
		o["RL_sample_size"] = entry.get("sample_size", "")
		xref = entry.get("xref", {})
		o["RL_first_seen"] = xref.get("first_seen", "")
		o["RL_last_seen"] = xref.get("last_seen", "")
		o["RL_sample_type"] = xref.get("sample_type", "")
		analysis_entries = entry.get("analysis", {}).get("entries", [])
		if len(analysis_entries) > 0:
			analysis_entry = analysis_entries[0]
			tc_report = analysis_entry.get("tc_report", {})
			o["RL_story"] = tc_report.get("story", "")
			file_info = tc_report.get("info", {}).get("file", {})
			o["RL_file_type"] = file_info.get("file_type", "")
			o["RL_file_subtype"] = file_info.get("file_subtype", "")
			identification_info = tc_report.get("info", {}).get("identification", {})
			o["RL_identification_name"] = identification_info.get("name", "")

	return out, num_of_unknown


def _query_network_reputation(locations):
	log = logging.getLogger("ReversingLabsCommand")
	log.info("network_reputation query start: location_count=%d proxy=%r cert_path=%r", len(locations), PROXY, CERT_PATH)
	net_rep = NetworkReputation(
		host=HOST,
		username=USERNAME,
		password=PASSWORD,
		user_agent=USER_AGENT,
		proxies={"http": PROXY, "https": PROXY} if PROXY else None,
		verify=CERT_PATH if CERT_PATH else True,
	)

	try:
		response = net_rep.get_network_reputation(network_locations=locations)
	except Exception as e:
		log.error("network_reputation query failed:\n%s", traceback.format_exc())
		raise Exception("Request failed: " + traceback.format_exc()) from e

	out = {}

	resp_json = response.json()
	entries = resp_json.get("rl", {}).get("entries", [])
	log.info("network_reputation query done: entry_count=%d http_status=%d", len(entries), response.status_code)

	for entry in entries:
		o = out[entry.get("requested_network_location")] = {}

		o["RL_requested_network_location"] = entry.get("requested_network_location", "")
		o["RL_type"] = entry.get("type", "")
		o["RL_first_seen"] = entry.get("first_seen", "")
		o["RL_last_seen"] = entry.get("last_seen", "")
		o["RL_classification"] = entry.get("classification", "")
		o["RL_reason"] = entry.get("reason", "")
		o["RL_associated_malware"] = entry.get("associated_malware", "")
		third_party_reputations = entry.get("third_party_reputations", {})
		o["RL_third_party_reputations_total"] = third_party_reputations.get("total", "")
		o["RL_third_party_reputations_undetected"] = third_party_reputations.get("undetected", "")
		o["RL_third_party_reputations_malicious"] = third_party_reputations.get("malicious", "")
		o["RL_third_party_reputations_clean"] = third_party_reputations.get("clean", "")

	return out


def batch(gen, n=1):
	"""Get several items from a generator
		:param gen: The generator
		:param n: The number of items to get
		:return: A list of items retrieved from the generator
	"""
	records = []
	for record in gen:
		records.append(record)
		n = n - 1
		if n <= 0:
			break
	return records


@Configuration(local=True)
class ReversingLabsCommand(StreamingCommand):
	file_reputation_hash = Option(
		require=False,
		validate=validators.Fieldname(),
		doc="""
		**Syntax:** file_reputation_hash=<field_name>
		**Description:** The name of the field that contains a file hash
		"""
	)

	file_analysis_hash = Option(
		require=False,
		validate=validators.Fieldname(),
		doc="""
		**Syntax:** file_analysis_hash=<field_name>
		**Description:** The name of the field that contains a file hash
		"""
	)

	network_reputation_location = Option(
		require=False,
		validate=validators.Fieldname(),
		doc="""
		**Syntax:** network_reputation_location=<field_name>
		**Description:** The name of the field that contains a network location (URL, IP address or domain)
		"""
	)

	def map_rl(self, records):
		"""Incorporate RL information into the events provided in 'records'
		:param records: The records to be supplemented with added information
		:return: None
		"""
		for record in records:
			for k in OUTPUT_FIELDS[self.report_type]:
				if k not in record.keys():
					record[k] = ""

		records_dict = {}
		resources = []

		for record in records:
			if self.matching_field in record.keys() \
					and isinstance(record[self.matching_field], str) \
					and record[self.matching_field] == record[self.matching_field].strip():
				_resource = record[self.matching_field]
				records_dict[_resource] = record
				resources.append(_resource)

		if len(resources) == 0:
			self.logger.debug("Not querying RL API with %d resources" % len(resources))
			return
		self.logger.debug("Querying RL API with %d resources (%s)" % (len(resources), self.report_type))

		attempts = 0

		while True:
			try:
				attempts += 1
				if self.report_type == "file_reputation_hash":
					rl_res = _query_file_reputation(hashes=resources)
					expected_length = len(records_dict)

				elif self.report_type == "file_analysis_hash":
					rl_res, num_of_unknown = _query_file_analysis(hashes=resources)
					expected_length = len(records_dict) - num_of_unknown

				elif self.report_type == "network_reputation_location":
					rl_res = _query_network_reputation(locations=resources)
					expected_length = len(records_dict)

				break

			except Exception as e:
				self.logger.error("map_rl API call failed: attempt=%d\n%s", attempts, traceback.format_exc())
				self.error_exit(e, "Unexpected error when querying ReversingLabs API:" + str(e))

			if attempts > 10:
				self.error_exit(None, "Failed to retrieve results from ReversingLabs after 10 retries. Aborting.")

		if len(rl_res) != expected_length:
			self.error_exit(None, "ReversingLabs returned %d results, but %d were expected. "
							"Is the batch_size value set too high for this specific key (app setup)?"
							% (len(rl_res), expected_length))

		for k, v in rl_res.items():
			for rlk, rlv in v.items():
				records_dict[k][rlk] = rlv

	def prepare(self):
		"""Overrides the prepare method of the SearchCommand class.
		Called by splunkd before the command executes.
		Used to get configuration data for the custom command from Splunk.
		"""
		global USERNAME, PASSWORD, PROXY, CERT_PATH, _CERT_TEMP_FILE

		self.logger.debug('ReversingLabsCommand: %s', self)

		for credential in self.service.storage_passwords:
			if credential.realm == "reversinglabs-search-extension-realm":
				USERNAME = credential.username
				PASSWORD = credential.clear_password
				break

		if not USERNAME or not PASSWORD:
			self.error_exit(None, "Adequate TitaniumCloud credentials were not found. Please set up the app correctly.")

		stanza = self.service.confs['reversinglabs']['settings']
		PROXY = stanza.content.get('ticloud_proxy') or None

		cert_b64 = stanza.content.get('ticloud_cert_b64') or None
		if cert_b64:
			if _CERT_TEMP_FILE and os.path.exists(_CERT_TEMP_FILE):
				os.unlink(_CERT_TEMP_FILE)
			cert_pem = base64.b64decode(cert_b64)
			tmp = tempfile.NamedTemporaryFile(suffix='.pem', delete=False)
			tmp.write(cert_pem)
			tmp.close()
			_CERT_TEMP_FILE = tmp.name
			CERT_PATH = tmp.name
			self.logger.debug("cert loaded from config, written to temp file: %s", CERT_PATH)
		else:
			CERT_PATH = None

	def stream(self, records):
		"""Overrides the stream method of the StreamingCommand class.
		Hooking point for Splunk.
			:param records: The generator function provided by Splunk which will provide all the events.
			:return: yields events one at a time
		"""
		self.logger.debug("Starting ReversingLabs Search Extension in stream")

		self.matching_field = None
		self.report_type = None

		for rt in REPORT_TYPES:
			if getattr(self, rt) is not None:
				if self.report_type is not None:
					self.error_exit(None, "Multiple arguments are not supported. Specify only one")

					return

				self.report_type = rt
				self.matching_field = getattr(self, rt)

		if self.report_type is None:
			self.error_exit(None, "ReversingLabs command: No field was specified for matching")

			return

		try:
			while True:
				_records = batch(records)
				if len(_records) == 0:
					break
				self.map_rl(_records)
				for record in _records:
					yield record

		except SplunkJobTerminatedException as sjt:
			warning = "ReversingLabs Command: Forcing exit. Reason: Parent job termination detected. " \
					  "Parent job state: %s" % sjt.state
			self.write_warning(warning)
			self.logger.warning(warning)
			return
		except CustomCommandTimeoutException as cct:
			warning = "ReversingLabs Command: Forcing exit. Reason: Internal timeout reached. " \
					  "If necessary, the timeout can be increased on the app setup page. " \
					  "Command has been running for: %d seconds" % cct.runtime
			self.write_warning(warning)
			self.logger.warning(warning)
			return


dispatch(ReversingLabsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
