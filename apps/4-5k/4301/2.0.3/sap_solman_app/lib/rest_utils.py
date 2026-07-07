""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

from splunk import entity

import splunklib.client as splunk_client


def get_client(rest_handler, app_name):
    splunk_entity = entity.getEntity(
        '/server', 'settings', namespace=app_name,
        sessionKey=rest_handler.sessionKey, owner='-')
    return splunk_client.connect(
        token=rest_handler.sessionKey,
        port=splunk_entity['mgmtHostPort'],
        owner='nobody',
        app=app_name)
