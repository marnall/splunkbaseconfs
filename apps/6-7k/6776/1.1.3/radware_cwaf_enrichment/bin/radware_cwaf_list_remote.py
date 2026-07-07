#!/usr/bin/env python

# List Radware Cloud WAF Objects from the API

from __future__ import print_function

import sys

from future import standard_library

from radware_cwaf_common_command import RadwareCommonCommand
from splunklib.searchcommands import Configuration, dispatch

standard_library.install_aliases()


@Configuration()
class RadwareCWAFListRemoteCommand(RadwareCommonCommand):
    """ %(synopsis)

    ##Syntax

    | radwarecwaflistremote tenant_id="tenant_id"

    ##Description

    List remote apps from the Radware Cloud WAF API. Optionally filter by tenant_id (default is all tenants).

    """

    def __init__(self):
        super().__init__()

    def generate(self):
        required_permission = 'run_radware_cwaf_enrichment_list_remote'
        super().init_command(required_permission)

        # Sanitize input
        if self.tenant_id:
            self.app_logger.debug('Tenant ID Context: %s' % self.tenant_id)
        else:
            self.tenant_id = None

        object_dict = self.get_radware_objects()

        for tenant_id in object_dict:
            for list_item in object_dict[tenant_id]:
                list_item['tenantId'] = tenant_id
                list_item["_key"] = "%s_%s" % (
                    list_item['tenantId'], list_item['id'])
                yield list_item


dispatch(RadwareCWAFListRemoteCommand, sys.argv,
         sys.stdin, sys.stdout, __name__)
