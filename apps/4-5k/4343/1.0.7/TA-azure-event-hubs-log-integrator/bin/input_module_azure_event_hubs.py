
# encoding = utf-8

import os
import sys
import string
import json

from fastavro import writer, reader, parse_schema
from azure.storage.blob import BlockBlobService

def validate_input(helper, definition):
    storage_account_name = definition.parameters.get('storage_account_name', None)
    storage_account_key = definition.parameters.get('storage_account_key', None)
    container_name = definition.parameters.get('container_name', None)


def collect_events(helper, ew):
    opt_storage_account_name = helper.get_arg('storage_account_name')
    opt_Accesskey = helper.get_arg('storage_account_key')
    opt_container = helper.get_arg('container_name')

    block_blob_service = BlockBlobService(account_name=opt_storage_account_name, account_key=opt_Accesskey)
    generator = block_blob_service.list_blobs(opt_container)
    for blob in generator:
        #content_length == 508 bytes is an empty file, so only process content_length > 508 (skip empty files)
        if blob.properties.content_length > 508:
            cleanName = string.replace(blob.name, '/', '_')
            cleanName = os.path.join(os.path.dirname(__file__), cleanName)
            block_blob_service.get_blob_to_path(opt_container, blob.name, cleanName)

            try:
                with open(cleanName, 'rb') as foa:
                    for record in reader(foa):
                        parsed_json = json.loads(record["Body"])

                        if 'records' in parsed_json:
                            records = parsed_json['records']
                            
                            for rec in records:
                                datai = json.dumps(rec)
    
                                event = helper.new_event(datai, host=None, source=None, sourcetype='aeh', done=True, unbroken=True)
    
                                try:
                                    ew.write_event(event)
                                except Exception as e:
                                    raise e
                        else:
                            data = json.dumps(parsed_json)
                            
                            event = helper.new_event(data, host=None, source=None, sourcetype='aeh', done=True, unbroken=True)
                            try:
                                ew.write_event(event)
                            except Exception as e:
                                raise e
            except:
                pass
            
            #Delete temporary avro files
            os.remove(cleanName)

        #Once it's done delete Azure blobs
        block_blob_service.delete_blob(opt_container, blob.name)