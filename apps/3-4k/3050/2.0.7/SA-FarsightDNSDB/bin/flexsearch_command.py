# Copyright 2016 Farsight Security, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import calendar
import json
import logging as logger
import sys
import os
import time
import traceback

import dnsdb2
from IPy import IP
import splunk.Intersplunk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import connect
from splunklib.binding import HTTPError
from splunk.clilib import cli_common as cli
from common import get_credentials, get_client_info


def get_flex_function(client, query_type, match_type):
    """ Given a query type and match type, returns the appropriate flex function """
    function_map = {
        "rdata": {
            "regex": client.flex_rdata_regex,
            "glob": client.flex_rdata_glob
        },
        "rrnames": {
            "regex": client.flex_rrnames_regex,
            "glob": client.flex_rrnames_glob
        }
    }
    return function_map[query_type][match_type]


try:
    input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    output_events = []
    sessionKey = settings["sessionKey"]
    query = options.get("query", None)
    match_type = options.get("match_type", "glob")
    query_type = options.get("query_type", "rdata")
    if match_type not in ["glob", "regex"]:
        error = splunk.Intersplunk.generateErrorResults(
            "Unknown match type: %s" % match_type)
        splunk.Intersplunk.outputResults(error)
        sys.exit()
    if query_type not in ["rdata", "rrnames"]:
        error = splunk.Intersplunk.generateErrorResults(
            "Unknown query type: %s" % query_type)
        splunk.Intersplunk.outputResults(error)
        sys.exit()
    limit = options.get("limit", 0)
    rrtype = options.get("rrtype", None)
    exclude = options.get("exclude", None)
    bailiwick = options.get("bailiwick", None)
    time_first_before = options.get("time_first_before", None)
    time_first_after = options.get("time_first_after", None)
    time_last_before = options.get("time_last_before", None)
    time_last_after = options.get("time_last_after", None)
    if not query:
        error = splunk.Intersplunk.generateErrorResults("Usage: | dnsdbflex query_type=<rdata|rrnames> match_type=<glob|regex> query=<glob or regex pattern> "
                                                        "[rrtype=**A/MX/CNAME/etc] [bailiwick=bailiwick]"
                                                        "[time_first_before=time] [time_first_after=time] [time_last_before=time] [time_last_after=time]")
        splunk.Intersplunk.outputResults(error)
        sys.exit()

    # Special case for all-time searches
    if str(time_last_after) == "0":
        time_last_after = None
        time_first_before = None

    # Deal with dashboard sending "now" as a time
    if str(time_first_before) == "now":
        time_first_before = None

    # Deal with dashboard sending "" as a time
    if str(time_last_before) == "":
        time_last_before = None
    if str(time_first_after) == "":
        time_first_after = None

    timestamps = [time_first_before, time_first_after, time_last_before, time_last_after]
    for i, timestamp in enumerate(timestamps):
        try:
            timestamps[i] = int(time.mktime(time.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')))
        except ValueError:
            pass
        except TypeError:
            pass
    # Final parsed time inputs
    p_time_first_before = timestamps[0]
    p_time_first_after = timestamps[1]
    p_time_last_before = timestamps[2]
    p_time_last_after = timestamps[3]

    if rrtype is not None:
        rrtype = rrtype.lower()
    if rrtype == "*":
        rrtype = None

    cfg = cli.getConfStanza('dnsdb', 'dnsdb')
    apikey = get_credentials(sessionKey)
    swclient, version = get_client_info(sessionKey)
    if not apikey:
        splunk.Intersplunk.generateErrorResults(
            "No API key found. Configure SA-FarsightDNSDB before running this command")
        sys.exit()
    proxy = cfg["proxy"]
    if proxy != "":
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version, proxies={"https": proxy, "http": proxy})
    else:
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version)
    flex_function = get_flex_function(dnsdb, query_type, match_type)
    output_events = list(flex_function(query,
                                       ignore_limited=True,
                                       query_type=query_type,
                                       bailiwick=bailiwick,
                                       limit=limit,
                                       rrtype=rrtype,
                                       exclude=exclude,
                                       time_first_before=p_time_first_before,
                                       time_first_after=p_time_first_after,
                                       time_last_before=p_time_last_before,
                                       time_last_after=p_time_last_after))

    splunk.Intersplunk.outputResults(output_events)

except Exception as e:
    stack = traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
