# Copyright 2020 Farsight Security, Inc.
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

import gzip
import csv
import json
import sys
from splunk.clilib import cli_common as cli
from dnsdb_command import run_query
import common
import logging
import dnsdb2

# CORE SPLUNK IMPORTS
try:
    from splunk.clilib.bundle_paths import make_splunkhome_path  # pylint: disable=import-error
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path  # pylint: disable=import-error

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-FarsightDNSDB",
                                      "lib"]))

from cim_actions import ModularAction, ModularActionTimer  # pylint: disable=wrong-import-position,import-error


logger = ModularAction.setup_logger("dnsdb_ar_action_modalert")


class DNSDBLookup(ModularAction):
    """
    Adaptive response action for enriching notable events using the DNSDB API
    """

    def __init__(self, settings, logger, action_name=None):  # pylint: disable=redefined-outer-name
        super(DNSDBLookup, self).__init__(settings, logger, action_name)

        self.target_field = self.configuration.get('target_field', None)
        self.target_type = self.configuration.get('target_type', 'auto')
        self.query_type = self.configuration.get('query_type', None)
        self.rrtype = self.configuration.get('rrtype', "ANY")
        self.bailiwick = self.configuration.get('bailiwick', None)
        self.time_first_before = self.configuration.get(
            'time_first_before', None)
        self.time_first_after = self.configuration.get(
            'time_first_after', None)
        self.time_last_before = self.configuration.get(
            'time_last_before', None)
        self.time_last_after = self.configuration.get('time_last_after', None)

        for attr in ("target_field", "query_type", "rrtype", "bailiwick", "time_first_before",
                     "time_first_after", "time_last_before", "time_last_after"):
            if getattr(self, attr) == "":
                setattr(self, attr, None)


def run():
    """ Execute the block """
    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print(sys.stderr, ("FATAL Unsupported execution mode"
                           " (expected --execute flag)"))
        sys.exit(1)
    modaction = DNSDBLookup(sys.stdin.read(), logger,
                            "dnsdb_ar_action")
    modaction.addinfo()
    session_key = modaction.session_key
    apikey = common.get_credentials(session_key)
    swclient, version = common.get_client_info(session_key)
    cfg = cli.getConfStanza('dnsdb', 'dnsdb')
    proxy = cfg["proxy"]
    if proxy != "":
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version, proxies={"https": proxy, "http": proxy})
    else:
        dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version)
    target_field = modaction.target_field  # pylint: disable=unused-variable
    target_list = []
    try:
        with ModularActionTimer(modaction, 'main', modaction.start_timer):
            with gzip.open(modaction.results_file, 'rt') as result_zip:
                for num, result in enumerate(csv.DictReader(result_zip)):
                    # set rid to row # (0->n) if unset
                    result.setdefault('rid', str(num))

                    logger.info("RESULTS: %s", result)

                    modaction.update(result)
                    modaction.invoke()

                    if modaction.target_field not in result:
                        logger.error(
                            "Specified field could not be found in event")
                        continue
                    else:
                        target_list.append(result[modaction.target_field])
                logger.debug('target list: ' + str(target_list))
                results = []
                for target in target_list:
                    output_events = run_query(dnsdb, target, modaction.query_type, modaction.rrtype, modaction.bailiwick,
                                              modaction.time_first_before, modaction.time_first_after,
                                              modaction.time_last_before, modaction.time_last_after, target_type=modaction.target_type)
                    results += output_events
                logger.debug('results: ' + str(results))
                for result in results:
                    logger.debug('result dict: ' + str(result))
                    modaction.addevent(raw=json.dumps(
                        result), sourcetype="dnsdb_ar_action")
                modaction.writeevents(index="main", source="dnsdb_ar_action")
     # This is standard chrome for outer exception handling
    except Exception as e:
        # adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print >> sys.stderr, "ERROR: %s" % e
        sys.exit(3)

    modaction.message("DNSDB lookup complete",
                      status='success', level=logging.INFO)


if __name__ == "__main__":
    run()
