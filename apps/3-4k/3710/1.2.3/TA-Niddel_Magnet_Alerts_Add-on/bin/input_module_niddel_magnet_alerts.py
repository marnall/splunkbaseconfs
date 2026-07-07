# encoding = utf-8

import json, sys, os
from datetime import datetime, timedelta

from magnetsdk2 import Connection
from magnetsdk2.iterator import AbstractPersistentAlertIterator, PersistenceEntry
from niddelutil import get_app_config, get_splunk_version

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


class HelperPersistentAlertIterator(AbstractPersistentAlertIterator):
    """Subclass of AbstractPersistentAlertIterator that saves the persistence state into KV store
    using the helper object."""

    def __init__(self, helper, *args, **kwargs):
        self.helper = helper
        super(HelperPersistentAlertIterator, self).__init__(*args, **kwargs)

    def _load(self):
        latest_ids = self.helper.get_check_point('%s:last_ids' % self.organization_id)

        latest_cursor = self.helper.get_check_point('%s:last_cursor' % self.organization_id)

        if latest_cursor:
            ## If 'latest_cursor' exists into KVStore it means new persistence format is already in place
            self.helper.log_info(' '.join(['checkpoint loaded: cursor=', latest_cursor, 'alert_id=', str(latest_ids)]))
            return PersistenceEntry(self.organization_id, None, latest_ids, latest_cursor)
        else:
            ## Otherwise, 'latest_batchDate' will be used for the last time then it will be converted to 
            ## new persistence format.
            latest_batchDate = self.helper.get_check_point('%s:last_batchDate' % self.organization_id)

            if not latest_batchDate:
                return None

            self.helper.log_info(' '.join(['checkpoint loaded: cursor=', latest_batchDate, 'alert_id=', str(latest_ids)]))
            return PersistenceEntry(self.organization_id, latest_batchDate, latest_ids, None)
            

    def _save(self):
        self.helper.save_check_point('%s:last_cursor' % self.organization_id, self.persistence_entry.latest_api_cursor)
        self.helper.save_check_point('%s:last_ids' % self.organization_id, self.persistence_entry.latest_alert_ids[-1])
        self.helper.log_info(' '.join(['checkpoint saved: cursor=', self.persistence_entry.latest_api_cursor, \
                                        'alert_id=',self.persistence_entry.latest_alert_ids[-1]]))


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # organization_id = definition.parameters.get('organization_id', None)
    pass


def collect_events(helper, ew):
    helper.log_info('collect events started')

    # get API key and open connection
    api_key = helper.get_arg('api_key')
    if not api_key:
        raise ValueError('cannot download data without an API key')

    appcfg = get_app_config()
    splversion = get_splunk_version()
    _user_agent = "Splunk Add-on/TA/v%s-build_%s; %s" % (appcfg['app_version'], appcfg['app_build'], str(splversion))
    conn = Connection(api_key=api_key, user_agent=_user_agent)

    # set connection proxy if necessary
    proxy = helper.get_proxy()
    if proxy and proxy.get('proxy_url'):
        proxy = {
            'proxy': proxy.get('proxy_url', None),
            'proxy_proto': proxy.get('proxy_type', 'https'),
            'proxy_port': proxy.get('proxy_port', None),
            'proxy_user': proxy.get('proxy_username', None),
            'proxy_pass': proxy.get('proxy_password', None),
        }
        helper.log_info('using proxy {0}://{1}:{2} with username {3}'.format(proxy['proxy_proto'], 
                                        proxy['proxy'], proxy['proxy_port'], proxy['proxy_user']))
        conn.set_proxy(**proxy)

    # get organization ID to process
    organizations = helper.get_arg('organization_ids')
    if organizations:
        organizations = {x.strip() for x in organizations.split(',')}
    else:
        organizations = {x['id'] for x in conn.iter_organizations()}

    for organization_id in organizations:
        helper.log_info('processing organization ' + str(organization_id))

        iter_alerts = HelperPersistentAlertIterator(helper, conn, organization_id)
        for alert in iter_alerts:
            try:
                alert['organization'] = organization_id
                utc_dt = datetime.strptime(alert['logDate'] + 'T' + alert['aggLast'], '%Y-%m-%dT%H:%M:%SZ')
                utc_dt = utc_dt + timedelta(milliseconds=1) # Padding 1 ms to respect the time requisite as a 3 digits milliseconds input
                event = helper.new_event(time=(utc_dt - datetime(1970, 1, 1)).total_seconds(),
                                         source=helper.get_input_type(),
                                         index=helper.get_output_index(),
                                         sourcetype=helper.get_sourcetype(),
                                         data=json.dumps(alert))
                ew.write_event(event)
                helper.log_info('wrote alert ' + str(alert['id']))
                helper.log_info('saving check point')
                iter_alerts.save()
            except Exception as e:
                helper.log_error('error writing alert ' + str(alert['id']))
                raise e
        helper.log_info('collect events finished for organization ' + str(organization_id))

    helper.log_info('collect events finished for the stanza')
