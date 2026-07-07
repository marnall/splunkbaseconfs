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

import requests
sys.path.insert(0, str(Path(__file__).parent))
import get_oauth_token as auth
from splunk.persistconn.application import PersistentServerConnectionApplication


class pcapjobs_handler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        try:
            request_info = json.loads(args)
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

                jobs_url = f"{urlbase}/connect/jobs"
                headers = {
                    'Authorization': f'Bearer {access_token}'
                }
                params = {
                    'kind': ''
                }

                response = requests.get(
                    jobs_url,
                    headers=headers,
                    params=params,
                    timeout=30,
                    verify=auth.get_cert_path()
                )

                if response.status_code == 200:
                    jobs_data = response.json()

                    # Sort jobs by ID descending to get most recent first
                    if isinstance(jobs_data, list):
                        jobs_data.sort(key=lambda x: x.get('id', 0), reverse=True)
                        # Return only the 10 most recent jobs
                        recent_jobs = jobs_data[:10]
                    else:
                        recent_jobs = jobs_data

                    return {
                        'status': 200,
                        'payload': json.dumps({
                            'success': True,
                            'jobs': recent_jobs
                        })
                    }
                else:
                    return {
                        'status': response.status_code,
                        'payload': json.dumps({
                            'success': False,
                            'error': f'Failed to fetch jobs: HTTP {response.status_code}',
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
    app.run(pcapjobs_handler, sys.argv, sys.stdin, sys.stdin.buffer)