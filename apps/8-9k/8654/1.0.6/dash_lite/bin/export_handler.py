"""
REST handler for exporting a created Splunk app as an .spl file.

Endpoint: /services/dash/export_app
Methods:
  POST  — Package an existing Splunk app into a downloadable .spl file
"""

import os
import sys
import json
import tarfile
import io
import base64

from splunk.persistconn.application import PersistentServerConnectionApplication


class ExportAppHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = args.get('method', 'GET')

            if method == 'POST':
                return self._handle_export(args)
            else:
                return self._error('Method not allowed', 405)
        except Exception as e:
            return self._error('Internal handler error: %s' % str(e), 500)

    def _handle_export(self, args):
        try:
            payload = self._parse_payload(args)
            app_name = (payload.get('app_name') or '').strip()

            if not app_name:
                return self._error('App name is required.', 400)

            # Sanitize — only allow safe characters
            if not all(c.isalnum() or c in ('_', '-') for c in app_name):
                return self._error('Invalid app name.', 400)

            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            app_dir = os.path.join(splunk_home, 'etc', 'apps', app_name)

            if not os.path.isdir(app_dir):
                return self._error('App "%s" not found.' % app_name, 404)

            # Build .tar.gz (which is .spl) in memory
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w:gz') as tar:
                tar.add(app_dir, arcname=app_name)
            buf.seek(0)

            # Return as base64-encoded data (Splunk REST handlers can't stream
            # binary directly, so we encode and let the frontend decode)
            spl_b64 = base64.b64encode(buf.read()).decode('ascii')

            return {
                'payload': json.dumps({
                    'success': True,
                    'app_name': app_name,
                    'spl_data': spl_b64,
                    'filename': app_name + '.spl'
                }),
                'status': 200
            }

        except Exception as e:
            return self._error('Failed to export app: %s' % str(e), 500)

    @staticmethod
    def _parse_payload(args):
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
