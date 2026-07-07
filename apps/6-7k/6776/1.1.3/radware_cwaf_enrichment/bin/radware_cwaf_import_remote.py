#!/usr/bin/env python
# Import Radware Cloud WAF Objects from the API

from __future__ import print_function

import sys

from future import standard_library

from radware_cwaf_common_command import RadwareCommonCommand

standard_library.install_aliases()

from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class RadwareCWAFImportRemoteCommand(RadwareCommonCommand):
    """ %(synopsis)

    ##Syntax

    | radwarecwafimportremote tenant_id="tenant_id" object_type="applications

    ##Description

    Import remote objects from the Radware Cloud WAF API. Optionally filter by tenant_id (default is all tenants).

    """

    def __init__(self):
        super().__init__()

    def generate(self):
        required_permission = 'run_radware_cwaf_enrichment_import_remote'
        super().init_command(required_permission)

        # Sanitize input
        if self.tenant_id:
            self.app_logger.debug('Tenant ID Context: %s' % self.tenant_id)
        else:
            self.tenant_id = None

        object_store = self.get_object_store()

        object_dict = self.get_radware_objects()

        all_objects = []
        for tenant_id in object_dict:
            batch_save_items = []
            for list_item in object_dict[tenant_id]:
                list_item['tenantId'] = tenant_id
                list_item["_key"] = "%s_%s" % (
                    list_item['tenantId'], list_item['id'])
                batch_save_items += [list_item]
                all_objects += [list_item]
            object_store.data.batch_save(*batch_save_items)
            yield {'message': f"Imported {str(len(batch_save_items))} {self.object_type} from tenant " + tenant_id}

        # Reconcile (Delete) any objects that are no longer in the API
        if self.tenant_id and self.tenant_id != "*":
            kv_store_objects = object_store.data.query(query={"tenantId": self.tenant_id})
        else:
            kv_store_objects = object_store.data.query()
        for kv_store_object in kv_store_objects:
            if not next((item for item in all_objects if item["_key"] == kv_store_object['_key']), None):
                object_store.data.delete_by_id(kv_store_object['_key'])
                self.app_logger.debug("Deleted Object %s from KV Store" % kv_store_object['_key'])
                yield {'message': "Deleted Object %s from KV Store" % kv_store_object['_key']}
            else:
                self.app_logger.debug("Keeping Object %s in KV Store" % kv_store_object['_key'])
                yield {'message': "Keeping Object %s from KV Store" % kv_store_object['_key']}


dispatch(RadwareCWAFImportRemoteCommand, sys.argv,
         sys.stdin, sys.stdout, __name__)
