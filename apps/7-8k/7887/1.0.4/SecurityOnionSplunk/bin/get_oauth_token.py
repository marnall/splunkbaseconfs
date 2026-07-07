#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import sys
import os
import base64
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ta_name = 'SecurityOnionSplunk'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

import requests

sys.path.insert(0, str(Path(__file__).parent))
from setup_auth import get_credentials


def normalize_urlbase(urlbase):
    if not isinstance(urlbase, str):
        raise RuntimeError("Invalid URL base: expected a string")

    normalized_urlbase = urlbase.strip()
    if not normalized_urlbase:
        raise RuntimeError("Invalid URL base: value is empty")

    parsed_urlbase = urlsplit(normalized_urlbase)

    if parsed_urlbase.scheme.lower() != 'https':
        raise RuntimeError("Invalid URL base: only https URLs are allowed")

    if not parsed_urlbase.netloc:
        raise RuntimeError("Invalid URL base: hostname is required")

    if parsed_urlbase.query or parsed_urlbase.fragment:
        raise RuntimeError("Invalid URL base: query strings and fragments are not allowed")

    if parsed_urlbase.path not in ('', '/'):
        raise RuntimeError("Invalid URL base: path is not allowed")

    return urlunsplit(('https', parsed_urlbase.netloc, '', '', ''))

def get_cert_path():
    app_dir = os.path.dirname(os.path.dirname(__file__))
    cert_file = os.path.join(app_dir, 'local', 'certs', 'SO_CA.crt')

    if os.path.exists(cert_file):
        return cert_file
    else:
        raise FileNotFoundError(f"CA certificate not found at {cert_file}. Please configure the app with a CA certificate.")

def get_oauth_token():
    try:
        credentials = get_credentials()
        client_id = credentials['client_id']
        client_secret = credentials['client_secret']
        raw_urlbase = credentials['urlbase']
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve credentials: {e}")

    urlbase = normalize_urlbase(raw_urlbase)

    oauth_url = f"{urlbase}/oauth2/token"

    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials'
    }

    try:
        response = requests.post(oauth_url, headers=headers, data=data, timeout=30, verify=get_cert_path())
        response.raise_for_status()

        # Get the token response
        token_data = response.json()

        # Add urlbase to the response
        token_data['urlbase'] = urlbase

        return token_data
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to get OAuth token: {e}")
