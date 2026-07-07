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

import logging as logger
import traceback

import dnsdb2
import splunk.Intersplunk
from splunk.clilib import cli_common as cli
from common import get_credentials, get_client_info

try:
    input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()

    cfg = cli.getConfStanza('dnsdb', 'dnsdb')
    apikey = get_credentials(settings['sessionKey'])
    swclient, version = get_client_info(settings['sessionKey'])
    proxy = cfg["proxy"]
    if proxy != "":
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version, proxies={"https": proxy, "http": proxy})
    else:
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version)


    try:
        response = dnsdb.rate_limit()
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
    if response:
        output_events = [response['rate']]
    else:
        output_events = []

    splunk.Intersplunk.outputResults(output_events)

except Exception as e:
    stack = traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
