#!/usr/bin/env python
# Import Radware Cloud WAF Objects from the API

from __future__ import print_function

import sys

from future import standard_library

from radware_cwaf_common_command import RadwareCommonCommand

standard_library.install_aliases()

from splunklib.searchcommands import dispatch, Configuration


@Configuration()
class RadwareCWAFDeleteLocalCommand(RadwareCommonCommand):
    """ %(synopsis)

    ##Syntax

    | radwarecwafdeletelocal tenant_id="tenant_id" object_type="applications

    ##Description

    Delete all objects in the local KV store.

    """

    def __init__(self):
        super().__init__()

    def generate(self):
        required_permission = 'run_radware_cwaf_enrichment_delete_local'
        super().init_command(required_permission)

        object_store = self.get_object_store()

        if self.tenant_id and self.tenant_id != "*":
            kv_store_objects = object_store.data.query(query={"tenantId": self.tenant_id})
        else:
            kv_store_objects = object_store.data.query()

        if len(kv_store_objects) > 0:
            for kv_store_object in kv_store_objects:
                object_store.data.delete_by_id(kv_store_object['_key'])
        yield {'message': "Deleted %s object(s) from KV Store" % len(kv_store_objects)}


dispatch(RadwareCWAFDeleteLocalCommand, sys.argv,
         sys.stdin, sys.stdout, __name__)
