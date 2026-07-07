import json
import urllib2

import splunk.rest

import hue


class BaseHandler(splunk.rest.BaseRestHandler):
    def __init__(self, *args, **kwargs):
        splunk.rest.BaseRestHandler.__init__(self, *args, **kwargs)
        self._kv = None

    def kv(self):
        if self._kv is None:
            self._kv = hue.hue_state_kv(splunk.rest.makeSplunkdUri().rstrip('/'), self.sessionKey)
        return self._kv

    def respond_json(self, data, status=200):
        self.response.setStatus(status)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))


class HueRegistrationHandler(BaseHandler):
    def handle_GET(self):
        try:
            bridge = self.kv().get("bridge")

            if bridge is None:
                self.respond_json(dict(status="not_configured"))
            else:
                if hue.test_connection(bridge):
                    if bridge.get('dirty'):
                        self.kv().update('bridge', bridge)
                    self.respond_json(dict(status="connected", ip=bridge.get('ip'), id=bridge.get('id')))
                else:
                    self.respond_json(dict(status="disconnected", id=bridge.get('id')))
        except urllib2.HTTPError, e:
            self.respond_json(dict(error="Splunkd Error: " + str(e), response=e.read()), status=500)
        except Exception, e:
            # import traceback
            # self.respond_json(dict(error="Error: " + str(e), stack=traceback.format_exc()), status=500)
            self.respond_json(dict(error="Error: " + str(e)), status=500)

    def handle_POST(self):
        try:
            if 'action' in self.args:
                action = self.args['action']
                if action == 'discover':
                    self.handle_discover()
                    return
                if action == 'register':
                    self.handle_register()
                    return
                if action == 'reset':
                    self.handle_reset()
                    return

            self.respond_json(dict(error="Invalid action"), status=400)
        except urllib2.HTTPError, e:
            self.respond_json(dict(error="Splunkd Error: " + str(e), response=e.read()), status=500)
        except Exception, e:
            # import traceback
            # self.respond_json(dict(error="Error: " + str(e), stack=traceback.format_exc()), status=500)
            self.respond_json(dict(error="Error: " + str(e)), status=500)

    def handle_discover(self):
        self.respond_json(dict(bridges=hue.discover_bridges_nupnp()))

    def handle_register(self):
        if self.kv().get('bridge') is not None:
            raise Exception('Bridge is already configured')
        try:
            id = self.args.get('id')
            ip = self.args.get('ip')
            username = hue.register(id, ip)
            self.kv().create('bridge', dict(id=id, ip=ip, username=username))
            self.respond_json(dict(success=True))
        except hue.HueError, e:
            self.respond_json(dict(error=str(e), code=e.code), 500)

    def handle_reset(self):
        self.kv().delete('bridge')
        self.respond_json(dict(success=True))


class HueDisoveryHandler(BaseHandler):
    def handle_GET(self):
        self.respond_json(hue.discover_bridges_nupnp())


class HueLightsHandler(BaseHandler):
    def handle_GET(self):
        try:
            bridge = self.kv().get("bridge")
            if bridge is None:
                raise Exception('Hue bridge is not configured')
            lights = hue.get_lights(bridge)
            self.respond_json(
                [dict(
                    id=light_id,
                    name=light.get('name'),
                    state=light.get('state')
                ) for light_id, light in lights.items()])
        except urllib2.HTTPError, e:
            self.respond_json(dict(error="Splunkd Error: " + str(e), response=e.read()), status=500)
        except Exception, e:
            # import traceback
            # self.respond_json(dict(error="Error: " + str(e), stack=traceback.format_exc()), status=500)
            self.respond_json(dict(error="Error: " + str(e)), status=500)

    def handle_POST(self):
        try:
            if 'action' in self.args:
                action = self.args['action']
                if action == 'rename':
                    self.handle_rename()
                    return
                if action == 'flash':
                    self.handle_flash()
                    return

            self.respond_json(dict(error="Invalid action"), status=400)
        except urllib2.HTTPError, e:
            self.respond_json(dict(error="Splunkd Error: " + str(e), response=e.read()), status=500)
        except Exception, e:
            # import traceback
            # self.respond_json(dict(error="Error: " + str(e), stack=traceback.format_exc()), status=500)
            self.respond_json(dict(error="Error: " + str(e)), status=500)

    def handle_rename(self):
        bridge = self.kv().get("bridge")
        hue.rename_light(bridge, self.args.get('id'), self.args.get('name'))
        self.respond_json(dict(success=True))

    def handle_flash(self):
        bridge = self.kv().get("bridge")
        hue.set_light_state(bridge, self.args.get('id'), json.dumps(dict(alert="select")))
        self.respond_json(dict(success=True))

