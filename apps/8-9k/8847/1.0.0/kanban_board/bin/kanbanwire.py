#!/usr/bin/env python3
"""
kanbanwire — Splunk generating command that wires kanban dashboards.

Usage (in a search):
    | kanbanwire [dashboard=<view name>] [app=<app name>]

With no arguments, wires ALL Dashboard Studio dashboards that contain a
kanban_board.kanban panel. The dashboard= and app= options filter by name
and app respectively.

Emits one row per matching view:
    {_time, dashboard, app, changed (true/false), detail}
"""

import os
import sys
import time

# Vendor path — kanban_board/lib is sibling of bin
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.insert(0, _LIB)

# Also insert bin on the path so wiring / dashboard_client are importable
_BIN = os.path.dirname(os.path.abspath(__file__))
if _BIN not in sys.path:
    sys.path.insert(0, _BIN)

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import splunklib.client as client

from wiring import extract_definition, replace_definition, ensure_wired
from dashboard_client import list_kanban_views, save_view


@Configuration(type='events')
class KanbanWireCommand(GeneratingCommand):
    """Add kanban write wiring to Dashboard Studio dashboards containing the Kanban Board visualization."""

    dashboard = Option(require=False, default=None,
                       doc='Filter: only wire dashboards whose name matches this value.')
    app       = Option(require=False, default=None,
                       doc='Filter: only wire dashboards in this Splunk app.')

    def generate(self):
        try:
            si      = self._metadata.searchinfo
            uri     = si.splunkd_uri
            token   = si.session_key

            from urllib.parse import urlparse
            parsed = urlparse(uri)
            scheme = parsed.scheme or 'https'
            host   = parsed.hostname or '127.0.0.1'
            port   = parsed.port or 8089

            # Connect with the user's session so that saves run with their perms
            service = client.connect(
                scheme=scheme,
                host=host,
                port=port,
                splunkToken=token,
            )
        except Exception as exc:
            yield self._row('', '', False, 'error: could not connect to splunkd: {}'.format(exc))
            return

        try:
            views = list_kanban_views(service)
        except Exception as exc:
            yield self._row('', '', False, 'error: could not list kanban views: {}'.format(exc))
            return

        # Apply dashboard= / app= filters
        if self.dashboard:
            views = [v for v in views if v['name'] == self.dashboard]
        if self.app:
            views = [v for v in views if v['app'] == self.app]

        if not views:
            yield self._row('', '', False, 'no matching kanban dashboards found')
            return

        for view in views:
            name     = view['name']
            app_name = view['app']
            owner    = view['owner']
            xml_text = view['eai_data']

            try:
                def_dict, span = extract_definition(xml_text)
                if def_dict is None:
                    yield self._row(name, app_name, False,
                                    'error: could not parse dashboard definition JSON')
                    continue

                new_def, changed, notes = ensure_wired(def_dict)

                if not changed:
                    yield self._row(name, app_name, False, 'already wired')
                    continue

                new_xml = replace_definition(xml_text, new_def, span)
                save_view(service, app_name, owner, name, new_xml)

                detail = '; '.join(notes) if notes else 'wired'
                yield self._row(name, app_name, True, detail)

            except Exception as exc:
                yield self._row(name, app_name, False,
                                'error: {}'.format(exc))

    @staticmethod
    def _row(dashboard, app_name, changed, detail):
        return {
            '_time':     int(time.time()),
            'dashboard': dashboard or '',
            'app':       app_name or '',
            'changed':   'true' if changed else 'false',
            'detail':    detail or '',
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    dispatch(KanbanWireCommand, sys.argv, sys.stdin, sys.stdout, __name__)
