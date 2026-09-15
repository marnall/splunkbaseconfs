#!/usr/bin/env python3
"""
Generates the TA-guardrails normalization lookups.

The taxonomy lives here so that the CSVs, the schema doc, and the tests can
never drift from one another. Regenerate with: python3 build_lookups.py
"""

import csv
import os

BASE = '/home/claude/TA-guardrails'

# ---------------------------------------------------------------------------
# Normalized category taxonomy.
#
# Aligned with the MLCommons hazard taxonomy where a hazard concept exists, and
# with OWASP LLM Top 10 where the concern is an attack rather than a hazard.
# 'family' groups categories for reporting; 'is_attack' distinguishes an
# adversarial action against the system from unsafe content passing through it.
# That distinction is the one SOC analysts care about most: a user asking about
# violence is a content event, a user trying to override the system prompt is
# an intrusion event.
# ---------------------------------------------------------------------------
CATEGORIES = [
    # name,                  family,        is_attack, description
    ('hate_discrimination',  'harmful',     0, 'Hate speech, slurs, or discriminatory content'),
    ('harassment',           'harmful',     0, 'Insults, bullying, or targeted harassment'),
    ('violence',             'harmful',     0, 'Violent content or threats'),
    ('sexual_content',       'harmful',     0, 'Sexual or adult content'),
    ('child_safety',         'harmful',     0, 'Child sexual exploitation or endangerment'),
    ('self_harm',            'harmful',     0, 'Suicide, self-harm, or disordered eating'),
    ('criminal_activity',    'harmful',     0, 'Facilitation of criminal acts'),
    ('dangerous_advice',     'harmful',     0, 'Weapons, CBRN, or hazardous specialized advice'),
    ('profanity',            'harmful',     0, 'Profanity or obscene language'),
    ('elections',            'harmful',     0, 'Election misinformation'),
    ('defamation',           'harmful',     0, 'Defamatory content about real persons'),

    ('pii_exposure',         'data',        0, 'Personally identifiable information detected'),
    ('credential_exposure',  'data',        1, 'Secrets, keys, or credentials detected'),
    ('intellectual_property','data',        0, 'Protected or copyrighted material'),

    ('prompt_injection',     'attack',      1, 'Instruction override or injected directive'),
    ('jailbreak',            'attack',      1, 'Attempt to bypass model safety alignment'),
    ('code_execution',       'attack',      1, 'Abuse of code interpreter or tool execution'),

    ('topic_denied',         'policy',      0, 'Topic prohibited by deployment policy'),
    ('groundedness',         'quality',     0, 'Response not grounded in provided source'),
    ('relevance',            'quality',     0, 'Response not relevant to the query'),
    ('custom_word',          'policy',      0, 'Custom word or blocklist match'),
    ('custom_regex',         'policy',      0, 'Custom regular expression match'),
    ('unknown',              'unknown',     0, 'Unmapped vendor category'),
]

# ---------------------------------------------------------------------------
# Vendor category -> normalized category.
# guardrail_vendor is included in the key because vendors reuse names with
# different meanings ("Violence" in Azure is a severity-scored hazard, in
# Llama Guard S1 it is a crime category).
# ---------------------------------------------------------------------------
CATEGORY_MAP = [
    # vendor,      vendor_category,                  category
    ('bedrock',    'HATE',                           'hate_discrimination'),
    ('bedrock',    'INSULTS',                        'harassment'),
    ('bedrock',    'SEXUAL',                         'sexual_content'),
    ('bedrock',    'VIOLENCE',                       'violence'),
    ('bedrock',    'MISCONDUCT',                     'criminal_activity'),
    ('bedrock',    'PROMPT_ATTACK',                  'prompt_injection'),
    ('bedrock',    'GROUNDING',                      'groundedness'),
    ('bedrock',    'RELEVANCE',                      'relevance'),
    ('bedrock',    'PROFANITY',                      'profanity'),
    ('bedrock',    'TOPIC',                          'topic_denied'),
    ('bedrock',    'CUSTOM_WORD',                    'custom_word'),
    ('bedrock',    'REGEX',                          'custom_regex'),
    ('bedrock',    'PII',                            'pii_exposure'),

    ('azure_content_safety', 'Hate',                 'hate_discrimination'),
    ('azure_content_safety', 'SelfHarm',             'self_harm'),
    ('azure_content_safety', 'Sexual',               'sexual_content'),
    ('azure_content_safety', 'Violence',             'violence'),
    ('azure_content_safety', 'userPromptAttack',     'prompt_injection'),
    ('azure_content_safety', 'documentAttack',       'prompt_injection'),
    ('azure_content_safety', 'blocklistsMatch',      'custom_word'),

    ('azure_openai', 'hate',                         'hate_discrimination'),
    ('azure_openai', 'self_harm',                    'self_harm'),
    ('azure_openai', 'sexual',                       'sexual_content'),
    ('azure_openai', 'violence',                     'violence'),
    ('azure_openai', 'jailbreak',                    'jailbreak'),
    ('azure_openai', 'profanity',                    'profanity'),
    ('azure_openai', 'protected_material_code',      'intellectual_property'),
    ('azure_openai', 'protected_material_text',      'intellectual_property'),
    ('azure_openai', 'indirect_attack',              'prompt_injection'),

    ('vertex',     'HARM_CATEGORY_HATE_SPEECH',      'hate_discrimination'),
    ('vertex',     'HARM_CATEGORY_HARASSMENT',       'harassment'),
    ('vertex',     'HARM_CATEGORY_SEXUALLY_EXPLICIT','sexual_content'),
    ('vertex',     'HARM_CATEGORY_DANGEROUS_CONTENT','dangerous_advice'),
    ('vertex',     'HARM_CATEGORY_CIVIC_INTEGRITY',  'elections'),

    ('llama_guard','S1',                             'criminal_activity'),
    ('llama_guard','S2',                             'criminal_activity'),
    ('llama_guard','S3',                             'criminal_activity'),
    ('llama_guard','S4',                             'child_safety'),
    ('llama_guard','S5',                             'defamation'),
    ('llama_guard','S6',                             'dangerous_advice'),
    ('llama_guard','S7',                             'pii_exposure'),
    ('llama_guard','S8',                             'intellectual_property'),
    ('llama_guard','S9',                             'dangerous_advice'),
    ('llama_guard','S10',                            'hate_discrimination'),
    ('llama_guard','S11',                            'self_harm'),
    ('llama_guard','S12',                            'sexual_content'),
    ('llama_guard','S13',                            'elections'),
    ('llama_guard','S14',                            'code_execution'),

    ('lakera',     'prompt_injection',               'prompt_injection'),
    ('lakera',     'jailbreak',                      'jailbreak'),
    ('lakera',     'pii',                            'pii_exposure'),
    ('lakera',     'moderated_content',              'harassment'),
    ('lakera',     'unknown_links',                  'custom_regex'),

    ('nemo',       'self_check_input',               'prompt_injection'),
    ('nemo',       'self_check_output',              'groundedness'),
    ('nemo',       'check_blocked_terms',            'custom_word'),
    ('nemo',       'topical_rail',                   'topic_denied'),
]

# ---------------------------------------------------------------------------
# Vendor severity/confidence -> normalized 0-100 score and CIM severity band.
#
# Normalizing to a shared numeric scale is what makes cross-vendor alerting
# possible at all. The mapping is deliberately conservative: where a vendor
# gives a coarse band, the score is placed at the middle of that band rather
# than its edge, so thresholds behave predictably across providers.
# ---------------------------------------------------------------------------
SEVERITY_MAP = [
    # vendor,               vendor_severity, score, severity,        severity_id
    ('bedrock',             'NONE',          0,   'informational', 1),
    ('bedrock',             'LOW',           30,  'low',           2),
    ('bedrock',             'MEDIUM',        60,  'medium',        3),
    ('bedrock',             'HIGH',          90,  'high',          4),

    ('azure_content_safety','0',             0,   'informational', 1),
    ('azure_content_safety','1',             15,  'low',           2),
    ('azure_content_safety','2',             30,  'low',           2),
    ('azure_content_safety','3',             45,  'medium',        3),
    ('azure_content_safety','4',             60,  'medium',        3),
    ('azure_content_safety','5',             75,  'high',          4),
    ('azure_content_safety','6',             90,  'high',          4),
    ('azure_content_safety','7',             100, 'critical',      5),

    ('azure_openai',        'safe',          0,   'informational', 1),
    ('azure_openai',        'low',           30,  'low',           2),
    ('azure_openai',        'medium',        60,  'medium',        3),
    ('azure_openai',        'high',          90,  'high',          4),

    ('vertex',              'NEGLIGIBLE',    0,   'informational', 1),
    ('vertex',              'LOW',           30,  'low',           2),
    ('vertex',              'MEDIUM',        60,  'medium',        3),
    ('vertex',              'HIGH',          90,  'high',          4),
    ('vertex',              'HARM_SEVERITY_NEGLIGIBLE', 0,  'informational', 1),
    ('vertex',              'HARM_SEVERITY_LOW',        30, 'low',           2),
    ('vertex',              'HARM_SEVERITY_MEDIUM',     60, 'medium',        3),
    ('vertex',              'HARM_SEVERITY_HIGH',       90, 'high',          4),

    ('llama_guard',         'safe',          0,   'informational', 1),
    ('llama_guard',         'unsafe',        80,  'high',          4),

    ('lakera',              'flagged',       80,  'high',          4),
    ('lakera',              'clean',         0,   'informational', 1),

    ('nemo',                'blocked',       80,  'high',          4),
    ('nemo',                'allowed',       0,   'informational', 1),
]

# ---------------------------------------------------------------------------
# Vendor action -> normalized action and CIM Intrusion Detection action.
#
# CIM permits only allowed|blocked for the IDS datamodel, so the richer
# guardrail_action is kept alongside it rather than being flattened away.
# 'anonymized' is the interesting case: the request proceeded, but content was
# redacted. That is neither a clean allow nor a block, and collapsing it to
# either loses the fact that PII was present.
# ---------------------------------------------------------------------------
ACTION_MAP = [
    # vendor,               vendor_action, guardrail_action, action
    ('bedrock',             'BLOCKED',     'blocked',    'blocked'),
    ('bedrock',             'ANONYMIZED',  'anonymized', 'allowed'),
    ('bedrock',             'NONE',        'allowed',    'allowed'),
    ('bedrock',             'GUARDRAIL_INTERVENED', 'blocked', 'blocked'),
    ('bedrock',             'DENY',        'blocked',    'blocked'),

    ('azure_content_safety','reject',      'blocked',    'blocked'),
    ('azure_content_safety','accept',      'allowed',    'allowed'),

    ('azure_openai',        'true',        'blocked',    'blocked'),
    ('azure_openai',        'false',       'allowed',    'allowed'),

    ('vertex',              'true',        'blocked',    'blocked'),
    ('vertex',              'false',       'allowed',    'allowed'),
    ('vertex',              'SAFETY',      'blocked',    'blocked'),

    ('llama_guard',         'unsafe',      'flagged',    'blocked'),
    ('llama_guard',         'safe',        'allowed',    'allowed'),

    ('lakera',              'true',        'flagged',    'blocked'),
    ('lakera',              'false',       'allowed',    'allowed'),

    ('nemo',                'refuse',      'blocked',    'blocked'),
    ('nemo',                'allow',       'allowed',    'allowed'),
]


def write(path, header, rows):
    full = os.path.join(BASE, path)
    with open(full, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print('wrote {0} ({1} rows)'.format(path, len(rows)))


if __name__ == '__main__':
    write('lookups/guardrail_categories.csv',
          ['category', 'category_family', 'is_attack', 'category_description'],
          CATEGORIES)
    write('lookups/guardrail_category_map.csv',
          ['guardrail_vendor', 'vendor_category', 'category'],
          CATEGORY_MAP)
    write('lookups/guardrail_severity_map.csv',
          ['guardrail_vendor', 'vendor_severity', 'guardrail_score', 'severity', 'severity_id'],
          SEVERITY_MAP)
    write('lookups/guardrail_action_map.csv',
          ['guardrail_vendor', 'vendor_action', 'guardrail_action', 'action'],
          ACTION_MAP)
