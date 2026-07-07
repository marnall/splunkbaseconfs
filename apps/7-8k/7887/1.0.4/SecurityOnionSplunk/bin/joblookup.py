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


class joblookup_handler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        try:
            request_info = json.loads(args)

            form_list = request_info.get('form', [])
            form_data = dict(form_list) if form_list else {}

            ncid = form_data.get('ncid', 'not provided')
            uid = form_data.get('uid', 'not provided')
            time = form_data.get('time', 'not provided')

            # Handle empty strings as 'not provided'
            if ncid == '':
                ncid = 'not provided'
            if uid == '':
                uid = 'not provided'
            if time == '':
                time = 'not provided'

            # Validate required parameters - need time and either ncid or uid
            if time == 'not provided':
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Missing required parameter: time',
                        'received_params': {
                            'ncid': ncid,
                            'uid': uid,
                            'time': time
                        }
                    })
                }

            if ncid == 'not provided' and uid == 'not provided':
                return {
                    'status': 400,
                    'payload': json.dumps({
                        'success': False,
                        'error': 'Missing required parameters: either ncid or uid must be provided',
                        'received_params': {
                            'ncid': ncid,
                            'uid': uid,
                            'time': time
                        }
                    })
                }

            # Track if we found community_id via uid lookup
            found_via_uid = False

            # If we only have uid and no ncid, look up the community_id first
            if uid != 'not provided' and ncid == 'not provided':
                try:
                    from query_events import find_community_id_by_uid
                    community_id = find_community_id_by_uid(uid, time)

                    if community_id:
                        ncid = community_id
                        found_via_uid = True
                    else:
                        return {
                            'status': 404,
                            'payload': json.dumps({
                                'success': False,
                                'message': f'No community_id found for uid: {uid}',
                                'uid': uid,
                                'time': time
                            })
                        }
                except Exception as e:
                    return {
                        'status': 500,
                        'payload': json.dumps({
                            'success': False,
                            'error': f'Failed to lookup community_id: {str(e)}',
                            'uid': uid,
                            'time': time
                        })
                    }

            # Get OAuth token and urlbase
            try:
                token_response = auth.get_oauth_token()
                access_token = token_response['access_token']
                urlbase = auth.normalize_urlbase(token_response['urlbase'])

                if not access_token:
                    return {
                        'status': 500,
                        'payload': json.dumps({
                            'success': False,
                            'error': 'Failed to get access token',
                            'token_response': token_response
                        })
                    }

                joblookup_url = f"{urlbase}/connect/joblookup"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                params = {
                    'time': time,
                    'ncid': ncid
                }

                response = requests.get(
                    joblookup_url,
                    headers=headers,
                    params=params,
                    timeout=30,
                    verify=auth.get_cert_path(),
                    allow_redirects=False
                )

                if response.status_code == 302:
                    # Job successfully created - get redirect location (jobid link)
                    location = response.headers.get('Location', '')
                    response_data = {
                        'success': True,
                        'message': 'Job successfully created',
                        'redirect_location': location,
                        'time': time,
                        'ncid': ncid
                    }

                    # Include uid and lookup flag if community_id was found via uid
                    if found_via_uid and uid != 'not provided':
                        response_data['uid'] = uid
                        response_data['found_via_uid'] = True

                    return {
                        'status': 200,
                        'payload': json.dumps(response_data)
                    }
                elif response.status_code == 404:
                    return {
                        'status': 200,
                        'payload': json.dumps({
                            'success': False,
                            'message': 'No document found that matched the provided time and ncid',
                            'time': time,
                            'ncid': ncid
                        })
                    }
                elif response.status_code == 403:
                    return {
                        'status': 200,
                        'payload': json.dumps({
                            'success': False,
                            'error': 'Permission denied',
                            'message': response.text,
                            'time': time,
                            'ncid': ncid
                        })
                    }
                elif response.status_code == 500:
                    return {
                        'status': 500,
                        'payload': json.dumps({
                            'success': False,
                            'error': 'Internal error - review SOC logs',
                            'time': time,
                            'ncid': ncid
                        })
                    }
                else:
                    return {
                        # Not sure, return the first 500 of error response
                        'status': response.status_code,
                        'payload': json.dumps({
                            'success': False,
                            'error': f'Unexpected status code: {response.status_code}',
                            'response_text': response.text[:500],
                            'time': time,
                            'ncid': ncid
                        })
                    }

            except requests.exceptions.RequestException as req_error:
                return {
                    'status': 500,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'API request error: {str(req_error)}',
                        'error_type': 'RequestException',
                        'url': joblookup_url if 'joblookup_url' in locals() else None
                    })
                }
            except Exception as oauth_error:
                return {
                    'status': 500,
                    'payload': json.dumps({
                        'success': False,
                        'error': f'Error: {str(oauth_error)}',
                        'error_type': type(oauth_error).__name__
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
    app.run(joblookup_handler, sys.argv, sys.stdin, sys.stdin.buffer)