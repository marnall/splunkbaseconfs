# File: box.py
# Copyright (c) 2021-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import json
import random
import string
import time

import jwt
import requests


class Box:
    def __init__(self, client_id, client_secret, public_key, private_key, box_user_id, box_kid):
        self.client_id = client_id
        self.client_secret = client_secret
        self.public_key = public_key
        self.private_key = private_key
        self.box_user_id = box_user_id
        self.box_kid = box_kid

    def _make_rest_call(self, url, params=None, files=None, body=None, headers=None, method="get"):
        request_func = getattr(requests, method)
        if not request_func:
            return {"type": "error", "message": "Unsupported Method"}
        try:
            r = request_func(url, data=body, params=params, headers=headers, files=files)
        except Exception as e:
            return {"type": "error", "message": f"Server Connection Error: {e!s}"}
        else:
            try:
                resp_json = r.json()
            except Exception:
                if not r.text:
                    return {"type": "error", "message": "Oops, something went wrong"}
                else:
                    msg_string = {"type": "error", "message": f"Something went wrong, oops: {r.text}"}
                    return msg_string
            return resp_json

    def _get_auth_token(self):
        exp = time.time() + 30
        random_string = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        claim_raw = {
            "iss": self.client_id,
            "sub": self.box_user_id,
            "box_sub_type": "user",
            "aud": "https://api.box.com/oauth2/token",
            "jti": random_string,
            "exp": int(exp),
        }

        header_raw = {"alg": "RS256", "typ": "JWT", "kid": self.box_kid}

        pem_prefix = "-----BEGIN RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
        pem_suffix = "\n-----END RSA PRIVATE KEY-----"
        private_key = "{}{}{}".format(pem_prefix, self.private_key.replace("\\n", "\n"), pem_suffix)
        signature = jwt.encode(headers=header_raw, payload=claim_raw, key=private_key, algorithm="RS256")
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "assertion": signature,
        }
        token_request_result = self._make_rest_call(url="https://api.box.com/oauth2/token", body=data, method="post")
        try:
            access_token = token_request_result["access_token"]
        except Exception:
            return f"Oops, something went wrong in retrieving access token: {token_request_result!s}"

        return access_token

    def _create_file(self, name, file, parent_id="0"):
        access_token = self._get_auth_token()

        files = {"file": (name, file)}
        body = {"parent_id": parent_id}
        headers = {"Authorization": "Bearer " + str(access_token)}

        result = self._make_rest_call(url="https://upload.box.com/api/2.0/files/content", files=files, body=body, headers=headers, method="post")

        return result

    def _create_folder(self, name, parent_id="0"):
        access_token = self._get_auth_token()

        headers = {"Authorization": "Bearer " + str(access_token)}
        body = json.dumps({"name": name, "parent": {"id": parent_id}})

        result = self._make_rest_call(url="https://api.box.com/2.0/folders", body=body, headers=headers, method="post")

        return result
