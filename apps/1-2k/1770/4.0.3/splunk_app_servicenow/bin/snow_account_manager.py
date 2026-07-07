__author__ = 'strong'

import httplib
import urllib
import base64
import util as u
import splunklib.client as client
import splunklib.binding as binding
import splunk.admin as admin
from urlparse import urlparse

logger = u.getLogger()

SETUP_ACCOUNT_URL = "service_now_setup/snow_account"
TABLE_NAME = "cmn_department"

class SnowAccount(object):
    def __init__(self, snow_url, release, username, password, name='snow_account'):
        self.name = name
        self.snow_url = snow_url
        self.release = release and release.strip() or ''
        self.username = username and username.strip() or ''
        self.password = password and password.strip() or ''


class SnowAccountManager(object):
    def __init__(self, service=None):
        self._service = service

    def update(self, name="snow_account", snow_url=None, release="automatic", username=None, password=None):
        response, data = self.validate_snow_account(snow_url,release,username,password)
        if response.status not in (200, 201):
            raise admin.InternalException("Can not authenticate the ServiceNow account you provided.")
        account = self.get_by_name(name)
        props = {"url":snow_url, "release":release, "username":username, "password":password}
        account.update(**{"body":binding._encode(**props),"app":"Splunk_TA_snow","owner":self._service.namespace.get('owner')})
        return self.get_by_name(name)

    def validate_snow_account(self,snow_url, release, username, password):
        auth = base64.b64encode("%s:%s" % (username, password))
        headers = {"Accept": "application/json", "Authorization": "Basic " + auth}
        result = urlparse(snow_url)
        connection = httplib.HTTPSConnection(result.hostname,result.port)
        connection.request(method="GET", url="/incident.do?JSONv2&sysparm_query=&sys_updated_on>=2000-01-01+00:00:00&sysparm_record_count=1", headers=headers)
        response = connection.getresponse()
        data = response.read()
        return response, data

    def add_or_update(self, name='snow_account', snow_url=None, release="automatic", username=None, password=None):
        return self.update(name,snow_url,release,username,password)

    def get_by_name(self, name):
        snow_account_collection = client.Collection(self._service,SETUP_ACCOUNT_URL)
        accounts = snow_account_collection.list()
        for account in accounts:
            if account.name == name:
                return account

        return None

    def list(self):
        # TODO IMPORTANT, for current status, Service Now TA only support one account
        # edit this when TA support multiple accounts
        return [self.get_by_name("snow_account")]

    def delete(self, name="snow_account"):
        account = self.get_by_name(name)
        props = {"url":" ", "release":" ", "username":" ", "password":" "}
        return account.update(**{"body":binding._encode(**props),"app":"Splunk_TA_snow","owner":self._service.namespace.get('owner')})