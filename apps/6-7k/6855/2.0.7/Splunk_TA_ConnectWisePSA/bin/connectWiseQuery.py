#!/Applications/Splunk/bin/python
# Modular input for ConnectWise Manage
# Written by Paul Stout @ bitsIO <pstout@bitsioinc.com>
#
# Remember kids, don't drink and rm - rf.

import datetime
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunk.clilib import cli_common as cli
from splunklib.binding import *
from splunklib.client import *
from splunklib.modularinput import *

from cwpsa import CWManage

logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

class CWManageModInput(Script):
    def get_scheme(self):
        scheme = Scheme("ConnectWise Manage")
        scheme.description = "Streams changes to ConnectWise PSA objects."

        endpoint_argument = Argument("endpoint")
        endpoint_argument.data_type = Argument.data_type_string
        endpoint_argument.description = "ConnectWise Manage endpoint to query"
        endpoint_argument.required_on_create = True
        endpoint_argument.validation = "object_type/object"
        scheme.use_external_validation = True
        scheme.add_argument(endpoint_argument)

        collection_argument = Argument("collection")
        collection_argument.data_type = Argument.data_type_string
        collection_argument.description = "Splunk collection for the ConnectWise PSA object"
        collection_argument.required_on_create = True
        collection_argument.validation = "collection_name"
        scheme.use_external_validation = True
        scheme.add_argument(collection_argument)

        return scheme

    def validate_input(self, validation_definition):
        print(validation_definition)
        endpoint = validation_definition.parameters['endpoint']
        endpoint_match = re.match( r'[a-zA-Z0-9]+\/[a-zA-Z0-9]+', endpoint)

        if not endpoint_match:
            raise ValueError("Endpoint must follow the object_type/object pattern. [%s] provided." % endpoint)

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            utc_now = datetime.datetime.utcnow()
            newstyle_checkpoint = utc_now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            cwm_conf = cli.getConfStanza('connectwise', 'general');

            company_id = cwm_conf.get('company')
            client_id = cwm_conf.get('clientId')
            public_key = cwm_conf.get('publicKey')
            api_version = cwm_conf.get('version')
            base_uri = cwm_conf.get('url')
            release = cwm_conf.get('release')
            active_pagesize = cwm_conf.get('active_pagesize')

            process_deleted = int(input_item['process_deleted']) if 'process_deleted' in input_item else 1

            endpoint = input_item['endpoint']
            session_key = inputs.metadata['session_key']

            splunk_client = Service(token=session_key)
            storage_passwords = splunk_client.storage_passwords

            checkpoint_collection = splunk_client.kvstore['connectwise_checkpoints']

            checkpoint_key = input_item['endpoint'].replace('/','_')

            offset = False
            lastId = 0
            deleted_ids = []

            try:
                checkpoint_result = checkpoint_collection.data.query_by_id(checkpoint_key)

                if checkpoint_result:
                    if 'checkpoint' in checkpoint_result:
                        offset = checkpoint_result['checkpoint']

                    if 'lastId' in checkpoint_result:
                        lastId = checkpoint_result['lastId']

            except HTTPError as e:
                # Now that we've moved to the KVstore, if the storage engine is still initializing when this runs, the
                # There is no checkpoint and we will re-index the entire damn thing. Let's press pause if that happens, or
                # if for any reason the KVstore is unavailable.

                if e.status == 503:
                    logging.warning('connectWiseQuery: input="%s" status=delayed message="Waiting for KVstore evailability."' % input_name)
                    return

                pass

            credential_name = "connectWiseQuery:%s:" % public_key
            credential = False

            for storage_password in storage_passwords.list():
                if storage_password.name == credential_name:
                    credential = storage_password
                    break

            private_key = credential['clear_password']

            manage_api = CWManage(company_id, client_id, base_uri, release, api_version, endpoint, public_key, private_key)

            try:
                manage_api.query(offset=offset)
            except:
                logging.error("HTTP error from manage endpoint='%s'" % manage_api.uri )

            input_collection = splunk_client.kvstore[input_item['collection']]

            for event in manage_api.events:
                # ConnectWise API seems to return events AT the timestamp of che checkpoint even though
                # the operator is 'greater than' until exactly 5 hours has passed. This, to me, tells
                # me we are not respecting timezones or DST. So, to get around this, we are going to
                # discard events at the exact same timestamp if they exist in cache. This may not prevent
                # all duplicates but should prevent them after the cache runs.

                # if 'id' in event and event['id'] == lastId and 'lastUpdated' in event:
                #    logging.info('Discarding record=%s of input=%s as a potential duplicate.' % (event['id'], input_name))
                #    continue

                ev = Event()

                ev.stanza = input_name
                ev.data = json.dumps(event)

                ew.write_event(ev)

            cap_id = max(lastId, manage_api.lastId)

            skipped_ids = []

            if process_deleted:
                active_endpoint = "%s?pageSize=%s&fields=id" % (input_item['endpoint'], active_pagesize)
                active_api = CWManage(company_id, client_id, base_uri, release, api_version, active_endpoint, public_key, private_key)

                try:
                    active_api.query(active_api.base_uri)
                except Exception as e:
                    logging.error("HTTP error from manage endpoint='%s'" % active_api.uri )
                    logging.error(e.reason)
                active_ids = []

                for event in active_api.events:
                    active_ids.append(event['id'])

                deactivated_ids = 0

                if len(active_ids) > 0:
                    # This solves for the condition where if the latest records are deleted and
                    # no new ids are added, we have no way of determining if it is active by
                    # querying all active ids.

                    active_ids.append(cap_id + 1)

                    last_id = 1

                    found_ids = 0

                    for record in active_ids:
                        if record - last_id > 1:
                            for skipped_id in range(last_id, record):
                                if not skipped_id in active_ids:
                                    skipped_ids.append(skipped_id)

                        last_id = record

                    iterate_ids = []

                    batch_size = 1000

                    for i in range(0,len(skipped_ids), 1000):
                        iterate_ids.append(skipped_ids[i:i+1000])

                    for delete_chunk in iterate_ids:
                        delete_objects = []

                        for record in delete_chunk:
                            delete_objects.append({"_key": str(record)})

                        if delete_objects:
                            input_query = {
                                "active": True,
                                "$or": delete_objects
                            }

                            try:
                                active_deleted_objects = input_collection.data.query(query=input_query)
                            except HTTPError as e:
                                logging.error("HTTP error querying KVstore for input=%s" % input_name)

                            if active_deleted_objects:
                                found_ids = found_ids + len(active_deleted_objects)
                                for i, record in enumerate(active_deleted_objects):
                                    active_deleted_objects[i]['active'] = False
                                    active_deleted_objects[i].pop('_user', None)
                                    logging.info('Marking _key=%s as inactive for input=%s' % (active_deleted_objects[i]['_key'], input_name))

                                    try:
                                        input_collection.data.batch_save(active_deleted_objects[i])
                                    except HTTPError as e:
                                        logging.error("HTTP error saving to KVstore for input=%s key=%s" % (input_name, active_deleted_objects[i]['_key']))

                                    deactivated_ids = deactivated_ids + 1

                logging.info('input=%s action=deactivate psa_records=%s kvstore_records=%s deactivated_records=%s' % (
                    input_name,
                    len(skipped_ids),
                    found_ids,
                    deactivated_ids
                ))

            if manage_api.checkpoint:
                deleted_ids.sort()

                checkpoint_data = {
                    "_key": checkpoint_key,
                    "checkpoint": newstyle_checkpoint,
                    "lastId": cap_id
                }

                checkpoint_collection.data.batch_save(checkpoint_data)

if __name__=='__main__':
    sys.exit(CWManageModInput().run(sys.argv))
