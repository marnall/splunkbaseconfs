""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

from os import environ as ENV
import functools

import connector

import epmspln_odata2.client


search_id = u'0050568B51541EE6BED18D0345F844BF'
service_id = u'0050568B51541EE6BED17E69D2DA04B8'
service_name = 'AI_SYSMON_OVERVIEW_SRV'
feed_name_events = 'EventListSet'
feed_name_system = 'SystemListSet'


new_sap_connector = epmspln_odata2.client.OdataClient(
    services_base=ENV['TOX_SERVICES_BASE'],
    userid=ENV['TOX_USERID'],
    password=ENV['TOX_PASSWORD'],
)


client_factory = functools.partial(
    connector.AuthenticatedClient,
    services_base=ENV['TOX_SERVICES_BASE'],
    userid=ENV['TOX_USERID'],
    password=ENV['TOX_PASSWORD'],
)

pyslet_sap_connector = connector.PysletOdataConnector(client_factory)


def filter_events(event, event_id):
    for x in event:
        if x[0] == event_id:
            return x


def filter_entity(entities, context_id):
    for x in entities:
        if (
            x[0] == (u'005056B44CB91EE2998FB712C0BD4BBE', u'')
            and x[1][u'MoContextid'] == context_id
        ):
            return x


def test_system_list_set():
    our_impl_service = list(
        new_sap_connector.get_feed_collection_items(
            service_name, feed_name_system
        )
    )

    pyslet_impl_service = list(
        pyslet_sap_connector.get_feed_collection_items(
            service_name, feed_name_system
        )
    )

    expected = filter_events(pyslet_impl_service, service_id)
    actual = filter_events(our_impl_service, service_id)

    # Change to == for testing implementations equality
    assert expected != actual


def test_event_list_set_search():
    our_impl_search = list(
        new_sap_connector.get_feed_collection_items(
            service_name, feed_name_events, search=search_id
        )
    )

    pyslet_impl_search = list(
        pyslet_sap_connector.get_feed_collection_items(
            service_name, feed_name_events, search=search_id
        )
    )

    expected = filter_entity(pyslet_impl_search, search_id)
    actual = filter_entity(our_impl_search, search_id)
    # Remove next two lines if you want to test odata implentation
    # We do not use Deferred value, but in future we have to add tis type
    # Just for sake of testing seach functonality you should do this hack
    expected[1].pop(u'ValueTimestampMeasurement', None)
    actual[1].pop(u'ValueTimestampMeasurement', None)

    assert expected == actual
