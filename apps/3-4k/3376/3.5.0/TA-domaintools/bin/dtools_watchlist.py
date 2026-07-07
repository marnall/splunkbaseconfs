import csv
import gzip
import json
import logging
import logging.handlers
import sys
import re
import time
import base64
import datetime
import urllib
import urllib2
from datetime import datetime
from datetime import timedelta
import traceback
from domaintools import API
import dtools_credentials
import tldextract

# CORE SPLUNK IMPORTS
import splunk
import splunk.search as splunkSearch
from splunk.rest import simpleRequest
import splunk.version as ver
from time import strftime
from time import localtime
import splunk.auth
import splunk.search
import splunk.Intersplunk as si
from cim_actions import ModularAction
from Utils.app_env import AppEnv

tldextract_cached = tldextract.TLDExtract(cache_file=AppEnv.tldcache)

##
# Debugging : index=_internal (source=*_modalert.log* OR source=*_modworkflow.log*)


# ModularAction wrapper
class DomainToolsWatchlist(ModularAction):

    def __init__(self, settings, logger, action_name=None):
        super(DomainToolsWatchlist, self).__init__(settings, logger, action_name)

        self.domainfield = self.configuration.get('domainfield', None)
        self.email = self.configuration.get('email', None)
        self.org = self.configuration.get('org', None)
        self.registrar = self.configuration.get('registrar', None)
        self.ns = self.configuration.get('ns', None)

        self.logger.info("Domain Field = %s", self.domainfield)
        self.logger.info("E-mail  = %s", self.email)
        self.logger.info("Org = %s", self.org)
        self.logger.info("Registrar = %s", self.registrar)
        self.logger.info("Nameserver = %s", self.ns)


def watchlist(email, org, ns, registrar, orig_domain):
    app_env = AppEnv()
    lookup_path = os.path.join(app_env.lookups, "dtools_watchlist.csv")
    now = str(int(time.time()))
    if os.path.isfile(lookup_path):
        bl = open(lookup_path, 'a')
        bl_writer = csv.writer(bl, quoting=csv.QUOTE_ALL)
    else:
        bl = open(lookup_path, 'a')
        bl_writer = csv.writer(bl, quoting=csv.QUOTE_ALL)
        bl_writer.writerow(['email', 'org', 'ns', 'registrar', 'orig_domain', 'timestamp', 'match'])
    if email:
        bl_writer.writerow([email, '', '', '', orig_domain, now, 'true'])
    if org:
        bl_writer.writerow(['', org, '', '', orig_domain, now, 'true'])
    if registrar:
        bl_writer.writerow(['', '', '', registrar, orig_domain, now, 'true'])
    for server in ns:
        bl_writer.writerow(['', '', server, '', orig_domain, now, 'true'])
    bl.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

    try:
        app_env = AppEnv()
        # cool new way to get a logger - use this now!
        logger = ModularAction.setup_logger('dtools_watchlist_modalert')
        modaction = DomainToolsWatchlist(sys.stdin.read(), logger, 'dtools_watchlist')
        modaction.addinfo()
        session_key = modaction.session_key

        # process results
        with gzip.open(modaction.results_file, 'rb') as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                # set rid to row # (0->n) if unset
                result.setdefault('rid', str(num))
                logger.info("RESULTS: %s", result)
                modaction.update(result)
                modaction.invoke()
                username, api_key = dtools_credentials.getCredentials()
                domainfield = modaction.domainfield
                if not domainfield in result:
                    logger.error("Specified domain field could not be found in event")
                    break
                extracted = tldextract_cached(result[domainfield])
                if extracted.suffix == '':
                    domain = extracted.domain
                else:
                    domain = "%s.%s" % (extracted.domain, extracted.suffix)
                api = API(username, api_key, app_partner='splunk',
                          app_name=app_env.package_id, app_version=app_env.integration_version)
                results = api.parsed_whois(domain).response()
                watchlist_email = None
                watchlist_org = None
                watchlist_registrar = None
                watchlist_ns = []
                if modaction.email:
                    watchlist_email = results['parsed_whois']['contacts']['registrant']['email']
                if modaction.org:
                    watchlist_org = results['parsed_whois']['contacts']['registrant']['org']
                if modaction.registrar:
                    watchlist_registrar = results['parsed_whois']['registrar']['name']
                if modaction.ns:
                    for ns in results['parsed_whois']['name_servers']:
                        watchlist_ns.append(str(ns))
                watchlist(watchlist_email, watchlist_org, watchlist_ns, watchlist_registrar, domain)
                # THIS IS THE PROPER WAY TO WRITE EVENTS NOW
                # IF YOU WERE USING modaction.makeevents please switch
                #modaction.addevent("This Is Some Event: " + json.dumps(modaction.settings), 'checkphish' )
        # if modaction.writeevents(index='main',source=modaction.search_name):
        #    modaction.message('Successfully created splunk event', status='success', rids=modaction.rids)
        # else:
        #    modaction.message('Failed to create splunk event', status='failure',rids=modaction.rids, level=logging.ERROR)

    except Exception as e:
        # adding additional logging since adhoc search invocations do not write to stderr
        try:
            logger.critical(modaction.message(e, 'failure'))
        except:
            logger.critical(e)
            traceback.print_exc(file=sys.stderr)
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        sys.exit(3)
