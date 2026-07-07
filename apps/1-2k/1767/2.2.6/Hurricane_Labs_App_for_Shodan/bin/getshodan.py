#!/usr/bin/env python

""" Python custom command for querying Shodan API """

# pylint: disable=wrong-import-position

import datetime
import json
import os
import sys
import time

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "Hurricane_Labs_App_for_Shodan", "lib")
)

from shodan import Shodan
from splunk import entity
from splunk.clilib import cli_common as cli
from splunklib.searchcommands import (Configuration, GeneratingCommand, Option,
                                      dispatch, validators)

# pylint: enable=wrong-import-position


def get_credentials(session_key):
    """
    Retrieves credentials from encrypted credential store.
    """
    myapp = 'Hurricane_Labs_App_for_Shodan'
    try:
        # list all credentials
        entities = entity.getEntities(
            ['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=session_key
        )
    except Exception as unknown_exception:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Could not get {myapp} credentials from splunk."
                        f"Error: {str(unknown_exception)}"
                        ) from unknown_exception

    # grab first set of credentials
    last = None
    for stanza in list(entities.values()):
        if stanza['eai:acl']['app'] == myapp:
            last = stanza['clear_password']

    if not last:
        sys.exit(0)
    return last


@Configuration(type="events")
class ShodanCommand(GeneratingCommand):
    """ SCP V2 Command definition """
    netlist = Option(require=False, validate=validators.List())

    @staticmethod
    def build_header(events):
        """
        Apparently in SCPv2, the fields from the first yielded event are considered the
        authoritative header. Any fields in later events that aren't present in the first event are
        ignored. In order to circumvent this, I generate a header first before yielding any events.
        """
        header = []
        for event in events:
            for key in list(event.keys()):
                if key not in header:
                    header.append(key)
        return header

    @staticmethod
    def format_event(event, query, header):
        """
        Takes a search result from Shodan API and formats it to be more Splunk-friendly. query is
        the original Shodan query.
        """
        event["_raw"] = json.dumps(event)
        event["source"] = "shodan"
        event["sourcetype"] = "shodan"
        event["query"] = query
        event["data"] = json.dumps(event["data"]).replace('"', '')\
            .replace('\\n\\t', '').replace('\\t', '').replace('\\n', '').replace('\\r', '')

        if "timestamp" in event:
            try:
                dt = datetime.datetime.strptime(
                    event["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                dt = datetime.datetime.strptime(
                    event["timestamp"], "%Y-%m-%dT%H:%M:%S")
            event["_time"] = time.mktime(dt.timetuple())
        else:
            event["_time"] = time.time()

        if "ip_str" in event:
            event["host"] = event["ip_str"]
        else:
            event["host"] = "shodan"

        if "location" in event:
            location = event.pop("location")
            for k in location:
                new_k = f"location_{k}"
                event[new_k] = location[k]
        for key in header:
            if key not in event:
                event[key] = None
        return event

    def generate(self):
        """
        Main GeneratingCommand function. Makes Shodan query(s) and then passes to format_event.
        """
        session_key = self.metadata.searchinfo.session_key
        cfg = cli.getConfStanza('shodan', 'config')
        proxy_cfg = cli.getConfStanza('shodan', 'proxy')
        proxy_dict = {
            'http': proxy_cfg.get('http'),
            'https': proxy_cfg.get('https')
        }
        api_key = get_credentials(session_key)
        api = Shodan(api_key, proxies=proxy_dict)
        max_pages = int(cfg['max_pages'])
        results = []
        if max_pages < 0:
            self.error_exit(None,
                            message=f"max_pages must be a non-negative integer. got {max_pages}")
        if self.netlist:
            for net in self.netlist:
                query = f"net:{net}"
                current_page = 1
                while current_page <= max_pages:
                    results += api.search(query, page=current_page)['matches']
                    time.sleep(1)
                    current_page += 1
        else:
            query = ' '.join(self.metadata.searchinfo.raw_args)
            current_page = 1
            while current_page <= max_pages:
                results += api.search(query, page=current_page)['matches']
                time.sleep(1)
                current_page += 1
        header = self.build_header(results)
        for event in results:
            event = self.format_event(event, query, header)
            yield event


dispatch(ShodanCommand, sys.argv, sys.stdin, sys.stdout, __name__)
