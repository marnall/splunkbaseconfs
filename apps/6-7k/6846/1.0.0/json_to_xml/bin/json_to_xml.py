#!/usr/bin/env python

import sys
import os
import json
import xml.etree.ElementTree as ET

# Set up environment variables
splunkhome = os.environ.get('SPLUNK_HOME')
if splunkhome:
    sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'json_to_xml', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class ConvertJsonToXmlCommand(StreamingCommand):
    """ ConvertJsonToXml

    ##Syntax

    | convertjsontoxml [output_file=<output_file_path>] [exclude_tags=<comma_separated_tags_to_exclude>]

    ##Description

    This command converts JSON data to XML format and optionally writes the result to a file.

    """
    output_file = Option(require=False)
    exclude_tags = Option(require=False, validate=validators.List())

    def dict_to_xml(self, data, parent=None):
        if parent is None:
            parent = ET.Element("root")

        if isinstance(data, dict):
            for key, value in data.items():
                elem = ET.Element(key)
                parent.append(elem)
                self.dict_to_xml(value, elem)
        elif isinstance(data, list):
            for item in data:
                self.dict_to_xml(item, parent)
        else:
            parent.text = str(data)

        return parent

    def remove_keys(self, data, keys_to_remove):
        if isinstance(data, dict):
            return {
                key: self.remove_keys(value, keys_to_remove)
                for key, value in data.items()
                if key not in keys_to_remove
            }
        elif isinstance(data, list):
            return [self.remove_keys(item, keys_to_remove) for item in data]
        return data

    def stream(self, records):
        for record in records:
            try:
                json_data = json.loads(record['_raw'])

                if self.exclude_tags:
                    json_data = self.remove_keys(json_data, self.exclude_tags)

                xml_data = self.dict_to_xml(json_data)
                xml_string = ET.tostring(xml_data, encoding="utf-8", method="xml").decode("utf-8")

                if self.output_file:
                    with open(self.output_file, "w") as f:
                        f.write(xml_string)

                record['_raw'] = xml_string
                yield record
            except Exception as e:
                yield {"_raw": "Error: " + str(e)}
                raise

dispatch(ConvertJsonToXmlCommand, sys.argv, sys.stdin, sys.stdout, __name__)
