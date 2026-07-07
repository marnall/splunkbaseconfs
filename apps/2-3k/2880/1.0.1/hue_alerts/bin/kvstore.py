import json
import urllib
import urllib2

from util import merge


def splunkd_auth(session_key):
    return {'Authorization': 'Splunk %s' % session_key}


class KVStoreCollection:
    def __init__(self, collection, server_uri, session_key, app, owner='nobody'):
        self.collection = urllib.quote(collection)
        self.server_uri = server_uri
        self.session_key = session_key
        self.app = urllib.quote(app)
        self.owner = urllib.quote(owner)

    def uri(self, name=None, query=None):
        qs = dict(output_mode='json')
        if query is not None:
            qs.update(query)
        if name is not None:
            return '%s/servicesNS/%s/%s/storage/collections/data/%s/%s?%s' % (
                self.server_uri, self.owner, self.app, self.collection, urllib.quote(name), urllib.urlencode(qs))
        else:
            return '%s/servicesNS/%s/%s/storage/collections/data/%s?%s' % (
                self.server_uri, self.owner, self.app, self.collection, urllib.urlencode(qs))

    def build_req(self, method, data=None, name=None, query=None):
        h = splunkd_auth(self.session_key)
        if h is not None:
            h['Content-Type'] = 'application/json'
        req = urllib2.Request(self.uri(name), json.dumps(data), h)
        req.get_method = lambda: method
        return req

    def load(self, count=0):
        req = self.build_req('GET', query=dict(count=count))
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def get(self, key):
        req = self.build_req('GET', name=key)
        try:
            res = urllib2.urlopen(req)
            return json.loads(res.read())
        except urllib2.HTTPError, e:
            if e.code == 404:
                return None
            else:
                raise e

    def update(self, key, data):
        req = self.build_req('PUT', name=key, data=data)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def create(self, key, data):
        req = self.build_req('POST', data=(merge({"_key": key}, data)))
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def delete(self, key):
        req = self.build_req('DELETE', name=key)
        urllib2.urlopen(req)
