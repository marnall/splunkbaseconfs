"""
Custom command used to update Google Analytics View ID list
"""

import os
from apiclient.discovery import build # pylint: disable=import-error
from oauth2client.file import Storage # pylint: disable=import-error
import splunk.rest # pylint: disable=import-error
import splunk.Intersplunk # pylint: disable=import-error
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path # pylint: disable=import-error


def get_view_ids():
    """ Generates a dictionary of view IDs to view names """
    key_location = make_splunkhome_path(['etc', 'apps', 'TA-google_analytics_reporting', 'bin',
                                         'google_analytics_input_google_analytics_creds'])
    storage = Storage(key_location)
    credentials = storage.get()

    # Build the service object.
    analytics = build('analytics', 'v3', credentials=credentials)
    account_summaries = analytics.management().accountSummaries().list().execute()
    views = {}
    for account in account_summaries['items']:
        for web_property in account['webProperties']:
            for view in web_property['profiles']:
                views[view['id']] = view['name']
    return views


def update_manager_xml(views):
    """ Given the view dict from get_view_ids(), updates manager XML """
    xml_location = make_splunkhome_path(['etc', 'apps', 'TA-google_analytics_reporting', 'local',
                                         'data', 'ui', 'manager'])
    if not os.path.isdir(xml_location):
        os.makedirs(xml_location)
    xml_file = os.path.join(xml_location, 'analytics_report_manager.xml')
    with open(xml_file, 'w') as f:
        f.write(header)
        for view_id, view_name in views.iteritems():
            # indenting
            f.write('                        ')
            f.write('<opt value="%s" label="%s"/>\n' % (view_id, view_name))
        f.write(footer)


header = '''<endpoint name="data/inputs/analytics_report">
    <header>Google Analytics Report</header>
    <breadcrumb>
        <parent hidecurrent="False">datainputstats</parent>
        <name>Google Analytics Report</name>
    </breadcrumb>
    <elements>
        <element name="sourceFields" type="fieldset">
            <view name="list"/>
            <view name="edit"/>
            <view name="create"/>
            <elements>
                <element name="name" label="Google Analytics Input Name">
                    <view name="list"/>
                    <view name="create"/>
                    <key name="exampleText">Name of this Google Analytics Input</key>
                </element>
                <element name="view_id" type="select" label="View ID">
                    <view name="edit"/>
                    <view name="create"/>

                    <key name="exampleText">View ID
                    </key>
                    <options>
'''

footer = '''                    </options>
                </element>
                <element name="metrics" type="textfield" label="Metrics (comma-separated list)">
                    <view name="edit"/>
                    <view name="create"/>
                    <key name="exampleText">e.g. ga:sessions, ga:users</key>
                </element>
                <element name="dimensions" type="textfield"
                         label="Dimensions (optional, comma-separated list)">
                    <view name="edit"/>
                    <view name="create"/>
                    <key name="exampleText">e.g. ga:screenResolution</key>
                </element>
                <element name="backfill" type="textfield"
                         label="Backfill (days). Use 0 for no backfill">
                    <view name="edit"/>
                    <view name="create"/>
                </element>
            </elements>
        </element>

        <element name="spl-ctrl_EnableAdvanced" type="checkbox" label="More settings"
                 class="spl-mgr-advanced-switch">
            <view name="edit"/>
            <view name="create"/>
            <onChange>
                <key name="_action">showonly</key>
                <key name="0">NONE</key>
                <key name="1">ALL</key>
                <group_set>
                    <group name="advanced"/>
                </group_set>
            </onChange>
        </element>
        <element name="advanced" type="fieldset" class="spl-mgr-advanced-options">
            <view name="edit"/>
            <view name="create"/>
            <elements>
                <element name="hostFields" type="fieldset">
                    <key name="legend">Host</key>
                    <view name="list"/>
                    <view name="edit"/>
                    <view name="create"/>
                    <elements>
                        <element name="host" type="textfield" label="Host field value">
                            <view name="edit"/>
                            <view name="create"/>
                        </element>
                    </elements>
                </element>
                <element name="indexField" type="fieldset">
                    <key name="legend">Index</key>
                    <key name="helpText">Set the destination index for this source.</key>
                    <view name="list"/>
                    <view name="edit"/>
                    <view name="create"/>
                    <elements>
                        <element name="index" type="select" label="Index">
                            <view name="list"/>
                            <view name="edit"/>
                            <view name="create"/>
                            <key name="dynamicOptions" type="dict">
                                <key name="keyName">title</key>
                                <key name="keyValue">title</key>
                                <key name="splunkSource">/data/indexes</key>
                                <key name="splunkSourceParams" type="dict">
                                    <key name="search">'isInternal=false disabled=false'</key>
                                    <key name="count">-1</key>
                                </key>
                            </key>
                        </element>
                    </elements>
                </element>
            </elements>
        </element>
        <element name="eai:acl.app" label="App">
            <view name="list"/>
            <key name="processValueList">entity['eai:acl']['app'] or ""</key>
        </element>

    </elements>
</endpoint>'''


def main():
    """Main function"""
    dummyresults, settings = splunk.Intersplunk.getOrganizedResults()[1:]
    session_key = settings.get("sessionKey")
    output_events = []

    views = get_view_ids()
    update_manager_xml(views)
    for view_id, view_name in views.iteritems():
        output_events.append({'view_id': view_id, 'view_name': view_name})

    # Refresh manager endpoint
    splunk.rest.simpleRequest(
        '/services/data/ui/manager/_reload', method='GET', sessionKey=session_key)
    splunk.Intersplunk.outputResults(output_events)


if __name__ == "__main__":
    main()
