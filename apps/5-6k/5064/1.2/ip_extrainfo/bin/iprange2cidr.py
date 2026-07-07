#!/usr/bin/env python

###########
# Author: Lukas Utz <lutz@splunk.com>
# Date: 10 January 2022
###########

import sys
import os
import ipaddress

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class IpRange2Cidr(StreamingCommand):

    opt_ip_from = Option(
        doc='''
        **Syntax:** **ip_from=***<fieldname>*
        **Description:** Fieldname containing IP range "from" info."
        **Default:** ip_from*''',
        name='ip_from',
        require=False,
        default='ip_from',
        validate=validators.Fieldname())

    opt_ip_to = Option(
        doc='''
        **Syntax:** **ip_to=***<fieldname>*
        **Description:** Fieldname containing IP range "to" info."
        **Default:** ip_to*''',
        name='ip_to',
        require=False,
        default='ip_to',
        validate=validators.Fieldname())

    def stream(self, events):

        for event in events:
            startip = ipaddress.ip_address(str(event[self.opt_ip_from]))
            endip = ipaddress.ip_address(str(event[self.opt_ip_to]))
            tmp_cidrs = [ipaddr for ipaddr in ipaddress.summarize_address_range(startip, endip)]
            cidrs = []
            for cidr in tmp_cidrs:
                cidrs.append(str(cidr))
            event['ip_cidr'] = cidrs
            yield event

dispatch(IpRange2Cidr, sys.argv, sys.stdin, sys.stdout, __name__)
