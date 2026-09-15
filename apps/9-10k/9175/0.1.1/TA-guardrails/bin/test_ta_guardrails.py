#!/usr/bin/env python3
"""Validate TA-guardrails: taxonomy coverage, normalization, CIM compliance."""

import csv
import configparser
import json
import glob
import os
import re
import sys

BASE = '/home/claude/TA-guardrails'
FAIL = []


def check(label, cond, detail=''):
    if not cond:
        FAIL.append(label)
    print('  [{0}] {1}{2}'.format('PASS' if cond else 'FAIL', label,
                                  (' -> ' + str(detail)) if detail else ''))


def load(name):
    with open(os.path.join(BASE, 'lookups', name)) as fh:
        return list(csv.DictReader(fh))


cats = load('guardrail_categories.csv')
cmap = load('guardrail_category_map.csv')
smap = load('guardrail_severity_map.csv')
amap = load('guardrail_action_map.csv')

CAT_NAMES = set(c['category'] for c in cats)

print('\n== Taxonomy integrity ==')
check('categories unique', len(CAT_NAMES) == len(cats), '{0} rows'.format(len(cats)))
check('every mapped category exists in taxonomy',
      all(r['category'] in CAT_NAMES for r in cmap),
      [r['category'] for r in cmap if r['category'] not in CAT_NAMES])
check('unknown fallback defined', 'unknown' in CAT_NAMES)
check('is_attack is 0/1', all(r['is_attack'] in ('0', '1') for r in cats))
check('attack categories flagged',
      all(c['is_attack'] == '1' for c in cats
          if c['category'] in ('prompt_injection', 'jailbreak', 'code_execution', 'credential_exposure')),
      [c['category'] for c in cats if c['is_attack'] == '1'])
check('every category has a family', all(r['category_family'] for r in cats))
check('every category has a description', all(r['category_description'] for r in cats))

print('\n== Mapping key integrity ==')
cmap_keys = [(r['guardrail_vendor'], r['vendor_category']) for r in cmap]
check('no duplicate category keys', len(cmap_keys) == len(set(cmap_keys)),
      [k for k in cmap_keys if cmap_keys.count(k) > 1])
smap_keys = [(r['guardrail_vendor'], r['vendor_severity']) for r in smap]
check('no duplicate severity keys', len(smap_keys) == len(set(smap_keys)))
amap_keys = [(r['guardrail_vendor'], r['vendor_action']) for r in amap]
check('no duplicate action keys', len(amap_keys) == len(set(amap_keys)))

print('\n== Severity normalization ==')
check('scores within 0-100', all(0 <= int(r['guardrail_score']) <= 100 for r in smap))
CIM_SEV = {'critical', 'high', 'medium', 'low', 'informational', 'unknown'}
check('severity uses CIM vocabulary',
      all(r['severity'] in CIM_SEV for r in smap),
      sorted(set(r['severity'] for r in smap) - CIM_SEV))
check('severity_id numeric', all(r['severity_id'].isdigit() for r in smap))
# score and band must agree in ordering
bands = {}
for r in smap:
    bands.setdefault(r['severity'], []).append(int(r['guardrail_score']))
order = ['informational', 'low', 'medium', 'high', 'critical']
present = [b for b in order if b in bands]
maxes = [max(bands[b]) for b in present]
check('score bands monotonic with severity', maxes == sorted(maxes),
      dict(zip(present, maxes)))

print('\n== Action normalization ==')
check('CIM action is allowed|blocked only',
      all(r['action'] in ('allowed', 'blocked') for r in amap),
      sorted(set(r['action'] for r in amap)))
check('anonymized preserved in guardrail_action',
      any(r['guardrail_action'] == 'anonymized' for r in amap))
check('anonymized maps to allowed in CIM',
      all(r['action'] == 'allowed' for r in amap if r['guardrail_action'] == 'anonymized'))
check('flagged preserved', any(r['guardrail_action'] == 'flagged' for r in amap))

print('\n== Vendor coverage ==')
VENDORS = {'bedrock', 'azure_content_safety', 'azure_openai', 'vertex',
           'llama_guard', 'lakera', 'nemo'}
for v in sorted(VENDORS):
    has_c = any(r['guardrail_vendor'] == v for r in cmap)
    has_s = any(r['guardrail_vendor'] == v for r in smap)
    has_a = any(r['guardrail_vendor'] == v for r in amap)
    check('mapped: ' + v, has_c and has_s and has_a,
          'cat={0} sev={1} act={2}'.format(has_c, has_s, has_a))

print('\n== Fixture normalization (every vendor value must resolve) ==')
CAT_LOOKUP = {(r['guardrail_vendor'], r['vendor_category']): r['category'] for r in cmap}
SEV_LOOKUP = {(r['guardrail_vendor'], r['vendor_severity'].lower()): r for r in smap}
ACT_LOOKUP = {(r['guardrail_vendor'], r['vendor_action'].lower()): r for r in amap}


def extract(vendor, doc):
    """Mirror what props.conf derives, so the fixtures actually exercise the maps."""
    out = {'vendor': vendor, 'categories': [], 'severities': [], 'actions': []}
    if vendor == 'bedrock':
        g = doc['guardrail']
        for a in g['assessments']:
            for f in a.get('contentPolicy', {}).get('filters', []):
                out['categories'].append(f['type'])
                out['severities'].append(f['confidence'])
                out['actions'].append(f['action'])
            for t in a.get('topicPolicy', {}).get('topics', []):
                out['categories'].append('TOPIC')
                out['actions'].append(t['action'])
            for p in a.get('sensitiveInformationPolicy', {}).get('piiEntities', []):
                out['categories'].append('PII')
                out['actions'].append(p['action'])
        out['actions'].append(g['action'])
    elif vendor == 'azure_content_safety':
        pr = doc['properties']
        for c in pr['result']['categoriesAnalysis']:
            out['categories'].append(c['category'])
            out['severities'].append(str(c['severity']))
        if pr['promptShield']['userPromptAnalysis']['attackDetected']:
            out['categories'].append('userPromptAttack')
        if pr['result']['blocklistsMatch']:
            out['categories'].append('blocklistsMatch')
        out['actions'].append(pr['decision'])
    elif vendor == 'azure_openai':
        cfr = doc['properties']['prompt_filter_results'][0]['content_filter_results']
        for k, v in cfr.items():
            if v.get('filtered') or v.get('detected'):
                out['categories'].append(k)
            if 'severity' in v:
                out['severities'].append(v['severity'])
            out['actions'].append(str(v.get('filtered', False)).lower())
    elif vendor == 'vertex':
        for r in doc['jsonPayload']['safetyRatings']:
            out['categories'].append(r['category'])
            out['severities'].append(r['severity'])
            out['actions'].append(str(r['blocked']).lower())
        out['actions'].append(doc['jsonPayload']['finishReason'])
    elif vendor == 'llama_guard':
        out['categories'] = doc['violated_categories']
        out['severities'].append(doc['verdict'])
        out['actions'].append(doc['verdict'])
    elif vendor == 'lakera':
        res = doc['results'][0]
        out['categories'] = [k for k, v in res['categories'].items() if v]
        out['severities'].append('flagged' if res['flagged'] else 'clean')
        out['actions'].append(str(res['flagged']).lower())
    elif vendor == 'nemo':
        for r in doc['activated_rails']:
            out['categories'].append(r['name'])
            out['actions'].append(r['decision'])
        out['severities'].append('blocked' if any(
            r['decision'] == 'refuse' for r in doc['activated_rails']) else 'allowed')
    return out


FIXTURES = {
    'bedrock_guardrail.json': 'bedrock',
    'azure_content_safety.json': 'azure_content_safety',
    'azure_openai_filter.json': 'azure_openai',
    'vertex_safety.json': 'vertex',
    'llama_guard.json': 'llama_guard',
    'lakera_guard.json': 'lakera',
    'nemo_guardrails.json': 'nemo',
}

normalized_rows = []
for fname, vendor in sorted(FIXTURES.items()):
    doc = json.load(open(os.path.join(BASE, 'samples', fname)))
    ex = extract(vendor, doc)

    unmapped_c = [c for c in ex['categories'] if (vendor, c) not in CAT_LOOKUP]
    check('categories resolve: ' + vendor, not unmapped_c, unmapped_c or ex['categories'])

    unmapped_s = [s for s in ex['severities'] if (vendor, s.lower()) not in SEV_LOOKUP]
    check('severities resolve: ' + vendor, not unmapped_s, unmapped_s or ex['severities'])

    unmapped_a = [a for a in ex['actions'] if (vendor, a.lower()) not in ACT_LOOKUP]
    check('actions resolve: ' + vendor, not unmapped_a, unmapped_a or ex['actions'])

    for c in ex['categories']:
        if (vendor, c) in CAT_LOOKUP:
            normalized_rows.append((vendor, c, CAT_LOOKUP[(vendor, c)]))

print('\n== Cross-vendor equivalence ==')
by_norm = {}
for v, vc, nc in normalized_rows:
    by_norm.setdefault(nc, set()).add(v)
shared = {k: sorted(v) for k, v in by_norm.items() if len(v) > 1}
check('at least 3 categories span multiple vendors', len(shared) >= 3, shared)
check('hate_discrimination spans >=3 vendors in fixtures',
      len(by_norm.get('hate_discrimination', set())) >= 3,
      sorted(by_norm.get('hate_discrimination', set())))
check('prompt_injection reached from >=2 vendors',
      len(by_norm.get('prompt_injection', set())) >= 2,
      sorted(by_norm.get('prompt_injection', set())))

print('\n== props.conf ==')
props = open(os.path.join(BASE, 'default/props.conf')).read()
stanzas = re.findall(r'^\[(guardrail:[^\]]+)\]', props, re.M)
check('seven sourcetypes defined', len(stanzas) == 7, stanzas)
for st in stanzas:
    body = props.split('[' + st + ']', 1)[1].split('\n[')[0]
    check('shared lookups on ' + st, body.count('LOOKUP-0') == 4)
    check('vendor set on ' + st, 'EVAL-guardrail_vendor' in body)
    check('ids_type on ' + st, 'EVAL-ids_type' in body)

check('SEDCMD redaction present', props.count('SEDCMD-') >= 4,
      '{0} rules'.format(props.count('SEDCMD-')))
check('no reference to undefined lookup',
      all(t in open(os.path.join(BASE, 'default/transforms.conf')).read()
          for t in ['guardrail_category_map', 'guardrail_severity_map',
                    'guardrail_action_map', 'guardrail_categories']))

print('\n== CIM Intrusion Detection required fields ==')
required = ['action', 'category', 'dest', 'dvc', 'ids_type', 'severity',
            'severity_id', 'signature', 'src', 'user', 'user_name', 'vendor_product']
for f in required:
    present = ('EVAL-' + f) in props or (' AS ' + f) in props or ('OUTPUTNEW' in props and f in props)
    check('provides ' + f, present)
check('ids_type uses CIM vocabulary', re.search(r'EVAL-ids_type = "(network|host|application|wireless)"', props) is not None)

print('\n== Conf file sanity ==')
for conf in ['app.conf', 'props.conf', 'transforms.conf', 'eventtypes.conf',
             'tags.conf', 'macros.conf', 'inputs.conf']:
    cp = configparser.RawConfigParser(strict=False, delimiters=('=',))
    cp.optionxform = str
    try:
        cp.read(os.path.join(BASE, 'default', conf))
        check('parses: ' + conf, True, '{0} stanzas'.format(len(cp.sections())))
    except Exception as exc:
        check('parses: ' + conf, False, exc)

inp = configparser.RawConfigParser(strict=False, delimiters=('=',))
inp.read(os.path.join(BASE, 'default/inputs.conf'))
check('all inputs disabled',
      all(inp.get(s, 'disabled', fallback='0').strip() == '1' for s in inp.sections()))

json.load(open(os.path.join(BASE, 'app.manifest')))
check('app.manifest valid json', True)

print('\n== Macro references resolve ==')
mac = configparser.RawConfigParser(strict=False, delimiters=('=',))
mac.optionxform = str
mac.read(os.path.join(BASE, 'default/macros.conf'))
defined = set(s.split('(')[0] for s in mac.sections())
missing = []
for s in mac.sections():
    for ref in re.findall(r'`([a-z_0-9]+)', mac.get(s, 'definition', fallback='')):
        if ref.split('(')[0] not in defined:
            missing.append((s, ref))
check('all backtick macro refs defined', not missing, missing)
check('findings macros cover >=6 vendors',
      len([s for s in mac.sections() if s.startswith('guardrail_findings_')]) >= 6,
      [s for s in mac.sections() if s.startswith('guardrail_findings_')])

print('\n' + '=' * 62)
if FAIL:
    print('FAILED ({0}): {1}'.format(len(FAIL), FAIL))
    sys.exit(1)
print('ALL CHECKS PASSED')
