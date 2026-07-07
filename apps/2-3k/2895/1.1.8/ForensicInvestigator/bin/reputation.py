#!/usr/bin/env python

"""reputaiton.py: handler script for interacting with various online analysis
APIs and returning the results to Splunk"""

from ReputationAPI import MetascanAPI, TotalHashAPI
import sys
import json
import csv
from xml.etree import ElementTree
from xml.dom.minidom import parseString
import splunk.Intersplunk

__author__ = 'Josh Tornetta'
__maintainer__ = 'Josh Tornetta'
__email__ = "tornettaj@gmail.com"
__status__ = "Production"


metascan_api_key = "72bce8cd8b07b9ef3b388eb6c6f97a89"
totalhash_api_key = "6156d648be0489cbab8350cde53238b3ecba9ca77da2f681a35cfe6b76ccac28"
totalhash_userid = "jtornetta"

def metascan(query):
    metascan = MetascanAPI(metascan_api_key,scan_type)

    if scan_type == "hash":
        rep = metascan.hashLookup(query)
    elif scan_type == "ip":
        rep = metascan.ipLookup(query)
    elif scan_type == "url":
        rep = metascan.urlLookup(query)

    if rep:
        return json.loads(rep)
    else:
        return None

def totalhash(query):
    totalhash = TotalHashAPI(totalhash_api_key,totalhash_userid,scan_type,query)

    if scan_type == "hash":
        rep = totalhash.hashLookup(query)
        sha_hash = totalhash_xml_parser(rep)

        analysis_handler = TotalHashAPI(totalhash_api_key,totalhash_userid,"analysis",sha_hash)
        result = analysis_handler.hashAnalysis(sha_hash)

    if result:
        return result
    else:
       return None

def totalhash_xml_parser(content):
    xml_dom = parseString(content)
    xml_sha_element = xml_dom.getElementsByTagName('str')[0].toxml()
    sha_value = ElementTree.fromstring(xml_sha_element)
    sha = sha_value.text

    return sha


if __name__ == "__main__":
    (isgetinfo,sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
    reputation_source = sys.argv[1]
    scan_type = sys.argv[2]
    query = sys.argv[3].lstrip()

    if reputation_source == "metascan":
        response = metascan(query)

        if response is not None:
            output = csv.writer(sys.stdout)
            data = [['ms'],[json.dumps(response)]]
            output.writerows(data)
        else:
           splunk.Intersplunk.generateErrorResults("NULL response received.")
           sys.exit(1)
    elif reputation_source == "totalhash":
        response = totalhash(query)

        if response is not None:
            output = csv.writer(sys.stdout)
            data = [['th'],[response]]
            output.writerows(data)
        else:
            splunk.Intersplunk.generateErrorResults("NULL response received.")
            sys.exit(1)
    else:
        pass
