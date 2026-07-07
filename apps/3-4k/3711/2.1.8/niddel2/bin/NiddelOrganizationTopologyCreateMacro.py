# coding=utf-8
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

@Configuration()
class NiddelOrganizationTopologyCreateMacro(StreamingCommand):
    orgid = Option(require=True)

    def __init__(self):
        super(NiddelOrganizationTopologyCreateMacro, self).__init__()

    def stream(self, events):
        try:
            for top in events:
                value = 'false()'
                domains = top['domains'].split()
                if len(domains) > 0:
                    for idx, domain in enumerate(domains):
                        domains[idx] = '$domain$ == "' + domain + '" OR like($domain$, "%.' + domain + '")'
                    value = '(' + ' OR '.join(domains) + ')'
                self.service.post('properties/macros', __stanza='domains-' + self.orgid + '(1)')
                self.service.post('properties/macros/domains-' + self.orgid + '(1)', definition=value, args='domain')

                value = 'false()'
                ipsubnets = top['ipSubnets'].split()
                if len(ipsubnets) > 0:
                    for idx, ipsubnet in enumerate(ipsubnets):
                        ipsubnets[idx] = 'cidrmatch("' + ipsubnet + '", $ip$)'
                    value = '(' + ' OR '.join(ipsubnets) + ')'
                self.service.post('properties/macros', __stanza='public_subnets-' + self.orgid + '(1)')
                self.service.post('properties/macros/public_subnets-' + self.orgid + '(1)', definition=value, args='ip')
                yield top
        except Exception as e:
            self.logger.exception("unable to generate events")
            raise e

dispatch(NiddelOrganizationTopologyCreateMacro, sys.argv, sys.stdin, sys.stdout, __name__)