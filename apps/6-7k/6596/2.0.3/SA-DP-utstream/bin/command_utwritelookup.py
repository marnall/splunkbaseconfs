#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_utwritelookup.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals

# Import modules from system
import sys, os, uuid, io, csv, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from splunklib import client

from utstream.service_cribl_instance import CriblInstanceService
from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction

from utstream_template.factory_logger import Logger
from utstream_template.service_proxy import ProxyService

@Configuration()
class utwritelookup(EventingCommand):
    """ 
    ##Syntax

    | inputlookup <lookup_name> | utwritelookup instance="<cribl_instance>" lookup_name="<lookup_name>"

    ##Description

    Custom search command to write result set of a search to a lookup table in Cribl Stream.

    """

    app_owner = "admin"

    instance = Option(require=True)
    lookup_name = Option(require=True)
    append = Option(default=False)
    create_empty = Option(default=False)
    override_if_empty = Option(default=False)

    cribl_instance = None
    logger = None

    def transform(self, events):
        self.uuid = str(uuid.uuid4())
        self.logger = Logger('command', self.uuid)

        try:

            # Validate arguments
            self._validate_args()

            if self.append and len(self.instance.split(",")) > 1:
                raise Exception("Cannot append to multiple instances")

            self.cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            self.proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            self.cribl_objects = []

            for instance in self.instance.split(","):
                # Get instance
                cribl_object = self.cribl_instance_service.get_instance(instance)
                if cribl_object is None:
                    raise Exception("Instance {} not found".format(instance))
                self.cribl_objects.append(cribl_object)


            if self.append:
                yield from self._append_to_lookup(events)
            else:
                yield from self._write_to_lookup(events)


        except Exception as e:
            self.logger.error("action=\"\"failed\"\",status=\"failure\",result=\"failed\",error=\"{}\"".format(e))
            self.logger.error(traceback.format_exc())
            raise e


    def _append_to_lookup(self, events):
        # Get existing lookup data
        cribl_interaction_helper = HelperCriblInstanceInteraction(instance=self.cribl_objects[0], uuid=self.uuid, proxy=self.proxy_service.get_httpx_info())

        self.logger.error("action=\"get_lookup_file\",status=\"start\",result=\"success\"")

        existing_lookup_file_rows = [row for row in cribl_interaction_helper.get_lookup_file(self.lookup_name)]


        self.logger.error("action=\"get_lookup_file\",status=\"end\",result=\"success\"")
        self.logger.error("action=\"build_event_list\",status=\"start\",result=\"success\"")

        event_list = [dict(zip(event.keys(), event.values())) for event in events]

        self.logger.error("action=\"build_event_list\",status=\"end\",result=\"success\"")

        self.write_info(f"Fetched {len(existing_lookup_file_rows)} rows from lookup {self.lookup_name}")

        # Parse events and build lookup
        out = io.StringIO()
        csv_writer = None
        parsed_events = ""

        # Yield only new events
        for event in event_list:
            yield event

        self.write_info(f"Appending {len(event_list)} rows to lookup {self.lookup_name}")

        # Append new events to existing lookup
        event_list.extend(existing_lookup_file_rows)

        # Get all keys in existing lookup and events
        all_keys = set().union(*(d.keys() for d in event_list))

        # Build new parsed events
        for event in event_list:
            if csv_writer is None:
                csv_writer = csv.DictWriter(out, fieldnames=all_keys, extrasaction='ignore')
                csv_writer.writeheader()
            csv_writer.writerow(event)
        parsed_events = out.getvalue()
                        
        self.write_info(f"Starting to write {len(event_list)} rows to lookup {self.lookup_name}")

        # Update the lookup
        lookup_dict = cribl_interaction_helper.update_lookup(self.lookup_name, parsed_events, self.lookup_type)
        self.write_info("Results written to file {} on Cribl Stream instance {}".format(self.lookup_name, cribl_interaction_helper.used_url))


    def _write_to_lookup(self, events):

        # Parse events and build lookup
        out = io.StringIO()
        csv_writer = None
        parsed_events = ""

        # Build parsed_events
        for event in events:
            yield event
            if csv_writer is None:
                csv_writer = csv.DictWriter(out, fieldnames=event.keys())
                csv_writer.writeheader()
            csv_writer.writerow(event)
        parsed_events = out.getvalue()

        for cribl_object in self.cribl_objects:
            cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=self.proxy_service.get_httpx_info())

            lookup_dict = cribl_interaction_helper.get_lookup(self.lookup_name)

            # Write lookup and inform user
            if lookup_dict is None:
                # Check if there are any results passed to the command
                if len(parsed_events) == 0:
                    # If create_empty=true, create an empty lookup
                    if self.create_empty:
                        lookup_dict = cribl_interaction_helper.create_lookup(self.lookup_name, parsed_events, self.lookup_type)
                        self.write_info("No results. Created empty file %s" % self.lookup_name)
                    else:
                        self.write_info("Found no results to write to file %s" % self.lookup_name)
                else:
                    lookup_dict = cribl_interaction_helper.create_lookup(self.lookup_name, parsed_events, self.lookup_type)
                    self.write_info("Results written to file {} on Cribl Stream instance {}".format(self.lookup_name, cribl_interaction_helper.used_url))
            else:
                # Check if there are any results passed to the command
                if len(parsed_events) == 0:
                    # If override_if_empty=true, override the lookup
                    if self.override_if_empty:
                        lookup_dict = cribl_interaction_helper.update_lookup(self.lookup_name, parsed_events, self.lookup_type)
                        self.write_info("No results. Created empty file %s" % self.lookup_name)
                    else:
                        self.write_info("No results. Retaining existing lookup file %s" % self.lookup_name)
                else:
                    # Update the lookup
                    lookup_dict = cribl_interaction_helper.update_lookup(self.lookup_name, parsed_events, self.lookup_type)
                    self.write_info("Results written to file {} on Cribl Stream instance {}".format(self.lookup_name, cribl_interaction_helper.used_url))


    def _str2bool(self, v):
        if isinstance(v, bool):
            return v
        return v.lower() in ("yes", "true", "t", "1")


    def _validate_args(self):
        if self.lookup_name.endswith(".csv"):
            self.lookup_type = "csv"
        elif self.lookup_name.endswith(".gz"):
            self.lookup_type = "gz"
        else:
            raise Exception("Lookup name must end with .csv or .gz")

        self.append = self._str2bool(self.append)
        self.create_empty = self._str2bool(self.create_empty)
        self.override_if_empty = self._str2bool(self.override_if_empty)        


dispatch(utwritelookup, sys.argv, sys.stdin, sys.stdout, __name__)
