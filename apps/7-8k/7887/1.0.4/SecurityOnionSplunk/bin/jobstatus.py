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
ta_name = 'securityonion'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

import requests
sys.path.insert(0, str(Path(__file__).parent))
import get_oauth_token as auth
from splunk.persistconn.application import PersistentServerConnectionApplication


class jobstatus_handler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        try:
            request_info = json.loads(args)

            # Extract job ID from the path
            rest_path = request_info.get('rest_path', '')

            job_id_match = re.search(r'/jobstatus/(\d+)', rest_path)

            if not job_id_match:
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': 'No job ID provided in path',
                        'rest_path': rest_path,
                        'request_keys': list(request_info.keys())
                    })
                }

            job_id = job_id_match.group(1)

            try:
                token_response = auth.get_oauth_token()
                access_token = token_response['access_token']
                urlbase = auth.normalize_urlbase(token_response['urlbase'])

                if not access_token:
                    return {
                        'status': 500,
                        'payload': json.dumps({
                            'success': False,
                            'error': 'Failed to get access token'
                        })
                    }

                job_status_url = f"{urlbase}/connect/job/{job_id}"
                headers = {
                    'Authorization': f'Bearer {access_token}'
                }

                response = requests.get(
                    job_status_url,
                    headers=headers,
                    timeout=30,
                    verify=auth.get_cert_path()
                )

                if response.status_code == 200:
                    job_data = response.json()
                    return {
                        'status': 200,
                        'payload': json.dumps({
                            'success': True,
                            'jobId': job_id,
                            'completeTime': job_data.get('completeTime'),
                            'status': job_data.get('status'),
                            'data': job_data
                        })
                    }
                elif response.status_code == 404:
                    return {
                        'status': 404,
                        'payload': json.dumps({
                            'success': False,
                            'error': f'Job {job_id} not found'
                        })
                    }
                else:
                    return {
                        'status': response.status_code,
                        'payload': json.dumps({
                            'success': False,
                            'error': f'Unexpected status code: {response.status_code}',
                            'response_text': response.text[:500]
                        })
                    }

            except requests.exceptions.RequestException as req_error:
                return {
                    'status': 500,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'API request error: {str(req_error)}'
                    })
                }
            except Exception as e:
                return {
                    'status': 500,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Error: {str(e)}'
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
    app.run(jobstatus_handler, sys.argv, sys.stdin, sys.stdin.buffer)