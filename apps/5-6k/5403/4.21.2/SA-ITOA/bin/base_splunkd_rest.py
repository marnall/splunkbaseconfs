# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
# This is a copy: please import etc/apps/SA-UserAccess/lib/base_splunkd_rest.py instead

import json
import splunk.rest


class BaseSplunkdRest(splunk.rest.BaseRestHandler):
    """
    Base class for all of ITSI's splunkd endpoints
    """
    def render_json(self, response_data):
        '''
        given data, convert it to a JSON which is consumable by a web client
        '''
        response = json.dumps(response_data).replace("</", "<\\/")

        # Pad with 256 bytes of whitespace for IE security issue. See SPL-34355
        return ' ' * 256 + '\n' + response
