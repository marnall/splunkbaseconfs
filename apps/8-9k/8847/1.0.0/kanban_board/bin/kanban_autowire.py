#!/usr/bin/env python3
"""
kanban_autowire — Splunk modular input that auto-wires kanban dashboards.

Runs on a schedule (default 60 s). For each Dashboard Studio dashboard that
contains a kanban_board.kanban panel, it:
  1. Skips dashboards modified more recently than min_quiet_seconds (default 60).
  2. Calls ensure_wired().
  3. If changed, saves the updated dashboard XML via the REST API and writes
     a Splunk event with sourcetype=kanban:autowire.

Never crashes the input — all per-view errors are logged and the input
continues processing the remaining views.
"""

import os
import sys

# Vendor path — kanban_board/lib is sibling of bin
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.insert(0, _LIB)

# Also insert bin on the path so wiring / dashboard_client are importable
_BIN = os.path.dirname(os.path.abspath(__file__))
if _BIN not in sys.path:
    sys.path.insert(0, _BIN)

import splunklib.modularinput as smi

from wiring import extract_definition, replace_definition, ensure_wired
from dashboard_client import list_kanban_views, get_view, save_view, seconds_since_updated


class KanbanAutowireInput(smi.Script):
    """Modular input that automatically adds write wiring to kanban dashboards."""

    def get_scheme(self):
        scheme = smi.Scheme('kanban_autowire')
        scheme.title       = 'Kanban Board dashboard auto-wiring'
        scheme.description = (
            'Automatically adds kanban write wiring (writer data source, '
            'event handlers, token default) to Dashboard Studio dashboards '
            'that contain the Kanban Board visualization.'
        )
        scheme.use_single_instance = False

        arg = smi.Argument('min_quiet_seconds')
        arg.title       = 'Minimum quiet seconds'
        arg.description = (
            'Skip dashboards modified more recently than this many seconds. '
            'Default 60.'
        )
        arg.data_type       = smi.Argument.data_type_number
        arg.required_on_edit    = False
        arg.required_on_create  = False
        scheme.add_argument(arg)

        return scheme

    def validate_input(self, validation_definition):
        # Nothing to validate beyond Splunk's built-in type checks.
        pass

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            try:
                min_quiet = int(float(input_item.get('min_quiet_seconds', 60) or 60))
            except (TypeError, ValueError):
                min_quiet = 60

            # self.service is provided by the splunklib Script base and is
            # already authenticated with the token splunkd injected.
            try:
                views = list_kanban_views(self.service)
            except Exception as exc:
                ew.log(smi.EventWriter.ERROR,
                       'kanban_autowire: could not list kanban views: {}'.format(exc))
                continue

            n_wired = 0
            n_quiet = 0
            n_already = 0

            for view in views:
                name     = view['name']
                app_name = view['app']
                owner    = view['owner']
                xml_text = view['eai_data']
                updated  = view['updated']

                try:
                    # Fast path: steady-state cost control. If the definition
                    # already carries both wiring markers, skip without JSON
                    # parsing or any further REST calls. (A hand-made partial
                    # wiring that includes both markers is left alone; users
                    # can always run `| kanbanwire` for a full pass.)
                    if 'kanbanwrite' in xml_text and 'kb_refresh' in xml_text:
                        n_already += 1
                        continue

                    age = seconds_since_updated(updated)
                    if age < min_quiet:
                        n_quiet += 1
                        continue

                    # Pre-save re-check: re-fetch the view to close the stale-snapshot
                    # window between list_kanban_views and save_view (TOCTOU hardening).
                    fresh = get_view(self.service, app_name, owner, name)
                    if fresh is not None:
                        fresh_age = seconds_since_updated(fresh['updated'])
                        if fresh_age < min_quiet:
                            n_quiet += 1
                            continue
                        # Use the freshly-fetched XML for the extract+wire+save cycle
                        xml_text = fresh['eai_data']

                    def_dict, span = extract_definition(xml_text)
                    if def_dict is None:
                        ew.log(smi.EventWriter.ERROR,
                               'kanban_autowire: could not parse definition for {}'.format(name))
                        continue

                    new_def, ch, notes = ensure_wired(def_dict)
                    if not ch:
                        n_already += 1
                        continue

                    new_xml = replace_definition(xml_text, new_def, span)
                    save_view(self.service, app_name, owner, name, new_xml)

                    n_wired += 1
                    detail = '; '.join(notes)
                    ew.log(smi.EventWriter.INFO,
                           'kanban_autowire: wired {} — {}'.format(name, detail))

                    event = smi.Event(
                        data='dashboard={} app={} notes={}'.format(
                            name, app_name, detail),
                        sourcetype='kanban:autowire',
                        source='kanban_autowire',
                    )
                    ew.write_event(event)

                except Exception as exc:
                    ew.log(smi.EventWriter.ERROR,
                           'kanban_autowire: error processing {}: {}'.format(name, exc))
                    # Continue to next view — never crash the input

            # One summary line per cycle; per-view lines only on change/error.
            if n_wired or n_quiet:
                ew.log(smi.EventWriter.INFO,
                       'kanban_autowire: checked {} kanban view(s): wired {}, already wired {}, deferred (quiet period) {}'.format(
                           len(views), n_wired, n_already, n_quiet))


if __name__ == '__main__':
    sys.exit(KanbanAutowireInput().run(sys.argv))
