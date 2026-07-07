#!/usr/bin/python

import csv      ## Result set is in CSV format
import gzip     ## Result set is gzipped
import logging  ## For specifying log levels
import sys      ## For appending the library path
import urllib   ## For url encoding
import json
import action_util
from CorvilApiStreamingClient import *
from config_util import *

## Importing the cim_actions.py library
## A.  Import make_splunkhome_path
## B.  Append your library path to sys.path
## C.  Import ModularAction from cim_actions
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_actions import ModularAction

## Retrieve a logging instance from ModularAction
## It is required that this endswith _modalert
logger = ModularAction.setup_logger('targetedpacketcapture_modalert')

## Subclass ModularAction for purposes of implementing
## a script specific dowork() method
class TargetedPacketCaptureModularAction(ModularAction):

    CNE_URL_TO_INSPECT_DATA = "%s://%s/ui#/networkdata?dashboard=%s&session=%s"

    def __init__(self, settings, logger, action_name=None):
        super(TargetedPacketCaptureModularAction, self).__init__(settings, logger, action_name)

        orig_raw_string = self.configuration.get('orig_raw')
        try:
            self.orig_raw = json.loads(orig_raw_string.replace('\\', '"'))
        except Exception ,e:
            logger.debug("Source event is not in expected JSON format.")
            self.orig_raw = None
        self.config = None

        self.cne_host = self.configuration.get('cne_host')
        if not self.cne_host:
            if self.orig_raw:
                self.cne_host = self.orig_raw.get('CNEHost')
            # CNE Host is not present in source event most probably when it is not a Corvil event, fetch the hostname
            # from the input config
            if not self.cne_host:
                configs = InputsConfig.get_all_configs(additional_namespaces=[self.app], session_key=self.session_key)
                if len(configs) == 0:
                    logger.error("No inputs config found. Check data inputs.")
                    self.config = None
                else:
                    self.config = configs[0]
                    self.cne_host = self.config.host

        self.src_ip = self.configuration.get('src_ip')
        if not self.src_ip and self.orig_raw:
            # Original event doesn't have the alias field so look check all field names to get the Source IP.
            self.src_ip = self.orig_raw.get('src_ip') or self.orig_raw.get('SrcIP') or self.orig_raw.get('SrcIp')

        self.prefix = self.configuration.get('session_prepend_text')
        self.suspicious_session = "%s%s" % (self.prefix, self.src_ip)
        self.inspect_data_dashboard = self.configuration.get('inspect_data_dashboard', 'Investigate Host')

        file = open('session_config.txt', 'r')
        self.session_config = file.read() % \
                         (self.suspicious_session, self.src_ip, self.suspicious_session, self.suspicious_session)

    def validate(self):
        if not self.cne_host or not self.src_ip or not self.inspect_data_dashboard:
            logger.error('Failed to track the suspicious host because of few invalid parameters. '
                         'CNE Host, Source IP and Dashboard Name are required to run this action.')
            raise Exception('Failed to track the suspicious host because of few invalid parameters. '
                            'CNE Host, Source IP and Dashboard Name are required to run this action.')


    def dowork(self):
        '''
        Check if the session is present on CNE if yes then generate Inspect Data URL
        of CNE for that session, otherwise install that session on CNE and then generate URL.
        '''
        success = True
        if not self.config:
            configs = InputsConfig.from_host(self.cne_host, additional_namespaces=[self.app], session_key=self.session_key)

            if len(configs) == 0:
                logger.error("No inputs config found. Check data inputs.")
                raise Exception("No inputs config found")

            self.config = configs[0]

        self.config.username, self.config.password = action_util.fetch_valid_credentials(self.config.username,
            self.config.password, self.config.auth_script, self.config.use_auth_script, self.cne_host, self.session_key)

        self.protocolUsed, client = action_util.get_client(self.cne_host, int(self.config.port), self.config.username,
                                            self.config.password, int(self.config.encrypted), corvil_api_mtom_client=True)
        logger.info("Connection with host %s is established using %s mode" % (self.cne_host, self.protocolUsed))

        # Try to get all the channels
        sc = client.getSudsClient()
        summary = sc.service.getSummary("", client.createObject("ns0:ReportingPeriod")['1-hour'])
        channels = summary.channel
        mps = set()

        # Check if Suspicious Session is present in CNE channels:
        for channel in channels:
            if urllib.unquote(channel._name).endswith(self.suspicious_session):
                mps.add(channel._name)
                logger.info("Session '%s' is present on Corvil Appliance '%s'." % \
                            (self.suspicious_session, self.cne_host))
                break

        # Create a Suspicious Session, if it is not present.
        if len(mps) == 0:
            logger.info("Trying to create a session on Corvil Appliance...")
            success = action_util.create_session(self.config.username, self.config.password, self.cne_host, self.suspicious_session, self.session_config, logger)

        if success:
            url_to_cne = TargetedPacketCaptureModularAction.CNE_URL_TO_INSPECT_DATA % (self.protocolUsed, self.cne_host,
                                                                                       urllib.quote(self.inspect_data_dashboard),
                                                                                       self.suspicious_session)
            self.message('Use the URL to access the Corvil session which is being used to capture packets and'
                         ' analyze traffic for the involved host.', status='success', URL=url_to_cne, protocol=self.protocolUsed, CNEHost=self.cne_host)
        else:
            self.message("Failed to create session '%s' on Corvil Appliance '%s'" %
                         (self.suspicious_session, self.cne_host), status='failure')

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

    try:
        modaction = TargetedPacketCaptureModularAction(sys.stdin.read(), logger, 'targetedpacketcapture')

        ## process results
        fh = gzip.open(modaction.results_file, 'rb')
        for num, result in enumerate(csv.DictReader(fh)):
            result.setdefault('rid', str(num))
            modaction.update(result)
            modaction.invoke()
            modaction.validate()
            modaction.dowork()

    except Exception, e:
        ## adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print >> sys.stderr, "ERROR: %s" % e
        sys.exit(3)
