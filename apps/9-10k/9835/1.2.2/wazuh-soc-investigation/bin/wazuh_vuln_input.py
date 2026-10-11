#!/usr/bin/env python3

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import urllib3
from splunklib.modularinput import Argument, Event, EventWriter, Scheme, Script

try:
    import requests
except ImportError:
    requests = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WazuhVulnInput(Script):

    def get_scheme(self):
        scheme = Scheme("Wazuh Vulnerability Input")
        scheme.description = "Pulls vulnerability findings from the Wazuh Indexer API into Splunk."
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        scheme.add_argument(Argument(
            name="indexer_host",
            title="Indexer host",
            description="Hostname or IP of the Wazuh Indexer",
            data_type=Argument.data_type_string,
            required_on_create=True,
        ))
        scheme.add_argument(Argument(
            name="port",
            title="Indexer port",
            description="Default 9200",
            data_type=Argument.data_type_number,
            required_on_create=False,
        ))
        scheme.add_argument(Argument(
            name="username",
            title="Username",
            description="A read-only Wazuh indexer account, for example readall",
            data_type=Argument.data_type_string,
            required_on_create=True,
        ))
        scheme.add_argument(Argument(
            name="password",
            title="Password",
            description="Password for the indexer account. Stored encrypted by Splunk.",
            data_type=Argument.data_type_string,
            required_on_create=True,
        ))
        scheme.add_argument(Argument(
            name="index_pattern",
            title="Indexer index pattern",
            description="Default wazuh-states-vulnerabilities*",
            data_type=Argument.data_type_string,
            required_on_create=False,
        ))
        scheme.add_argument(Argument(
            name="verify_ssl",
            title="Verify SSL certificate",
            description="Wazuh indexers normally use a self-signed certificate, leave unchecked unless yours is CA-signed.",
            data_type=Argument.data_type_boolean,
            required_on_create=False,
        ))
        scheme.add_argument(Argument(
            name="page_size",
            title="Page size",
            description="Default 1000",
            data_type=Argument.data_type_number,
            required_on_create=False,
        ))
        return scheme

    def validate_input(self, validation_definition):
        params = validation_definition.parameters
        if not params.get("indexer_host", "").strip():
            raise ValueError("Indexer host is required")
        if not params.get("username", "").strip():
            raise ValueError("Username is required")
        if not params.get("password", ""):
            raise ValueError("Password is required")

    def stream_events(self, inputs, ew):
        if requests is None:
            ew.log(EventWriter.ERROR, "wazuh_vuln_input: the 'requests' library is not available")
            return
        for input_name, input_item in inputs.inputs.items():
            self._process_input(input_name, input_item, ew)

    def _process_input(self, input_name, input_item, ew):
        host = input_item.get("indexer_host", "").strip()
        port = (input_item.get("port") or "9200").strip()
        username = input_item.get("username", "").strip()
        password = input_item.get("password", "")
        index_pattern = (input_item.get("index_pattern") or "wazuh-states-vulnerabilities*").strip()
        verify_ssl = str(input_item.get("verify_ssl", "0")).lower() in ("1", "true", "yes")

        try:
            page_size = int(input_item.get("page_size") or 1000)
        except (TypeError, ValueError):
            page_size = 1000

        if not host or not username:
            ew.log(EventWriter.ERROR, "wazuh_vuln_input[{}]: host or username missing".format(input_name))
            return

        url = "https://{}:{}/{}/_search".format(host, port, index_pattern)
        auth = (username, password)
        search_after = None
        fetched = 0

        while True:
            body = {
                "size": page_size,
                "sort": [{"_id": "asc"}],
                "query": {"match_all": {}},
            }
            if search_after:
                body["search_after"] = search_after

            try:
                resp = requests.post(url, auth=auth, json=body, verify=verify_ssl, timeout=60)
            except requests.exceptions.RequestException as e:
                ew.log(EventWriter.ERROR, "wazuh_vuln_input[{}]: request failed: {}".format(input_name, e))
                return

            if resp.status_code != 200:
                ew.log(EventWriter.ERROR, "wazuh_vuln_input[{}]: query failed, status {} body {}".format(
                    input_name, resp.status_code, resp.text[:500]))
                return

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break

            for hit in hits:
                source = hit.get("_source", {})
                vuln = source.get("vulnerability", {})
                source["timestamp"] = vuln.get("detected_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                event = Event(
                    data=json.dumps(source),
                    stanza=input_name,
                    sourcetype="wazuh:vulnerability",
                )
                ew.write_event(event)
                fetched += 1

            search_after = hits[-1].get("sort")
            if not search_after or len(hits) < page_size:
                break

        ew.log(EventWriter.INFO, "wazuh_vuln_input[{}]: fetched {} vulnerability records".format(input_name, fetched))


if __name__ == "__main__":
    sys.exit(WazuhVulnInput().run(sys.argv))
