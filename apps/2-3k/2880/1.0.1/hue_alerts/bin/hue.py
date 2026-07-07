import colorsys
import json
import socket
import urllib2

from kvstore import KVStoreCollection
from util import merge


class HueError(Exception):
    def __init__(self, msg, code=0):
        Exception.__init__(self, msg)
        self.code = code


def hue_state_kv(server_uri, session_key):
    return KVStoreCollection('hue_alerts_state', server_uri, session_key, app='hue_alerts')


def discover_bridges():
    return discover_bridges_nupnp()


def discover_bridges_nupnp():
    req = urllib2.Request('https://www.meethue.com/api/nupnp')
    res = urllib2.urlopen(req)
    data = json.loads(res.read())
    return [dict(id=b['id'], ip=b['internalipaddress']) for b in data]


def discover_bridges_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1900))
    print sock

    upnp_msg = '\r\n'.join((
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1900',
        'MAN: "ssdp:discover"',
        'MX: 3',
        'ST: go.hue:idl',
        ''))

    print 'sending', upnp_msg
    sock.sendto(upnp_msg, ('239.255.255.250', 1900))

    while True:
        data, addr = sock.recvfrom(8192)
        print "RECEIVED", data, addr


def get_bridge_ip(bridge_id):
    matches = filter(lambda b: b['id'] == bridge_id, discover_bridges())
    if len(matches) != 1:
        raise HueError("Bridge not found")
    return matches[0]['ip']


def register(bridge_id, ip=None):
    if ip is None:
        ip = get_bridge_ip(bridge_id)
    req = urllib2.Request('http://%s/api' % ip, json.dumps(dict(devicetype='Splunk#test1')))
    try:
        res = urllib2.urlopen(req, timeout=5)
        data = json.loads(res.read())
        reply = data[0]
        if 'error' in reply:
            err = reply.get('error')
            raise HueError(err.get('description'), err.get('type', 0))
        if 'success' in reply:
            return reply.get('success').get('username')
        raise HueError('Unexpected response')
    except urllib2.URLError:
        raise HueError('Cannot connect to brigde at ' + ip)


def hue_request(bridge, method, path, data=None, timeout=5):
    url = 'http://%(ip)s/api/%(username)s%(path)s' % merge(bridge, dict(path=path))
    req = urllib2.Request(url, data)
    req.get_method = lambda: method
    res = urllib2.urlopen(req, timeout=timeout)
    return json.loads(res.read())


def test_connection(bridge):
    try:
        hue_request(bridge, 'GET', '/config', timeout=2)
        return True
    except urllib2.URLError:
        ip = get_bridge_ip(bridge.get('id'))
        if ip != bridge.get('ip'):
            bridge['ip'] = ip
            bridge['dirty'] = True
            try:
                hue_request(bridge, 'GET', '/config', timeout=2)
                return True
            except urllib2.URLError:
                pass
    return False


def get_lights(bridge):
    return hue_request(bridge, 'GET', '/lights')


def set_light_state(bridge, light, state):
    return hue_request(bridge, 'PUT', '/lights/%s/state' % light, data=state)


def rename_light(bridge, light, name):
    return hue_request(bridge, 'PUT', '/lights/%s' % light, data=json.dumps(dict(name=name)))

def rgb_to_hue_sat(val):
    r, g, b = [int(''.join(t), 16) / 255.0 for t in zip(*[val[i + 1::2] for i in range(2)])]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    print h, s, v
    return int(h * 65535), int(s * 254)
