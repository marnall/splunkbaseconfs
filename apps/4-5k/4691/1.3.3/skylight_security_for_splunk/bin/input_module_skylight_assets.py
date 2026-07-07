import csv
import sys
import os
import time
import splunk.appserver.mrsparkle.lib.util as util

cwd_asset_inv = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','bin', 'asset-inventory')
sys.path.insert(0, cwd_asset_inv)

from splunk_input import SplunkInput
from mac_tag_extractor import MACTagExtractor
from server_tag_extractor import ServerTagExtractor
from useragent_tag_extractor import UserAgentTagExtractor
from port_tag_extractor import PortTagExtractor
from csv_report_generator import CSVReportGenerator

from splunk_searches import *

REPORT_FILENAME = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','lookups', 'assets.csv')

mac_te = MACTagExtractor()
server_te = ServerTagExtractor()
useragent_te = UserAgentTagExtractor()
port_te = PortTagExtractor()

csv_rg = CSVReportGenerator()

def get_tags_from_splunk(search_str, tag_extractor, SPLUNK_TOKEN):
    '''Generic function to make a Splunk search, parse it and extract tags from it.

    search_str: Splunk search.
    tag_extractor: function that extracts tags from data
    '''

    data = SplunkInput(SPLUNK_TOKEN).search(search_str)
    results = {}

    for row in data:
        tags = []

        if type(row[1]) == list:
            for row_elem in row[1]:
                tag = tag_extractor.extract_tag(row_elem)
                if tag: tags.append(tag)
        else:
            tag = tag_extractor.extract_tag(row[1])
            if tag: tags.append(tag)

        results[row[0]] = tags

    return results


def main(SPLUNK_TOKEN):
    if sys.version_info[0] < 3:
        time_function = time.time()
    else:
        time_function = time.perf_counter()

    try:
        s_time = time_function
        mac_info = get_tags_from_splunk(MAC_SEARCH, mac_te, SPLUNK_TOKEN)
        print('Got MAC info in %.3f sec' % (time_function - s_time))

        s_time = time_function
        ports_info = get_tags_from_splunk(PORT_SEARCH, port_te, SPLUNK_TOKEN)
        print('Got ports info in %.3f sec' % (time_function - s_time))

        s_time = time_function
        ua_info = get_tags_from_splunk(USERAGENT_SEARCH, useragent_te, SPLUNK_TOKEN)
        print('Got user-agent info in %.3f sec' % (time_function - s_time))

        s_time = time_function
        server_info = get_tags_from_splunk(SERVER_SEARCH, server_te, SPLUNK_TOKEN)
        print('Got server info in %.3f sec' % (time_function - s_time))

        s_time = time_function
        csv_rg.generate_report(REPORT_FILENAME, mac_info, ports_info, ua_info, server_info)
        print('Generated report in %.3f sec' % (time_function - s_time))
    except Exception as e:
        cwd = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','bin', 'asset-inventory','error.txt')
        with open(cwd, "a") as f:
            f.write("\n")
            f.write('error: {}'.format(e))

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    SPLUNK_TOKEN = helper.context_meta['session_key']
    main(SPLUNK_TOKEN)
