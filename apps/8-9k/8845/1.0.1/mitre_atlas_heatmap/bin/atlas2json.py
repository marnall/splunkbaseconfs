"""
Fetches the latest MITRE ATLAS matrix data and converts it into the
tactics/techniques/sub_techniques JSON structure consumed by the
MITRE ATLAS Heatmap visualization (build/atlasMatrix.js).

Usage:
    pip install pyyaml requests
    python atlas2json.py
"""
import requests
import json
import re

path_prefix = '../appserver/static/visualizations/mitre_atlas_heatmap/build/'

# ATLAS matrix tactic ordering, mirrors the order published on
# https://atlas.mitre.org/matrices/ATLAS
sort_order = [
    'Reconnaissance', 'Resource Development', 'Initial Access',
    'AI Model Access', 'Execution', 'Persistence', 'Privilege Escalation',
    'Defense Evasion', 'Credential Access', 'Discovery', 'Lateral Movement',
    'Collection', 'AI Attack Staging', 'Command and Control', 'Exfiltration',
    'Impact'
]

url = 'https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml'

response = requests.get(url)
response.raise_for_status()

import yaml
atlas = yaml.safe_load(response.text)
matrix = atlas['matrices'][0]

output_json = {'tactics': [], 'techniques': [], 'sub_techniques': []}

for tactic in matrix['tactics']:
    output_json['tactics'].append({
        'id': tactic['id'],
        'name': tactic['name'],
        'short_name': tactic['id'],
        'sort_order': sort_order.index(tactic['name']) if tactic['name'] in sort_order else 100
    })

for technique in matrix['techniques']:
    is_sub = bool(re.match(r'AML\.T\d{4}\.\d+', technique['id']))
    if not is_sub:
        output_json['techniques'].append({
            'id': technique['id'],
            'name': technique.get('name', ''),
            'tactics': technique.get('tactics', []),
            'url': 'https://atlas.mitre.org/techniques/' + technique['id'],
            'platform': []
        })
    else:
        short_id = re.search(r'\.\d+$', technique['id'])
        output_json['sub_techniques'].append({
            'id': technique['id'],
            'short_id': short_id.group() if short_id else None,
            'name': technique.get('name', ''),
            'technique': technique.get('specializes'),
            'url': 'https://atlas.mitre.org/techniques/' + technique['id'],
            'platform': []
        })

output_json['tactics'] = sorted(output_json['tactics'], key=lambda t: t['sort_order'])
output_json['sub_techniques'] = sorted(output_json['sub_techniques'], key=lambda s: s['id'])

with open(path_prefix + 'atlasMatrix.js', 'w') as fp:
    fp.write('define(function() { return ' + json.dumps(output_json) + ' })')

print('Wrote', len(output_json['tactics']), 'tactics,',
      len(output_json['techniques']), 'techniques,',
      len(output_json['sub_techniques']), 'sub-techniques')
print('Now run `webpack` inside appserver/static/visualizations/mitre_atlas_heatmap to rebuild visualization.js')
