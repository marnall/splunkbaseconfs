#!/usr/bin/env python
# coding: utf-8

import os, sys, json

sys.path.insert(0, os.path.dirname(__file__))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

@Configuration(local=True)
class MITRECommand(StreamingCommand):
    """
    The vectramitre command maps Vectra detections to MITRE ATT&CK Framework techniques.
    """

    def stream(self, records):
        with open(os.path.join(os.path.dirname(__file__), "..", "json", "detection_to_technique.json"), 'rt') as file_json:
            mapping = json.load(file_json)
            mapping_lower = {d.lower(): t for d, t in mapping.items()}

            for record in records:
                record_raw_json = json.loads(record["_raw"])
                if record_raw_json["d_type_vname"].lower() in mapping_lower:
                    record_raw_json["techniques"] = mapping_lower[record_raw_json["d_type_vname"].lower()]
                    record["techniques"] = mapping_lower[record["d_type_vname"].lower()]
                else:
                    record_raw_json["techniques"] = ""
                    record["techniques"] = ""
                record["_raw"] = json.dumps(record_raw_json)
                yield record


dispatch(MITRECommand, sys.argv, sys.stdin, sys.stdout, __name__)