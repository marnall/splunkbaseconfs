import sys
import json
from fnmatch import fnmatch

import hue


COLOR_NAMES = dict(
    white=(0, 0),
    red=(0, 254),
    yellow=(12750, 254),
    green=(25500, 254),
    blue=(46920, 254),
)

ALERT_VALS = dict(
    none="none",
    once="select",
    long="lselect",
)

payload = json.loads(sys.stdin.read())

kv = hue.hue_state_kv(payload.get('server_uri'), payload.get('session_key'))
bridge = kv.get('bridge')

if bridge is None:
    print >> sys.stderr, "FATAL Hue bridge is not configured"
    sys.exit(1)

print >> sys.stderr, "DEBUG Got bridge info: ", bridge

config = payload.get('configuration', dict())
patterns = config.get('lights', '*').split(',')

lights = hue.get_lights(bridge)
# find all lights we want to modify
matches = [light_id for light_id, light in lights.items() if
           # lights IDs matching the pattern
           any([fnmatch(light_id, pattern.strip()) for pattern in patterns]) or
           # lights names matching the pattern
           any([fnmatch(light.get('name').lower(), pattern.lower().strip()) for pattern in patterns])]

if len(matches) == 0:
    print >> sys.stderr, "WARN No light names matched"
    sys.exit(0)

# Compute new state

state = dict()
if 'color' in config:
    color = config.get('color', '#ffffff')
    if color in COLOR_NAMES:
        hue_val, sat = COLOR_NAMES[color]
    else:
        hue_val, sat = hue.rgb_to_hue_sat(color)
    state.update(dict(hue=hue_val, sat=sat))
if 'bri' in config:
    state['bri'] = int(config.get('bri', '255'))
if 'on' in config:
    state['on'] = config.get('on', '1') == '1'
state['alert'] = ALERT_VALS.get(config.get('flash', 'none'), 'none')

print >> sys.stderr, "INFO Applying state=%s to lights=%s" % (json.dumps(state), json.dumps(matches))

# Apply state to lights
for light in matches:
    hue.set_light_state(bridge, light, json.dumps(state))