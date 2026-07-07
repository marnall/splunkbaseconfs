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
import re

import dnsdb2
from IPy import IP
import splunk.Intersplunk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import connect
from splunklib.binding import HTTPError
from splunk.clilib import cli_common as cli
from common import get_credentials, get_client_info


def is_valid_ip(ip):
    try:
        ip = IP(ip)
    except (ValueError, TypeError):
        return False
    else:
        return True

def is_raw_rdata(raw):
    if re.match(r'^[a-fA-F0-9]+$', raw) and (len(raw) % 2) == 0:
        return True
    return False

# Given a host, find the ip
def lookup(host, dnsdb):
    response = list(dnsdb.lookup_rrset(target, ignore_limited=True))
    ips = []
    for record in response:
        if record['rrtype'] == 'A':
            ips = list(set(ips + record['rdata']))
    return ips

# Given an ip, return the host
def rlookup(ip, dnsdb):
    response = list(dnsdb.lookup_rdata_ip(ip, ignore_limited=True))
    hostnames = []
    for record in response:
        if record['rrtype'] == 'A':
            hostnames.append(record['rrname'])
    return hostnames

def rawlookup(raw, dnsdb):
    response = list(dnsdb.lookup_rdata_raw(raw, ignore_limited=True))
    rrnames = []
    rrtypes = []
    rdatas = []
    for record in response:
        rrnames.append(record['rrname'])
        rrtypes.append(record['rrtype'])
        rdatas.append(" ".join(record['rdata']))
    return rrnames, rrtypes, rdatas


try:
    input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    output_events = []
    sessionKey = settings["sessionKey"]

    input_field = options.get("input_field", None)

    if not input_field:
        error = splunk.Intersplunk.generateErrorResults("Usage: ... | dnsdblookup "
                                                        "input_field=\"<field name>\"")
        splunk.Intersplunk.outputResults(error)
        sys.exit()

    cfg = cli.getConfStanza('dnsdb', 'dnsdb')
    apikey = get_credentials(sessionKey)
    swclient, version = get_client_info(sessionKey)

    if not apikey:
        splunk.Intersplunk.generateErrorResults("No API key found. Configure SA-FarsightDNSDB before running this command")
        sys.exit()
    proxy = cfg["proxy"]

    if proxy != "":
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version, proxies={"https": proxy, "http": proxy})
    else:
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version)
    output_events = []
    for event in input_events:
        if input_field not in event:
            output_events.append(event)
            continue
        target = event[input_field]
        try:
            if is_raw_rdata(target):
                event["dnsdb_rrname"], event["dnsdb_rrtype"], event["dnsdb_rdata"] = rawlookup(target, dnsdb)
            elif is_valid_ip(target):
                event["dnsdb_host"] = rlookup(target, dnsdb)
            else:
                event["dnsdb_ip"] = lookup(target, dnsdb)
        except dnsdb2.QueryError as e:
            raise Exception("Server returned query error: %s" % str(e))
        except dnsdb2.QueryFailed as e:
            raise Exception("Server encountered an error while running query: %s" % str(e))
        except dnsdb2.QueryLimited as e:
            # With ignore_limited=True we should never see this
            raise Exception("Result limit reached")
        except dnsdb2.QueryTruncated as e:
            raise Exception("Query results are incomplete due to a server error: %s" % str(e))
        except dnsdb2.QuotaExceeded as e:
            raise Exception("Query quota for this API key has been reached.")
        except dnsdb2.AccessDenied as e:
            raise Exception("Authorization failed. Check API key")
        except dnsdb2.ConcurrencyExceeded as e:
            raise Exception("Number of concurrent connections has exceeded your limit.")
        except dnsdb2.ProtocolError as e:
            raise Exception("Invalid data is received via the Streaming Application Framework: %s" % str(e))
        output_events.append(event)

    splunk.Intersplunk.outputResults(output_events)

except Exception as e:
    stack = traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
