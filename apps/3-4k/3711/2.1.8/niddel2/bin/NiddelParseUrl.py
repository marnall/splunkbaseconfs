"""Module: niddelparseurl.py
Application: Niddel Magnet app for Splunk
"""
import re, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))

import six
import ipaddress
from uritools import urisplit, uricompose
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

_SCHEME_PATTERN = re.compile("^:?(//)?")
_PASSWORD_PATTERN = re.compile(":[^:]*$")


@Configuration()
class NiddelParseUrlCommand(StreamingCommand):
    """ The niddelparseurl command will look for a net_dst_url field, parse its components (protocol, hostname and
    port at this point) and fill in the relevant fiels (net_l7proto, net_dst_domain and net_dst_port).

    ##Syntax

    .. code-block::
        niddelparseurl
    """

    def stream(self, events):
        """ Processes a batch of events by applying the process_event method on each one.
        :param events: the events sent to this command by the search
        """
        for evt in events:
            try:
                self.process_event(evt)
            except:
                self.logger.exception('exception raised while processing {}'.format(evt))
            finally:
                yield evt

    def process_event(self, event):
        """ Parses the URL field of an event and tries to fill in the other missing fields as appropriate.
        :param event: the event to process
        """
        raw_url = event.get('net_dst_url', 'NA')
        if raw_url != 'NA':
            url = urisplit(raw_url)

            # if we don't have a properly parsed URL with scheme and hostname, this means this might
            # be a truncated URL, let's try our best to use other fields to make sense of it
            if not url.scheme or not url.gethost():
                scheme = None
                try:
                    port = int(event.get('net_dst_port', 'NA'))
                    if port == 80:
                        scheme = 'http'
                    elif port == 443:
                        scheme = 'https'
                    elif port == 21:
                        scheme = 'ftp'
                except ValueError:
                    if event.get('net_l7proto', 'NA') != 'NA':
                        scheme = event['net_l7proto'].lower()
                    elif event.get('net_l4proto', 'NA').lower() == 'tcp':
                        scheme = 'tcp'
                if scheme:
                    url = urisplit(scheme + '://' + re.sub(_SCHEME_PATTERN, '', raw_url))

                # if we still can't parse it properly, raise an error
                if not url.scheme or not url.gethost():
                    raise ValueError('unable to parse URL "' + raw_url + '"')

            # remove password if present and update URL field with well-formed value
            if url.userinfo and re.search(_PASSWORD_PATTERN, url.userinfo):
                username = re.sub(_PASSWORD_PATTERN, '', url.userinfo)
                password = '*' * (len(url.userinfo) - len(username))
                event['net_dst_url'] = uricompose(scheme=url.scheme, path=url.path, query=url.query,
                                                  fragment=url.fragment,
                                                  userinfo=username + ':' + password,
                                                  host=url.host, port=url.port)
            else:
                event['net_dst_url'] = uricompose(scheme=url.scheme, path=url.path, query=url.query,
                                                  fragment=url.fragment, userinfo=url.userinfo,
                                                  host=url.host, port=url.port)

            # fill in destination hostname or IP address from URL, as this might help
            # with the inbound / outbound detection
            if isinstance(url.gethost(), (ipaddress.IPv4Address, ipaddress.IPv6Address)) \
                    and event.get('net_dst_ip', 'NA') == 'NA':
                event['net_dst_ip'] = str(url.gethost())
            elif isinstance(url.gethost(), six.string_types) \
                    and event.get('net_dst_domain', 'NA') == 'NA':
                event['net_dst_domain'] = url.gethost().lower()

            # fill in other missing fields on event based on what we parsed from the URL,
            # as this might improve aggregation
            if event.get('net_dst_port', 'NA') == 'NA':
                if url.getport():
                    event['net_dst_port'] = url.getport()
                elif url.getscheme():
                    if url.getscheme().lower() == 'http':
                        event['net_dst_port'] = 80
                    elif url.getscheme().lower() == 'https':
                        event['net_dst_port'] = 443
                    elif url.getscheme().lower() == 'ftp':
                        event['net_dst_port'] = 21

            if url.scheme and event.get('net_l7proto', 'NA') == 'NA' \
                    and url.scheme.upper() not in ('TCP', 'UDP', 'ICMP'):
                event['net_l7proto'] = url.scheme.upper()

            if url.scheme and event.get('net_l4proto', 'NA') == 'NA':
                scheme = url.scheme.lower()
                if scheme in {"http", "https", "ftp", "tcp"}:
                    event['net_l4proto'] = "TCP"
                elif scheme == "udp":
                    event['net_l4proto'] = "UDP"
                else:
                    event['net_l4proto'] = "NA"


dispatch(NiddelParseUrlCommand, sys.argv, sys.stdin, sys.stdout, __name__)
