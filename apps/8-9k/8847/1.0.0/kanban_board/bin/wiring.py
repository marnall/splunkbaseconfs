"""
wiring.py — Pure wiring engine for Kanban Board Dashboard Studio dashboards.

No Splunk imports; stdlib only. Fully unit-testable in plain Python.

Public API:
    extract_definition(xml_text)              -> (def_dict, span) or (None, None)
    replace_definition(xml_text, def_dict, span) -> new xml_text
    ensure_wired(def_dict)                    -> (new_def_dict, changed: bool, notes: list[str])

span is a (start, end) tuple of the CDATA content offsets in xml_text, as
returned by extract_definition.  Passing it back to replace_definition lets the
replacement splice exactly those bytes — no re-search, no desync.
"""

import copy
import json
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANON_READ_QUERY = (
    '| makeresults | eval rectype="beat", r=$kb_refresh|s$'
    ' | append [| inputlookup kanban_boards_lookup | eval rectype="board"]'
    ' | append [| inputlookup kanban_cards_lookup | eval rectype="card"]'
    ' | fields - _time'
)

CANON_WRITE_QUERY = '| makeresults | kanbanwrite payload=$kb_cmd|s$'

KANBAN_VIZ_TYPE = 'kanban_board.kanban'

# ---------------------------------------------------------------------------
# extract_definition / replace_definition
# ---------------------------------------------------------------------------

# Matches <definition> ... <![CDATA[ ... ]]> ... </definition>
# Tolerates whitespace between the tag and the CDATA section.
_DEFN_RE = re.compile(
    r'(<definition>)'          # group 1: opening tag
    r'(\s*<!\[CDATA\[)'        # group 2: CDATA open (with optional whitespace)
    r'(.*?)'                   # group 3: CDATA content (non-greedy)
    r'(\]\]>\s*)'              # group 4: CDATA close
    r'(</definition>)',        # group 5: closing tag
    re.DOTALL,
)


def extract_definition(xml_text):
    """
    Find and parse the JSON definition block from a Dashboard Studio XML string.

    Returns:
        (def_dict, span) on success  — span is (start, end) of the CDATA content
                                       (group 3 of _DEFN_RE), suitable for passing
                                       directly to replace_definition
        (None, None)     if not found or JSON is invalid
    """
    m = _DEFN_RE.search(xml_text)
    if not m:
        return None, None
    try:
        def_dict = json.loads(m.group(3))
    except (ValueError, TypeError):
        return None, None
    return def_dict, m.span(3)


def replace_definition(xml_text, def_dict, span):
    """
    Replace the JSON CDATA block in xml_text with a pretty-printed version of def_dict.

    span — (start, end) offsets of the CDATA content as returned by
           extract_definition.  The replacement splices at exactly those offsets,
           so there is no second regex search and no chance of extract/replace
           using different match positions (TOCTOU desync).

    Returns the new xml_text unchanged if span is None.
    """
    if span is None:
        return xml_text

    start, end = span
    new_json = json.dumps(def_dict, indent=2)
    return xml_text[:start] + new_json + xml_text[end:]


# ---------------------------------------------------------------------------
# ensure_wired
# ---------------------------------------------------------------------------

def ensure_wired(def_dict):
    """
    Add kanban write wiring to a dashboard definition dict (additive + idempotent).

    Returns:
        (new_def_dict, changed, notes)
        new_def_dict — a deep copy with modifications applied
        changed      — True if any change was made
        notes        — list of human-readable change descriptions
    """
    d = copy.deepcopy(def_dict)
    notes = []
    changed = False

    # ── 1. Find kanban vizzes ────────────────────────────────────────────────
    vizzes = d.get('visualizations', {})
    kanban_viz_ids = [
        vid for vid, vdata in vizzes.items()
        if isinstance(vdata, dict) and vdata.get('type') == KANBAN_VIZ_TYPE
    ]
    if not kanban_viz_ids:
        return d, False, []

    # ── 2. Resolve / create writer data source ───────────────────────────────
    ds_map = d.setdefault('dataSources', {})

    writer_ds_id = None
    for ds_id, ds_data in ds_map.items():
        if isinstance(ds_data, dict):
            q = ds_data.get('options', {}).get('query', '')
            if 'kanbanwrite' in q:
                writer_ds_id = ds_id
                break

    if writer_ds_id is None:
        writer_ds_id = 'ds_kanban_writer'
        ds_map[writer_ds_id] = {
            'type': 'ds.search',
            'name': 'kanban writer',
            'options': {
                'query': CANON_WRITE_QUERY,
                'queryParameters': {'earliest': '-1m', 'latest': 'now'},
            },
        }
        notes.append('added writer data source ({})'.format(writer_ds_id))
        changed = True

    # ── 3. Wire each kanban viz ──────────────────────────────────────────────
    for viz_id in kanban_viz_ids:
        viz = vizzes[viz_id]

        # --- 3a. Primary data source ---
        viz_ds = viz.setdefault('dataSources', {})
        primary_id = viz_ds.get('primary')

        if primary_id is None:
            # No primary at all — create ds_kanban and bind it
            read_ds_id = 'ds_kanban'
            if read_ds_id not in ds_map:
                ds_map[read_ds_id] = {
                    'type': 'ds.search',
                    'name': 'kanban data',
                    'options': {
                        'query': CANON_READ_QUERY,
                        'queryParameters': {'earliest': '-1m', 'latest': 'now'},
                    },
                }
                notes.append('added read data source ({})'.format(read_ds_id))
                changed = True
            viz_ds['primary'] = read_ds_id
            notes.append('bound primary data source for {}'.format(viz_id))
            changed = True
        else:
            # Primary exists — check/normalize its query
            primary_ds = ds_map.get(primary_id)
            if isinstance(primary_ds, dict):
                existing_query = primary_ds.get('options', {}).get('query', '')
                if '$kb_refresh' not in existing_query:
                    primary_ds.setdefault('options', {})['query'] = CANON_READ_QUERY
                    notes.append('normalized primary query for {}'.format(viz_id))
                    changed = True

        # --- 3b. Write data source binding ---
        if viz_ds.get('write') != writer_ds_id:
            viz_ds['write'] = writer_ds_id
            notes.append('set write data source for {}'.format(viz_id))
            changed = True

        # --- 3c. Event handlers ---
        handlers = viz.setdefault('eventHandlers', [])

        def _has_handler(token_name):
            for h in handlers:
                if not isinstance(h, dict):
                    continue
                if h.get('type') != 'drilldown.setToken':
                    continue
                tokens = h.get('options', {}).get('tokens', [])
                if isinstance(tokens, list) and tokens:
                    if tokens[0].get('token') == token_name:
                        return True
            return False

        for token_name, field_name in [('kb_cmd', 'kb_cmd'), ('kb_refresh', 'kb_refresh')]:
            if not _has_handler(token_name):
                handlers.append({
                    'type': 'drilldown.setToken',
                    'options': {
                        'events': ['any'],
                        'fields': [field_name],
                        'tokens': [{'key': 'value', 'token': token_name}],
                    },
                })
                notes.append('added {} event handler for {}'.format(token_name, viz_id))
                changed = True

        # --- 3d. defaults.tokens.default.kb_refresh ---
        defaults = d.setdefault('defaults', {})
        tokens_block = defaults.setdefault('tokens', {})
        default_block = tokens_block.setdefault('default', {})
        if 'kb_refresh' not in default_block:
            default_block['kb_refresh'] = {'value': '0'}
            notes.append('added defaults.tokens.default.kb_refresh')
            changed = True

    return d, changed, notes
