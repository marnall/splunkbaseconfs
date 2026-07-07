#!/usr/bin/env python
from __future__ import absolute_import
import os
import sys
import datetime
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import *
from splunklib import six
from bhe_client import *
from kv_last_stream import *
from kv_audit_last_stream import *
from event_functions import *
from principal_functions import *

class Main(Script):
    def get_scheme(self):
        # Rerquired for modular inputs. The data input 'description' is just a dummy. We store API creds in secrets.

        scheme = Scheme("BloodHound Enterprise")

        scheme.description = "Connect to BloodHound Enterprise instance."
        scheme.use_external_validation = True
        scheme.use_single_instance = True

        description_argument = Argument("description")
        description_argument.title = "Description"
        description_argument.data_type = Argument.data_type_string
        description_argument.description = "Data input description."
        description_argument.required_on_create = True

        scheme.add_argument(description_argument)

        return scheme

    def validate_input(self, validation_definition):
        # Required for modular inputs. We validata the API creds when entered in setup page (we plan to do that).
        pass

    def stream_events(self, inputs, ew):
        # Rerquired for modular inputs. This function handles all the action
        
        logging.info("BHE Streaming events")

        for input_name, input_item in six.iteritems(inputs.inputs):

            # Ensure index exist
            index_exist = False
            indexes = self.service.indexes
            for index in indexes.list():
                index_name = index.path
                if index_name.endswith("/bhe-splunk-app"):
                    logging.info("BHE Index exist")
                    index_exist = True
            if (not index_exist):
                logging.info("BHE Creating index")
                self.service.indexes.create("bhe-splunk-app")

            # Get API creds
            self.service.namespace["app"] = input_item["__app"]
            storage_passwords = self.service.storage_passwords

            creds_found = False
            for storage_password in storage_passwords.list(search="bhe-splunk-app"):
                try:
                    bhe_domain = storage_password.realm
                    token_id = storage_password.username
                    token_key = storage_password.clear_password
                    creds_found = True
                except AttributeError:
                    pass

            # Exit if no creds
            if creds_found:
                logging.info("BHE Credentials found")
            else:
                logging.info("BHE No BHE creds")
                continue

            # Connection to BHE domain
            credentials = Credentials(token_id, token_key)
            client = BHEClient(scheme='https', host=bhe_domain, port=443, credentials=credentials)

            # Check if BHE domain is reachable and creds are workings
            try:
                status_code = client.get_api_version().status_code
                response = client.get_api_version()
                logging.info(client.get_api_version().url)
            except:
                logging.info("BHE Cannot reach domain: %s" % bhe_domain)
                raise ValueError("Cannot reach domain: %s" % bhe_domain)
            else:
                if status_code == 200:
                    logging.info("BHE API creds validated")
                else:
                    logging.info("BHE Cannot log in using API keys. Status code: %s" % status_code)
                    raise ValueError("Cannot log in using API keys. Status code: %s" % status_code)

            # Get last data stream timestamp and update the value in the kv store
            no_last_data_stream = False
            timestamp_now = datetime.datetime.now(datetime.timezone.utc).strftime(tformat)[:-3] + 'Z'
            last_data_stream = get_last_data_stream(self.service)

            if not last_data_stream:
                no_last_data_stream = True
                last_data_stream = "2020-01-01T00:00:00.000Z"

            logging.info("BHE Last data stream %s" % last_data_stream)

            # Get last audit data stream timestamp and update the value in the kv store
            no_audit_last_data_stream = False
            timestamp_now = datetime.datetime.now(datetime.timezone.utc).strftime(tformat)[:-3] + 'Z'
            last_audit_data_stream = get_audit_last_data_stream(self.service)

            if not last_audit_data_stream:
                no_audit_last_data_stream = True
                last_audit_data_stream = "2020-01-01T00:00:00.000Z"

            logging.info("BHE Last Audit data stream %s" % last_audit_data_stream)


            # Get TimeStamp for Finding/Tier Zero Principal Lists
            finding_list_query_ts = datetime.datetime.now().strftime(tformat)[:-3] + 'Z'

            # # Get available domains
            domains = client.get_domains()
            logging.info("BHE Number of domains %s" % len(domains))

            for domain in domains:
                if domain['collected']:
                    # Get paths for domain
                    attack_paths = client.get_paths(domain)
                    logging.info(("BHE Processing %s attack paths for domain %s" % (len(attack_paths), domain['name'])))

                    for attack_path in attack_paths:
                        logging.info("BHE Processing attack path %s" % attack_path.id)
                        retry_limit = 0                       
                        while retry_limit < 3:
                            try:
                                #Create & Write finding_export events
                                path_details = client.get_path_principals(attack_path)
                                for finding in path_details.impacted_principals:
                                    spl_finding_event = create_finding_record(
                                        path_details=path_details,
                                        finding=finding,
                                        timestamp = finding_list_query_ts,
                                        stanza = input_name)
                                    ew.write_event(spl_finding_event)
                                                            
                                # Create attack path events in Splunk
                                path_events = client.get_path_timeline(
                                    path = attack_path,
                                    from_timestamp = last_data_stream,
                                    to_timestamp = timestamp_now
                                )
                                for path_event in path_events:
                                    splunk_path_event = get_splunk_attack_path_event(
                                        event_data = path_event,
                                        stanza = input_name,
                                        domain = domain
                                    )
                                    ew.write_event(splunk_path_event)
                                logging.info("BHE Processing attack path %s done" % attack_path.id)
                                break
                            except:
                                retry_limit += 1
                                logging.info("BHE Error Processing Attack Path. Retry attempt " + str(retry_limit) + " of 3")
                                time.sleep(3)
                        else:
                            logging.info("Error Processing Attack Path. Max Retries Attempted. Skipping Attack Path") 

            # Get posture data
            posture_events = client.get_posture(
                from_timestamp = last_data_stream,
                to_timestamp = timestamp_now
            )

            logging.info("BHE Processing %s events of posture data" % len(posture_events))

            # Create posture events in Splunk
            for posture_event in posture_events:
                splunk_posture_event = get_splunk_posture_event(
                    event_data = posture_event,
                    stanza = input_name,
                    domains = domains
                )
                ew.write_event(splunk_posture_event)
                        
            # Update last data stream
            if no_last_data_stream:
                insert_last_data_stream(self.service, timestamp_now)
            else:
                update_last_data_stream(self.service, timestamp_now)

            logging.info("BHE Streaming events done")      
            # Process T0 Export          
            logging.info("BHE Processing T0 Table Data")

            #Get & Write T0 Assets
            try:
                t0_objects = client.get_t0_assets()
                domains = client.get_domains()
                for t0_obj in t0_objects:
                    t0_obj = t0_objects[t0_obj]
                    t0_record = create_tier0_record(t0_obj,domains,finding_list_query_ts,input_name)
                    # Skip writing event if T0 Record is null (Object type is Meta or Base)
                    if t0_record is not None:
                        ew.write_event(t0_record)
                logging.info("BHE Processing T0 Export Data Done")
            except:
                logging.info("Error Processing T0 Export")

            logging.info("BHE Processing audit data")

            # Get Audit data
            try:

                audit_events = client.get_audit_events(
                    from_timestamp = last_audit_data_stream,
                    to_timestamp = timestamp_now
                )
             # Create Audit events in Splunk
                for audit_event in audit_events:
                    splunk_audit_event = get_splunk_audit_event(
                        event_data = audit_event,
                        stanza = input_name
                    )
                    ew.write_event(splunk_audit_event)
                        # Update last data stream
            
                if no_audit_last_data_stream:
                    insert_audit_last_data_stream(self.service, timestamp_now)
                else:
                    update_audit_last_data_stream(self.service, timestamp_now)

                logging.info("BHE Processing audit data done")
            except:
                logging.error("Unable to process Audit events. Please confirm API User is assigned Admin role to collect audit events.")
          

            logging.info("BHE Processing Environment Complete")


if __name__ == "__main__":
    # set up logging suitable for splunkd consumption
    logging.root
    logging.root.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)

    sys.exit(Main().run(sys.argv))