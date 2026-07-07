#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import sys
import os
import json
import re
from pathlib import Path

ta_name = 'SecurityOnionSplunk'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

import splunk
import splunk.admin as admin
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, str(Path(__file__).parent))
from query_events import find_community_id_by_uid


class LookupCommunityIdHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            request = json.loads(in_string)

            if isinstance(request, list) and len(request) > 0:
                request = request[0]

            method = request.get('method', '')

            if method == 'GET':
                return self.handle_get(request)
            else:
                return self.make_error_response(f"Unsupported method: {method}", 405)

        except Exception as e:
            return self.make_error_response(str(e), 500)

    def handle_get(self, request):
        """
        Handle GET requests to lookup community_id.
        Expected query parameters:
        - uid: The UID to lookup
        - timestamp: Timestamp to narrow the search
        - timezone: Optional timezone (default: UTC)
        """
        try:
            query_params = request.get('query', [])

            uid = ''
            timestamp = ''
            timezone = 'Etc/UTC'

            for param in query_params:
                if param[0] == 'uid':
                    uid = param[1]
                elif param[0] == 'timestamp':
                    timestamp = param[1]
                elif param[0] == 'timezone':
                    timezone = param[1]

            if not uid:
                return self.make_error_response("Missing required parameter: uid", 400)

            community_id = find_community_id_by_uid(
                uid,
                timestamp if timestamp else None,
                timezone
            )

            if community_id:
                response_data = {
                    'success': True,
                    'community_id': community_id,
                    'uid': uid
                }
            else:
                response_data = {
                    'success': False,
                    'message': f"No community_id found for uid: {uid}",
                    'uid': uid
                }

            return {
                'payload': json.dumps(response_data),
                'status': 200
            }

        except Exception as e:
            return self.make_error_response(f"Failed to lookup community_id: {str(e)}", 500)

    def make_error_response(self, message, status_code):
        return {
            'payload': json.dumps({
                'success': False,
                'message': message
            }),
            'status': status_code
        }


if __name__ == '__main__':
    admin.init(LookupCommunityIdHandler, admin.CONTEXT_APP_AND_USER)