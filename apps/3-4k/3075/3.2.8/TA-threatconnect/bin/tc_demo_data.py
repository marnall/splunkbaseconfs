#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Demo Data Generator Command."""
import json
import os
import random
import string
import sys
import time
from typing import Dict, Tuple
import uuid
from collections import OrderedDict
from datetime import datetime
from random import randint

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class DemoData(BaseGeneratingCommand):
    """Playbook download command."""

    # args
    address_count = Option(
        default=1000, doc='The number of ip address events to create.', require=False
    )
    email_address_count = Option(
        default=1000, doc='The number of email address events to create.', require=False
    )
    earliest_seconds = Option(doc='Earliest timestamp for generated events.', require=False)
    host_count = Option(default=1000, doc='The number of host events to create.', require=False)
    url_count = Option(default=1000, doc='The number of url events to create.', require=False)

    # properties
    filename = os.path.basename(__file__)

    @staticmethod
    def _event_summary(
        event: str,
        event_time: str,
        indicator: str,
        indicator_type: str,
        sourcetype: str,
        victim: str,
    ) -> dict:
        """Return the event summary."""
        event_summary = OrderedDict()
        event_summary['timestamp'] = event_time
        event_summary['diamondType'] = 'Infrastructure'
        event_summary['diamondVictim'] = victim
        event_summary['eventCd'] = 'no-cd'
        event_summary['eventIndexTime'] = event_time
        event_summary['eventRaw'] = event
        event_summary['eventSourcetype'] = sourcetype
        event_summary['eventTime'] = event_time
        event_summary['indicator'] = indicator
        event_summary['indicatorType'] = indicator_type
        event_summary['searchMethod'] = 'auto'
        event_summary['searchName'] = 'tcdemo generated event'
        event_summary['searchString'] = 'tcdemo generated event'
        event_summary['labels'] = ['New']
        event_summary['uuid'] = str(uuid.uuid4())

        return event_summary

    @property
    def _random_port(self):
        """Return a random port number"""
        return random.randint(1024, 65535)  # nosec

    def event_address(self, indicator: str, victim: str, event_time: int) -> str:
        """Return an event"""
        event_type_map = {
            'pfsense': self.event_pfsense,
            'sophos': self.event_sophos,
        }
        event_type = random.choice(['pfsense', 'sophos'])  # nosec
        return event_type_map.get(event_type)(indicator, victim, event_time)

    @staticmethod
    def event_bluecoat_proxy(indicator: str, victim: str, event_time: int) -> Tuple[str, str]:
        """Return a pfsense event."""
        event_datetime = datetime.fromtimestamp(event_time).strftime('%Y-%m-%d %H:%M:%S')
        return (
            (
                f'{event_datetime} '
                f'{victim} '
                '1365 33 TCP_ERR_MISS 400 0 0 7 - - DENIED GET '
                '129.188.69.98 HTTP/0.9 0 '
                f'{indicator} '
                '- - - -'
            ),
            'bluecoat:proxysg:access:file',
        )

    @staticmethod
    def event_bro_dns(indicator: str, victim: str, event_time: int) -> Tuple[str, str]:
        """Return a pfsense event."""
        return (
            (
                f'{event_time}	c2vBw3VX7fg	'
                f'{victim}	'
                '54460	10.152.11.202	53	udp	63891	'
                f'{indicator}  '
                '1	C_INTERNET	16	TXT	-	-	F	F	T	F	0	-	-'
            ),
            'bro_dns',
        )

    def event_pfsense(self, indicator: str, victim: str, event_time: int) -> Tuple[str, str]:
        """Return a pfsense event."""
        event_datetime = datetime.fromtimestamp(event_time).strftime('%b %d %H:%M:%S')
        protocol = random.choice(['tcp', 'udp'])  # nosec
        if protocol == 'udp':
            return (
                (
                    f'{event_datetime} filterlog: 5,,,1000000103,bce1,match,block,in,'
                    f'4,0x0,,64,35339,0,DF,17,{protocol},73,{indicator},{victim},'
                    f'{self._random_port},{self._random_port},53'
                ),
                'pfsense:filterlog',
            )

        return (
            (
                f'{event_datetime} filterlog: 5,,,1000000103,bce3,match,block,in,'
                f'4,0x0,,240,58133,0,none,6,tcp,40,{indicator},{victim},'
                f'{self._random_port},{self._random_port},0,S,3127989332,,1024,,'
            ),
            'pfsense:filterlog',
        )

    def event_sophos(self, indicator: str, victim: str, event_time: int) -> Tuple[str, str]:
        """Return a sophos event."""
        event_datetime = datetime.fromtimestamp(event_time).strftime('%Y-%m-%dT%H:%M:%SZ')
        return (
            (
                f'{event_datetime} firewall-1 ulogd[25202]: id="2001" severity="critical" '
                'sys="SecureNet" sub="packetfilter" name="Packet dropped" action="drop" '
                'fwrule="60001" initf="eth0" outitf="eth1" srcmac="0:25:90:31:f:c7" '
                'dstmac="0:25:90:34:ab:5c" '
                f'srcip="{indicator}" dstip="{victim}" proto="17" length="30" '
                f'tos="0x00" prec="0x00" ttl="64" srcport="{self._random_port}" '
                f'dstport="{self._random_port}" tcpflags="SYN"'
            ),
            'sophos:utm:firewall',
        )

    @staticmethod
    def event_stream_smtp(indicator: str, victim: str, event_time: int) -> Tuple[str, str]:
        """Return a stream smtp event."""
        event_datetime = datetime.fromtimestamp(event_time).strftime('%Y-%m-%dT%H:%M:%SZ')
        return (
            (
                '{'
                f'"timestamp": "{event_datetime}", '
                '"bytes": 364, '
                '"bytes_in": 364, '
                '"bytes_out": 0, '
                '"content_body": "http://www.timesofindia.com/ ", '
                '"content_transfer_encoding": "8bit", '
                '"date": "Thu, 10 Jul 2014 14:32:42 -0700", '
                '"dest_ip": "118.104.156.169", '
                '"dest_mac": "00:15:2C:0E:6C:00", '
                '"dest_port": 25, '
                '"email_index": "9", '
                '"mime_type": "text/plain", '
                f'"receiver": "{victim}", '
                f'"receiver_email": "{victim}", '
                '"receiver_type": "TO", '
                f'"sender": "{indicator}", '
                f'"sender_email": "{indicator}", '
                '"src_ip": "250.69.226.39", '
                '"src_mac": "00:50:56:92:3D:AE", '
                '"src_port": 50847, '
                '"subject": "Test Email - 2", '
                '"time_taken": 256235, '
                '"transport": "tcp" '
                '}'
            ),
            'stream:smtp',
        )

    @property
    def event_victim_address(self):
        """Return a random diamond victim (address)."""
        return f'10.20.30.{randint(1, 254)}'  # nosec

    @property
    def event_victim_email_address(self):
        """Return a random diamond victim (email address)."""
        tld = random.choice(['com', 'net', 'org'])  # nosec
        username = ''.join(
            random.choice(string.ascii_letters) for _ in range(randint(5, 9))  # nosec
        )
        domain = ''.join(random.choice(string.ascii_letters) for _ in range(randint(5, 9)))  # nosec
        return f'{username}@{domain}.{tld}'

    @property
    def event_time(self):
        """Return a random event time."""
        earliest_seconds = int(self.earliest_seconds or 5000000)
        return time.time() - randint(0, earliest_seconds)  # nosec

    @staticmethod
    def event_data(event_summary: Dict[str, str], indicator_data: Dict[str, str]) -> Dict[str, str]:
        """Build the event data to store in KV Store.

        Args:
            event_summary (dict): The event summary data.
            indicator_data (dict): The indicator data.

        Returns:
            collection.OrderedDict: The complete event data.
        """
        event_data = OrderedDict()
        event_data['timestamp'] = event_summary.get('timestamp')
        event_data['indicator'] = event_summary.get('indicator')
        event_data['indicatorId'] = indicator_data.get('id')
        event_data['indicatorDateAdded'] = indicator_data.get('dateAdded')
        event_data['indicatorLastModified'] = indicator_data.get('lastModified')
        event_data['indicatorOwnerName'] = indicator_data.get('ownerName')
        event_data['indicatorType'] = indicator_data.get('type')
        event_data['indicatorWebLink'] = indicator_data.get('webLink')
        event_data['indicatorConfidence'] = indicator_data.get('confidence', '')
        event_data['indicatorRating'] = indicator_data.get('rating', '')
        event_data['indicatorTags'] = [tag.get('name') for tag in indicator_data.get('tag', [])]
        # event_data['indicatorAssociations'] = ga
        event_data['uuid'] = event_summary.get('uuid')
        return event_data

    def generate(self):
        """Implement generate method for demo data and results."""
        self.generate_address_events()
        self.generate_email_address_events()
        self.generate_host_events()
        self.generate_url_events()

        # display results
        for r in self.results:
            yield r

    def generate_address_events(self):
        """Generate address events."""
        count = 1
        for indicator_data in self.tcs.collections.indicators.paginate(
            fields='indicator', query={'type': 'Address'}
        ):
            event_time = self.event_time
            indicator = indicator_data.get('indicator')
            victim = self.event_victim_address

            event, sourcetype = self.event_address(indicator, victim, event_time)
            event_summary = self._event_summary(
                event, event_time, indicator, 'Address', sourcetype, victim
            )

            self.tcs.collections.event_summaries.batch_data(event_summary)
            self.results.append(event_summary)

            # process event data
            fields = '_key,confidence,dateAdded,id,lastModified,ownerName,rating,tag,type,webLink'
            query = {'type': 'Address', 'indicator': indicator}
            for address_data in self.tcs.collections.indicators.paginate(
                fields=fields, query=query
            ):
                event_data = self.event_data(event_summary, address_data)
                self.service.tc_index('tc_event_data').submit(
                    json.dumps(event_data),
                    source='threatconnect-search-datamodel',
                    sourcetype='threatconnect-event-data',
                )

            # only process up to max count
            if count >= self.address_count:
                break

            # increment count
            count += 1

        # save any remaining events
        self.tcs.collections.event_summaries.batch_save()

    def generate_email_address_events(self):
        """Generate email address events."""
        for count, indicator_data in enumerate(
            self.tcs.collections.indicators.paginate(
                fields='indicator', query={'type': 'EmailAddress'}
            )
        ):
            event_time = self.event_time
            indicator = indicator_data.get('indicator')
            victim = self.event_victim_email_address

            event, sourcetype = self.event_stream_smtp(indicator, victim, event_time)
            event_summary = self._event_summary(
                event, event_time, indicator, 'EmailAddress', sourcetype, victim
            )

            self.tcs.collections.event_summaries.batch_data(event_summary)
            self.results.append(event_summary)

            # process event data
            fields = '_key,confidence,dateAdded,id,lastModified,ownerName,rating,tag,type,webLink'
            query = {'type': 'EmailAddress', 'indicator': indicator}
            for address_data in self.tcs.collections.indicators.paginate(
                fields=fields, query=query
            ):
                event_data = self.event_data(event_summary, address_data)
                self.service.tc_index('tc_event_data').submit(
                    json.dumps(event_data),
                    source='threatconnect-search-datamodel',
                    sourcetype='threatconnect-event-data',
                )

            # only process up to max count
            if count >= self.email_address_count:
                break

        # save any remaining events
        self.tcs.collections.event_summaries.batch_save()

    def generate_host_events(self):
        """Generate host events."""
        for count, indicator_data in enumerate(
            self.tcs.collections.indicators.paginate(fields='indicator', query={'type': 'Host'})
        ):
            event_time = self.event_time
            indicator = indicator_data.get('indicator')
            victim = self.event_victim_email_address

            event, sourcetype = self.event_bro_dns(indicator, victim, event_time)
            event_summary = self._event_summary(
                event, event_time, indicator, 'Host', sourcetype, victim
            )

            self.tcs.collections.event_summaries.batch_data(event_summary)
            self.results.append(event_summary)

            # process event data
            fields = '_key,confidence,dateAdded,id,lastModified,ownerName,rating,tag,type,webLink'
            query = {'type': 'Host', 'indicator': indicator}
            for address_data in self.tcs.collections.indicators.paginate(
                fields=fields, query=query
            ):
                event_data = self.event_data(event_summary, address_data)
                self.service.tc_index('tc_event_data').submit(
                    json.dumps(event_data),
                    source='threatconnect-search-datamodel',
                    sourcetype='threatconnect-event-data',
                )

            # only process up to max count
            if count >= self.email_address_count:
                break

        # save any remaining events
        self.tcs.collections.event_summaries.batch_save()

    def generate_url_events(self):
        """Generate host events."""
        for count, indicator_data in enumerate(
            self.tcs.collections.indicators.paginate(fields='indicator', query={'type': 'URL'})
        ):
            event_time = self.event_time
            indicator = indicator_data.get('indicator')
            victim = self.event_victim_email_address

            event, sourcetype = self.event_bluecoat_proxy(indicator, victim, event_time)
            event_summary = self._event_summary(
                event, event_time, indicator, 'URL', sourcetype, victim
            )

            self.tcs.collections.event_summaries.batch_data(event_summary)
            self.results.append(event_summary)

            # process event data
            fields = '_key,confidence,dateAdded,id,lastModified,ownerName,rating,tag,type,webLink'
            query = {'type': 'URL', 'indicator': indicator}
            for address_data in self.tcs.collections.indicators.paginate(
                fields=fields, query=query
            ):
                event_data = self.event_data(event_summary, address_data)
                self.service.tc_index('tc_event_data').submit(
                    json.dumps(event_data),
                    source='threatconnect-search-datamodel',
                    sourcetype='threatconnect-event-data',
                )

            # only process up to max count
            if count >= self.email_address_count:
                break

        # save any remaining events
        self.tcs.collections.event_summaries.batch_save()

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.address_count = int(self.address_count)
        self.email_address_count = int(self.email_address_count)
        self.host_count = int(self.host_count)


if __name__ == '__main__':
    dispatch(DemoData, sys.argv, sys.stdin, sys.stdout, __name__)
