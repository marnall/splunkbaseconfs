"""
REST handler for creating styled Splunk apps from DASH builder configurations.

Endpoint: POST /services/dash/create_app
Requires: admin or sc_admin role
"""

import os
import sys
import json
import shutil

# Ensure the app's bin/ directory is on sys.path so sibling modules can be found
# by Splunk's persistent connection process.
_bin_dir = os.path.dirname(os.path.abspath(__file__))
if _bin_dir not in sys.path:
    sys.path.insert(0, _bin_dir)

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

# Safe import — if this fails at module level, the entire handler class
# would fail to load, corrupting Splunk's persistent connection protocol.
try:
    import app_builder
except Exception:
    app_builder = None


class CreateAppHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        """Route incoming requests. Wrapped in try/except to prevent
        uncaught exceptions from corrupting the persistent connection
        protocol stream (which causes 'bad character in reply size')."""
        try:
            args = json.loads(in_string)
            method = args.get('method', 'GET')

            if method == 'POST':
                return self.handle_create(args)
            else:
                return {
                    'payload': json.dumps({'error': 'Method not allowed'}),
                    'status': 405
                }
        except Exception as e:
            return {
                'payload': json.dumps({
                    'error': 'Internal handler error: %s' % str(e)
                }),
                'status': 500
            }

    # ------------------------------------------------------------------ #
    #  Main creation logic                                                #
    # ------------------------------------------------------------------ #

    def handle_create(self, args):
        try:
            # Lazy import fallback if module-level import failed
            global app_builder
            if app_builder is None:
                try:
                    import app_builder as _ab
                    app_builder = _ab
                except Exception as ie:
                    return self._error(
                        'Could not load app builder module: %s. '
                        'Please restart Splunk.' % str(ie), 500
                    )

            # Ensure use case definitions are available
            try:
                use_cases = app_builder.get_use_cases()
            except Exception as ie:
                return self._error(
                    'Could not load use case definitions: %s. '
                    'Please restart Splunk.' % str(ie), 500
                )

            payload = self._parse_payload(args)
            session_key = args['session']['authtoken']

            app_title = (payload.get('app_title') or '').strip()
            if not app_title:
                return self._error('App title is required.', 400)

            app_name = app_builder.sanitize_app_name(app_title)
            if len(app_name) < 2:
                return self._error('App title must produce a valid folder name (at least 2 characters).', 400)

            styles = payload.get('styles', {})
            if not styles:
                return self._error('Style data is required.', 400)

            logo_data = payload.get('logo_data')
            logo_36 = payload.get('logo_36')
            logo_72 = payload.get('logo_72')
            background_data = payload.get('background_data')
            graph_colors = payload.get('graph_color_scheme', 'greyscale')
            use_case = payload.get('use_case', 'cybersecurity')
            selected_dashboards = payload.get('selected_dashboards')
            query_type = payload.get('query_type', 'sample')
            cim_queries = payload.get('cim_queries')

            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            app_dir = os.path.join(splunk_home, 'etc', 'apps', app_name)

            if os.path.exists(app_dir):
                return self._error(
                    'An app with the name "%s" already exists.' % app_name, 409
                )

            # Build the app — clean up on any failure
            try:
                app_builder.create_app_structure(
                    app_dir, app_title, app_name,
                    styles, logo_data, logo_36, logo_72,
                    background_data, graph_colors, use_case,
                    selected_dashboards,
                    query_type=query_type,
                    cim_queries=cim_queries
                )
            except Exception:
                if os.path.exists(app_dir):
                    shutil.rmtree(app_dir, ignore_errors=True)
                raise

            # Reload apps so the new app is visible immediately
            try:
                rest.simpleRequest(
                    '/services/apps/local/_reload',
                    sessionKey=session_key,
                    method='POST'
                )
            except Exception:
                pass  # Non-critical — user can reload manually

            # URL points to the first dashboard in the created app
            use_case_data = use_cases.get(use_case, {})
            dashboards = use_case_data.get('dashboards', [])
            if selected_dashboards:
                selected = [d for d in dashboards if d['id'] in selected_dashboards]
                first_dash_id = selected[0]['id'] if selected else (dashboards[0]['id'] if dashboards else 'overview')
            else:
                first_dash_id = dashboards[0]['id'] if dashboards else 'overview'
            app_url = '/app/%s/%s' % (app_name, first_dash_id)

            return {
                'payload': json.dumps({
                    'success': True,
                    'app_name': app_name,
                    'app_url': app_url,
                    'message': 'App "%s" created successfully.' % app_title
                }),
                'status': 200
            }

        except Exception as e:
            return self._error('Failed to create app: %s' % str(e), 500)

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def sanitize_app_name(title):
        return app_builder.sanitize_app_name(title)

    @staticmethod
    def _parse_payload(args):
        """Extract JSON payload from the PersistentServerConnectionApplication args."""
        payload = args.get('payload', '{}')
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    @staticmethod
    def _error(message, status=500):
        return {
            'payload': json.dumps({'error': message}),
            'status': status
        }
