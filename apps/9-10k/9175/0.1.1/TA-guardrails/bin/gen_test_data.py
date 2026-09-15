#!/usr/bin/env python3
"""
gen_test_data.py - generate realistic TA-guardrails test data.

Produces a scenario, not just sample events. Background traffic across seven
providers plus three planted patterns that the shipped detection macros are
supposed to catch:

  1. Bypass reconnaissance - one identity tripping many distinct categories
     in a short window (guardrail_bypass_recon)
  2. Persistent injection - a single account with sustained prompt injection
     attempts (guardrail_top_offenders, guardrail_attacks)
  3. Silent failure - one provider's evaluation volume collapsing to zero
     partway through the window (guardrail_silent_failure)

If a detection does not fire against this data, the detection is broken.

Usage:
  python3 gen_test_data.py --stdout                     # inspect
  python3 gen_test_data.py --out /tmp/guardrails        # files per sourcetype
  python3 gen_test_data.py --hec https://localhost:8088 --token <TOKEN>

Stdlib only.
"""

import argparse
import json
import os
import random
import ssl
import sys
import time
import urllib.request

random.seed(1337)  # reproducible scenarios

NOW = time.time()
WINDOW_HOURS = 24

BENIGN_USERS = [
    ('alice.chen@contoso.com', '192.0.2.15', 'support-bot'),
    ('bob.n@contoso.com', '192.0.2.16', 'support-bot'),
    ('carol.diaz@contoso.com', '192.0.2.17', 'legal-assistant'),
    ('svc-hrbot@contoso.com', '192.0.2.18', 'hr-chatbot'),
    ('dan.osei@contoso.com', '192.0.2.19', 'finance-copilot'),
    ('erin.walsh@contoso.com', '192.0.2.20', 'legal-assistant'),
]

ATTACKER = ('contractor17@partner.example', '203.0.113.44', 'legal-assistant')
RECON = ('temp.analyst@contoso.com', '198.51.100.77', 'support-bot')

MODELS = {
    'bedrock': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    'azure_openai': 'gpt-4o-prod',
    'vertex': 'gemini-1.5-pro-002',
}


def ts(offset_seconds):
    return NOW - offset_seconds


def iso(epoch, frac=False):
    base = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(epoch))
    return base + ('.0000000Z' if frac else 'Z')


# ---------------------------------------------------------------------------
# Per-provider event builders
# ---------------------------------------------------------------------------

def bedrock_event(epoch, user, src, app, filters, pii=None, topic=None, blocked=True):
    assessments = [{}]
    if filters:
        assessments[0]['contentPolicy'] = {'filters': [
            {'type': t, 'confidence': c, 'filterStrength': 'HIGH',
             'action': 'BLOCKED' if c in ('HIGH', 'MEDIUM') else 'NONE'}
            for t, c in filters]}
    if pii:
        assessments[0]['sensitiveInformationPolicy'] = {
            'piiEntities': [{'type': p, 'action': a} for p, a in pii]}
    if topic:
        assessments[0]['topicPolicy'] = {
            'topics': [{'name': topic, 'type': 'DENY', 'action': 'BLOCKED'}]}
    return 'guardrail:bedrock', epoch, {
        'schemaType': 'ModelInvocationLog', 'schemaVersion': '1.0',
        'timestamp': iso(epoch), 'accountId': '123456789012', 'region': 'us-east-1',
        'requestId': 'req-%08x' % random.getrandbits(32),
        'operation': 'Converse', 'modelId': MODELS['bedrock'],
        'identity': {'arn': 'arn:aws:sts::123456789012:assumed-role/%s/%s' % (app, user.split('@')[0])},
        'input': {'inputContentType': 'application/json', 'inputTokenCount': random.randint(40, 900)},
        'output': {'outputTokenCount': random.randint(5, 400)},
        'guardrail': {
            'action': 'GUARDRAIL_INTERVENED' if blocked else 'NONE',
            'guardrailId': 'gr-9f21ab', 'guardrailVersion': '3',
            'assessments': assessments, 'inputDirection': 'INPUT'},
    }


def acs_event(epoch, user, src, app, cats, shield=False, blocklist=False, reject=True):
    return 'guardrail:azure:contentsafety', epoch, {
        'time': iso(epoch, frac=True), 'operationName': 'ContentSafety_AnalyzeText',
        'resourceId': '/SUBSCRIPTIONS/AAA/RESOURCEGROUPS/RG-AI/PROVIDERS/MICROSOFT.COGNITIVESERVICES/ACCOUNTS/CS-PROD',
        'category': 'RequestResponse', 'callerIpAddress': src,
        'correlationId': 'acs-%06x' % random.getrandbits(24),
        'properties': {
            'apiName': 'analyze/text', 'direction': 'input', 'userPrincipal': user,
            'result': {
                'blocklistsMatch': ([{'blocklistName': 'corp-terms',
                                      'blocklistItemText': 'projectfalcon'}] if blocklist else []),
                'categoriesAnalysis': [{'category': c, 'severity': s} for c, s in cats]},
            'promptShield': {'userPromptAnalysis': {'attackDetected': shield},
                             'documentsAnalysis': [{'attackDetected': False}]},
            'decision': 'reject' if reject else 'accept'},
    }


def aoai_event(epoch, user, src, app, filtered, jailbreak=False, direction='input'):
    cfr = {k: {'filtered': False, 'severity': 'safe'}
           for k in ('hate', 'self_harm', 'sexual', 'violence')}
    for k, sev in filtered:
        cfr[k] = {'filtered': True, 'severity': sev}
    cfr['jailbreak'] = {'filtered': jailbreak, 'detected': jailbreak}
    cfr['profanity'] = {'filtered': False, 'detected': False}
    return 'guardrail:azure:openai', epoch, {
        'time': iso(epoch), 'operationName': 'ChatCompletions_Create',
        'resourceId': '/SUBSCRIPTIONS/AAA/RESOURCEGROUPS/RG-AI/PROVIDERS/MICROSOFT.COGNITIVESERVICES/ACCOUNTS/AOAI-PROD',
        'callerIpAddress': src,
        'properties': {'modelDeploymentName': MODELS['azure_openai'], 'userPrincipal': user,
                       'requestId': 'aoai-%06x' % random.getrandbits(24),
                       'prompt_filter_results': [{'prompt_index': 0, 'content_filter_results': cfr}],
                       'direction': direction},
    }


def vertex_event(epoch, user, src, app, ratings, blocked=True, direction='output'):
    return 'guardrail:vertex', epoch, {
        'timestamp': iso(epoch),
        'logName': 'projects/gcp-ai-prod/logs/aiplatform.googleapis.com%2Fpredict',
        'resource': {'labels': {'project_id': 'gcp-ai-prod', 'location': 'us-central1'}},
        'jsonPayload': {
            'model': MODELS['vertex'], 'requestId': 'vx-%06x' % random.getrandbits(24),
            'principalEmail': user, 'callerIp': src, 'direction': direction,
            'finishReason': 'SAFETY' if blocked else 'STOP',
            'safetyRatings': [
                {'category': c, 'probability': p, 'probabilityScore': round(random.uniform(0.1, 0.99), 2),
                 'severity': s, 'severityScore': round(random.uniform(0.1, 0.95), 2),
                 'blocked': b} for c, p, s, b in ratings]},
    }


def lakera_event(epoch, user, src, app, cats, direction='input'):
    allc = {'prompt_injection': False, 'jailbreak': False, 'pii': False, 'moderated_content': False}
    scores = {k: round(random.uniform(0.01, 0.1), 2) for k in allc}
    for c in cats:
        allc[c] = True
        scores[c] = round(random.uniform(0.75, 0.99), 2)
    return 'guardrail:lakera', epoch, {
        'ts': iso(epoch), 'vendor': 'lakera', 'model': 'lakera-guard-1',
        'request_id': 'lk-%06x' % random.getrandbits(24), 'user': user, 'src': src,
        'app': app, 'direction': direction,
        'results': [{'flagged': bool(cats), 'categories': allc, 'category_scores': scores}],
    }


def llamaguard_event(epoch, user, src, app, categories, direction='output'):
    return 'guardrail:llamaguard', epoch, {
        'ts': iso(epoch), 'vendor': 'llama_guard', 'model': 'Llama-Guard-3-8B',
        'request_id': 'lg-%06x' % random.getrandbits(24), 'direction': direction,
        'app': app, 'user': user, 'src': src,
        'verdict': 'unsafe' if categories else 'safe',
        'violated_categories': categories,
        'raw': 'unsafe\n' + ','.join(categories) if categories else 'safe',
    }


def nemo_event(epoch, user, src, app, rails, direction='input'):
    return 'guardrail:nemo', epoch, {
        'ts': iso(epoch), 'vendor': 'nemo', 'app': app,
        'request_id': 'nm-%06x' % random.getrandbits(24), 'user': user, 'src': src,
        'direction': direction,
        'activated_rails': [{'name': n, 'decision': d, 'score': round(random.uniform(0.1, 0.99), 2)}
                            for n, d in rails],
    }


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

def build_scenario():
    events = []
    span = WINDOW_HOURS * 3600

    # --- background: mostly clean traffic, occasional legitimate blocks -----
    for _ in range(600):
        off = random.uniform(0, span)
        user, src, app = random.choice(BENIGN_USERS)
        r = random.random()
        if r < 0.55:
            events.append(bedrock_event(ts(off), user, src, app,
                                        [('HATE', 'NONE'), ('VIOLENCE', 'NONE')], blocked=False))
        elif r < 0.70:
            events.append(acs_event(ts(off), user, src, app,
                                    [('Hate', 0), ('SelfHarm', 0), ('Sexual', 0), ('Violence', 0)],
                                    reject=False))
        elif r < 0.80:
            events.append(aoai_event(ts(off), user, src, app, []))
        elif r < 0.88:
            events.append(vertex_event(ts(off), user, src, app,
                                       [('HARM_CATEGORY_HATE_SPEECH', 'NEGLIGIBLE',
                                         'HARM_SEVERITY_NEGLIGIBLE', False)], blocked=False))
        elif r < 0.93:
            events.append(lakera_event(ts(off), user, src, app, []))
        elif r < 0.97:
            events.append(nemo_event(ts(off), user, src, app, [('topical_rail', 'allow')]))
        else:
            events.append(llamaguard_event(ts(off), user, src, app, []))

    # genuine but scattered content blocks - noise a detection must survive
    for _ in range(45):
        off = random.uniform(0, span)
        user, src, app = random.choice(BENIGN_USERS)
        r = random.random()
        if r < 0.4:
            events.append(bedrock_event(ts(off), user, src, app, [('VIOLENCE', 'MEDIUM')]))
        elif r < 0.7:
            events.append(acs_event(ts(off), user, src, app,
                                    [('Hate', 0), ('SelfHarm', 0), ('Sexual', 2), ('Violence', 6)]))
        else:
            events.append(vertex_event(ts(off), user, src, app,
                                       [('HARM_CATEGORY_DANGEROUS_CONTENT', 'HIGH',
                                         'HARM_SEVERITY_HIGH', True)]))

    # PII detections spread across normal users - should NOT look like an attack
    for _ in range(25):
        off = random.uniform(0, span)
        user, src, app = random.choice(BENIGN_USERS)
        events.append(bedrock_event(ts(off), user, src, app, [],
                                    pii=[('EMAIL', 'ANONYMIZED')], blocked=False))

    # --- pattern 1: bypass reconnaissance -----------------------------------
    # One identity, 6 distinct categories, inside a single 15-minute bucket.
    recon_base = span * 0.35
    user, src, app = RECON
    events.append(bedrock_event(ts(recon_base), user, src, app, [('PROMPT_ATTACK', 'HIGH')]))
    events.append(bedrock_event(ts(recon_base - 90), user, src, app, [('HATE', 'HIGH')]))
    events.append(bedrock_event(ts(recon_base - 180), user, src, app, [('VIOLENCE', 'HIGH')]))
    events.append(acs_event(ts(recon_base - 300), user, src, app,
                            [('Hate', 0), ('SelfHarm', 6), ('Sexual', 0), ('Violence', 0)]))
    events.append(lakera_event(ts(recon_base - 420), user, src, app, ['pii']))
    events.append(nemo_event(ts(recon_base - 540), user, src, app,
                             [('check_blocked_terms', 'refuse')]))
    events.append(llamaguard_event(ts(recon_base - 660), user, src, app, ['S9']))

    # --- pattern 2: persistent injection ------------------------------------
    # Sustained low-and-slow injection from one contractor account over hours.
    user, src, app = ATTACKER
    for i in range(38):
        off = span * 0.7 - (i * random.uniform(200, 600))
        if off <= 0:
            continue
        r = random.random()
        if r < 0.4:
            events.append(bedrock_event(ts(off), user, src, app, [('PROMPT_ATTACK', 'HIGH')]))
        elif r < 0.7:
            events.append(lakera_event(ts(off), user, src, app, ['prompt_injection']))
        elif r < 0.9:
            events.append(aoai_event(ts(off), user, src, app, [], jailbreak=True))
        else:
            events.append(acs_event(ts(off), user, src, app,
                                    [('Hate', 0), ('SelfHarm', 0), ('Sexual', 0), ('Violence', 0)],
                                    shield=True))
    # and a couple of successful PII exfil attempts mixed in
    for i in range(6):
        events.append(bedrock_event(ts(span * 0.68 - i * 800), user, src, app, [],
                                    pii=[('US_SOCIAL_SECURITY_NUMBER', 'BLOCKED'),
                                         ('CREDIT_DEBIT_CARD_NUMBER', 'BLOCKED')]))

    # --- pattern 3: silent failure ------------------------------------------
    # NeMo evaluates steadily, then stops 6 hours ago. Nothing errors; the
    # events simply cease. This is what a disabled policy looks like.
    for h in range(WINDOW_HOURS, 6, -1):
        for _ in range(random.randint(8, 14)):
            off = h * 3600 - random.uniform(0, 3600)
            user, src, app = random.choice(BENIGN_USERS)
            events.append(nemo_event(ts(off), user, src, app,
                                     [('self_check_input', 'allow'), ('topical_rail', 'allow')]))

    events.sort(key=lambda e: e[1])
    return events


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def send_hec(events, url, token, verify):
    endpoint = url.rstrip('/') + '/services/collector/event'
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    batch, sent = [], 0
    for sourcetype, epoch, doc in events:
        batch.append(json.dumps({
            'time': round(epoch, 3), 'host': 'guardrail-test',
            'source': 'gen_test_data', 'sourcetype': sourcetype,
            'index': 'guardrails', 'event': doc}))
        if len(batch) >= 100:
            sent += _post(endpoint, token, batch, ctx)
            batch = []
    if batch:
        sent += _post(endpoint, token, batch, ctx)
    print('sent {0} events to {1}'.format(sent, endpoint))


def _post(endpoint, token, batch, ctx):
    body = '\n'.join(batch).encode('utf-8')
    req = urllib.request.Request(endpoint, data=body)
    req.add_header('Authorization', 'Splunk ' + token)
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        payload = json.loads(resp.read().decode())
        if payload.get('code') != 0:
            print('HEC error: {0}'.format(payload), file=sys.stderr)
            return 0
        return len(batch)
    except Exception as exc:
        print('HEC post failed: {0}'.format(exc), file=sys.stderr)
        return 0


def write_files(events, outdir):
    os.makedirs(outdir, exist_ok=True)
    handles = {}
    for sourcetype, epoch, doc in events:
        name = sourcetype.replace(':', '_') + '.json'
        fh = handles.get(name) or open(os.path.join(outdir, name), 'w')
        handles[name] = fh
        fh.write(json.dumps(doc) + '\n')
    for name, fh in handles.items():
        fh.close()
        print('wrote {0}'.format(os.path.join(outdir, name)))


def summarize(events):
    from collections import Counter
    by_st = Counter(e[0] for e in events)
    print('\n{0} events across {1} hours'.format(len(events), WINDOW_HOURS))
    for st, n in sorted(by_st.items()):
        print('  {0:34s} {1}'.format(st, n))
    print('\nPlanted patterns:')
    print('  bypass recon      {0} / {1}'.format(*RECON[:2]))
    print('  persistent inject {0} / {1}'.format(*ATTACKER[:2]))
    print('  silent failure    guardrail:nemo stops ~6h ago')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hec', help='HEC base URL, e.g. https://localhost:8088')
    ap.add_argument('--token', help='HEC token')
    ap.add_argument('--out', help='write newline-delimited JSON files to this directory')
    ap.add_argument('--stdout', action='store_true')
    ap.add_argument('--insecure', action='store_true', help='skip TLS verification')
    args = ap.parse_args()

    events = build_scenario()
    summarize(events)

    if args.hec:
        if not args.token:
            sys.exit('--hec requires --token')
        send_hec(events, args.hec, args.token, verify=not args.insecure)
    if args.out:
        write_files(events, args.out)
    if args.stdout:
        for st, epoch, doc in events[:20]:
            print('{0}\t{1}'.format(st, json.dumps(doc)))
        print('... ({0} more)'.format(len(events) - 20))


if __name__ == '__main__':
    main()
