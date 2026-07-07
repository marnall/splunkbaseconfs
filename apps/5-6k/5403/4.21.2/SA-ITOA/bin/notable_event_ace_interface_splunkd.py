# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import operator

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.setup_logging import logger
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.event_management.ace_interface import AceInterfaceProvider

logger.debug("Initialized Ace Interface log")


class NotableEventAceInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for ACE interface endpoints
    """
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(NotableEventAceInterfaceSplunkd, self).__init__()

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        session_key = args.get('session', {}).get('authtoken', None)
        current_user = args.get('session', {}).get('user', None)
        rest_method = args.get('method', None)
        if not session_key or not current_user or not rest_method or 'rest_path' not in args or args['rest_path'] is None:
            raise Exception('Invalid parameters received from splunkd REST request')

        path_parts = args['rest_path'].strip().strip('/').split('/')
        interface_provider = AceInterfaceProvider(session_key, current_user, rest_method)
        if path_parts[-1] == 'seed_search_id':
            if rest_method != 'POST':
                raise Exception('Invalid REST method and path')
            data = NotableEventAceInterfaceSplunkd.extract_data_payload(args)['data']
            interface_provider.handle_save_seed_groups_from_search_id(data.get('sid', None))
