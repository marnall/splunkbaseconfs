#!/usr/bin/env python

import sys
import socket
import re
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class dnsresolver(StreamingCommand):

    inpf = Option(
        doc='''
        **Syntax:** **input=***<input_field_name>*
        **Description:** Name of the field containing URL or domain name string.''',
        require=True, validate=validators.Fieldname())

    outf = Option(
        doc='''
        **Syntax:** **output=***<output_field_name>*
        **Description:** Customize the name of the field that will contain the resolved IPv4 address.''',
        require=False, default="ipv4_addr")

    outfipv6 = Option(
        doc='''
        **Syntax:** **output=***<output_field_name>*
        **Description:** Customize the name of the field that will contain the resolved IPv6 address.''',
        require=False, default="ipv6_addr")

    port = Option(
        doc='''
        **Syntax:** **port=***80*
        **Description:** Speficy the port to use in calling the `getaddrinfo` function.''',
        require=False, default="80")

    verbose = Option(
        doc='''
        **Syntax:** **verbose=***<true|false>*
        **Description:** Set to true to generate more fields such as `ipv6_addr`, `fqdn`, and `addr_info`''',
        require=False, default=False, validate=validators.Boolean())

    first_match_only = Option(
        doc='''
        **Syntax:** **first_match_only=***<true|false>*
        **Description:** Set to true to avoid Multi-Value fields and only pick the first result''',
        require=False, default=False, validate=validators.Boolean())

    def stream(self, events):

        if self.outf.__eq__(self.outfipv6):
            raise Exception("Field names for output of IPv4 and IPv6 address must not be the same.")

        for event in events:

            resolved = self.resolver(event[self.inpf], self.port)

            addrinfo_proto4 = resolved[1]
            addrinfo_proto6 = resolved[2]

            if addrinfo_proto4 is not None:

                if self.first_match_only:
                    event[self.outf] = addrinfo_proto4[0][4][0]
                else:
                    ipv4 = []
                    for i in addrinfo_proto4: ipv4.append(i[4][0])
                    event[self.outf] = list(set(ipv4))

                if self.verbose:

                    outfipv6 = ''

                    if self.first_match_only:
                        fqdn = socket.getfqdn(addrinfo_proto4[0][4][0])
                        if addrinfo_proto6 is not None:
                            outfipv6 = addrinfo_proto6[0][4][0]
                    else:
                        fqdn = []
                        for ip in list(set(ipv4)): fqdn.append(socket.getfqdn(ip))
                        if addrinfo_proto6 is not None:
                            ipv6 = []
                            for i in addrinfo_proto6: ipv6.append(i[4][0])
                            outfipv6 = list(set(ipv6))
                    
                    
                    event[self.outfipv6] = '' if outfipv6 is None else outfipv6
                    event['fqdn'] = fqdn
                    event['treated_url'] = resolved[0]

            yield event

    @staticmethod
    def resolver(url, port=80):

        url_treated = re.findall('^(?:https?\:\/\/)?([^\:\/]+)[\:\/]?', url)

        url_treated = url_treated[0] if url_treated else ""

        try:
            addrinfo_proto4 = socket.getaddrinfo(
                url_treated, port, socket.AF_INET)
        except:
            addrinfo_proto4 = None

        try:
            addrinfo_proto6 = socket.getaddrinfo(
                url_treated, port, socket.AF_INET6)
        except:
            addrinfo_proto6 = None

        return (url_treated, addrinfo_proto4, addrinfo_proto6)


dispatch(dnsresolver, sys.argv, sys.stdin, sys.stdout, __name__)
