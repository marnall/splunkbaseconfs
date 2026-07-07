#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import sys
import os
import re
import json
from pathlib import Path

# Setup path for local libraries
ta_name = 'SecurityOnionSplunk'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

from splunk.persistconn.application import PersistentServerConnectionApplication


class save_cert_handler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        try:
            request_info = json.loads(args)
            form_list = request_info.get('form', [])
            form_data = dict(form_list) if form_list else {}

            cert_content_b64 = form_data.get('cert_content_b64', '')

            if not cert_content_b64:
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Missing required parameter: cert_content_b64'
                    })
                }

            try:
                import base64
                cert_content = base64.b64decode(cert_content_b64).decode('utf-8')
            except Exception as e:
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Failed to decode base64 certificate: {str(e)}'
                    })
                }

            # Validate certificate format
            if not (cert_content.strip().startswith('-----BEGIN CERTIFICATE-----') and
                    cert_content.strip().endswith('-----END CERTIFICATE-----')):
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Invalid certificate format. Must start with -----BEGIN CERTIFICATE----- and end with -----END CERTIFICATE-----'
                    })
                }

            app_dir = os.path.dirname(os.path.dirname(__file__))
            cert_dir = os.path.join(app_dir, 'local', 'certs')
            cert_file = os.path.join(cert_dir, 'SO_CA.crt')

            os.makedirs(cert_dir, exist_ok=True)

            # Write certificate to file
            try:
                with open(cert_file, 'w') as f:
                    f.write(cert_content)

                # Verify file was written
                if os.path.exists(cert_file):
                    return {
                        'status': 200,
                        'payload': json.dumps({
                            'success': True,
                            'message': 'Certificate saved successfully',
                            'cert_path': cert_file
                        })
                    }
                else:
                    return {
                        'status': 500,
                        'payload': json.dumps({
                            'success': False,
                            'error': 'Certificate file was not created'
                        })
                    }

            except IOError as e:
                return {
                    'status': 500,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Failed to write certificate file: {str(e)}'
                    })
                }

        except json.JSONDecodeError as e:
            return {
                'status': 500,
                'payload': json.dumps({
                    'success': False,
                    'error': f'JSON parse error: {str(e)}',
                    'args_type': str(type(args)),
                    'args_sample': str(args[:200]) if isinstance(args, bytes) else str(args)[:200]
                })
            }
        except Exception as e:
            import traceback
            return {
                'status': 500,
                'payload': json.dumps({
                    'success': False,
                    'error': f'Handler error: {str(e)}',
                    'traceback': traceback.format_exc()
                })
            }

    def done(self):
        pass

if __name__ == "__main__":
    import splunk.persistconn.application as app
    app.run(save_cert_handler, sys.argv, sys.stdin, sys.stdin.buffer)