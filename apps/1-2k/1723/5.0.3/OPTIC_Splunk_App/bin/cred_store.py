'''
Copyright (C) 2013-2015 ThreatStream Inc. All Rights Reserved.
'''
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field
from splunk import AuthenticationFailed, ResourceNotFound


class TSCredStore(SplunkAppObjModel):
    resource = 'storage/passwords'

    clear_password = Field()
    encr_password = Field()
    username = Field()
    password = Field()
    realm = Field()

class TSCredStoreManager(object):

    CRED_DELIM = '@@:@@'


    def __init__(self, sessionKey=None, app=None, owner=None, realm=None):
        if sessionKey is None:
            raise AuthenticationFailed('Provide a session key.')
        self._sessionKey = sessionKey

        if app is None:
            raise Exception("Provide an application name.")
        self._app = app

        if owner is None:
            raise Exception("Provide an owner name.")
        self._owner = owner

        self._realm = '' if realm is None else realm

    def _build_cred_id(self, name):
        return TSCredStore.build_id((self._realm or '') + ':' + name + ':', self._app, self._owner)

    def _create_creds(self, username, apikey):
        return username + self.CRED_DELIM + apikey

    def _extract_creds(self, raw_creds):
        results = raw_creds.split(self.CRED_DELIM)
        return results[0], results[1]

    def get_raw_creds(self, name):
        try:
            results = TSCredStore.get(self._build_cred_id(name), self._sessionKey)
            return self._extract_creds(results.clear_password)
        except ResourceNotFound:
            return '', ''

    def get_creds(self, name):
        results = TSCredStore.get(self._build_cred_id(name), self._sessionKey)
        return results.encr_password

    def create(self, name, username, apikey):
        cred = TSCredStore(self._app, self._owner, name, sessionKey=self._sessionKey)

        if self._realm:
            cred.realm = realm
        cred.password = self._create_creds(username, apikey)

        if cred.create():
            return self.get_creds(name)
        else:
            return None

    def update(self, name, username, apikey):
        if username:
            postargs = {'password': self._create_creds(username, apikey)}
        else:
            postargs = {'password': ''}
        cred = TSCredStore.manager()._put_args(self._build_cred_id(name), postargs, sessionKey=self._sessionKey)
        return cred['encr_password']

    def save(self, name, username, apikey):
        try:
            exists = self.get_creds(name)
            return self.update(name, username, apikey)
        except ResourceNotFound:
            return self.create(name, username, apikey)
