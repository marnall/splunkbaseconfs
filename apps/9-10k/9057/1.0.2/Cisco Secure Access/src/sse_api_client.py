# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Copyright (c) 2025 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import json
import requests
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2 import TokenExpiredError
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth


# key scopes
policies = "policies"
reports = "reports"
admin = "admin"
deployments = "deployments"
investigate = "investigate"

PUT = "put"
POST = "post"
GET = "get"
DELETE = "delete"
PATCH = "patch"
POST_MULTIPART_FORM_DATA = "post_multipart_form_data"

SSE_AUTH_ENDPOINT = "/auth/v2/token"

# Authorization value is always "Bearer {token}" per OAuth2 Bearer token usage
BEARER_PREFIX = "Bearer "

# All HTTP calls must use a bounded wait (bandit S113).
HTTP_REQUEST_TIMEOUT_SEC = 60

# pdns default and max limit
PDNS_DEFAULT_LIMIT = 1000
PDNS_MAX_LIMIT = 9999


def _encode_filters(filters):
    """Encode filters for query params: dict -> JSON string, else str()."""
    if filters is None:
        return None
    return json.dumps(filters) if isinstance(filters, dict) else str(filters)


# Secure Access API
class SSE_API:
    def __init__(
        self, base_url, client_id, client_secret, auth_header_name="Authorization"
    ):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_header_name = auth_header_name
        self.token = None

    def GetToken(self):
        auth = HTTPBasicAuth(self.client_id, self.client_secret)
        client = BackendApplicationClient(client_id=self.client_id)
        oauth = OAuth2Session(client=client)
        sse_auth_url = f"{self.base_url}{SSE_AUTH_ENDPOINT}"
        token_response = oauth.fetch_token(
            token_url=sse_auth_url,
            auth=auth,
            timeout=HTTP_REQUEST_TIMEOUT_SEC,
        )
        self.token = token_response.get("access_token")
        return self.token

    def Query(
        self,
        scope,
        end_point,
        operation,
        request_data=None,
        files=None,
        encoder=None,
        params=None,
    ):
        success = False
        base_uri = f"{self.base_url.rstrip('/')}/{scope}/v2"
        req = None
        if self.token is None:
            self.GetToken()
        while not success:
            try:
                api_headers = {
                    self.auth_header_name: BEARER_PREFIX + self.token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                if operation in GET:
                    req = requests.get(
                        f"{base_uri}/{end_point}",
                        headers=api_headers,
                        params=params,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                elif operation in PATCH:
                    req = requests.patch(
                        f"{base_uri}/{end_point}",
                        headers=api_headers,
                        json=request_data,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                elif operation in POST:
                    req = requests.post(
                        f"{base_uri}/{end_point}",
                        headers=api_headers,
                        json=request_data,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                elif operation in POST_MULTIPART_FORM_DATA:
                    # Content-Type is multipart/form-data
                    api_headers_multipart_form_data = {
                        self.auth_header_name: BEARER_PREFIX + self.token,
                        "Content-Type": encoder.content_type,
                    }
                    req = requests.post(
                        f"{base_uri}/{end_point}",
                        data=request_data,
                        headers=api_headers_multipart_form_data,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                elif operation in PUT:
                    req = requests.put(
                        f"{base_uri}/{end_point}",
                        headers=api_headers,
                        json=request_data,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                elif operation in DELETE:
                    req = requests.delete(
                        f"{base_uri}/{end_point}",
                        headers=api_headers,
                        json=request_data,
                        timeout=HTTP_REQUEST_TIMEOUT_SEC,
                    )
                req.raise_for_status()
                success = True
            except TokenExpiredError:
                self.GetToken()
            except Exception as e:
                raise (e)
        return req

    def QueryAllPages(
        self,
        scope,
        end_point,
        operation=GET,
        limit=100,
        response_is_array=False,
    ):
        """
        Fetch all pages of a 1-based page-numbered endpoint and return the combined result.

        response_is_array: True when the body is a raw list rather than a
        {data/records, meta} object.
        """
        all_data = []
        page = 1
        total = None
        last_status = None
        last_meta = {}
        while True:
            res = self.Query(
                scope=scope,
                end_point=end_point,
                operation=operation,
                params={"page": page, "limit": limit},
            )
            parsed = self.ParseJsonResponse(res)
            if response_is_array:
                chunk = (
                    parsed
                    if isinstance(parsed, list)
                    else ([parsed] if parsed is not None else [])
                )
                all_data.extend(chunk)
                if len(chunk) < limit:
                    break
                page += 1
                continue
            last_status = parsed.get("status")
            raw_meta = parsed.get("meta") or parsed.get("pageInfo") or {}
            last_meta = raw_meta if isinstance(raw_meta, dict) else {}
            chunk = parsed.get("data") or parsed.get("records") or []
            all_data.extend(chunk)
            total = last_meta.get("total") or last_meta.get("totalNumRecords")
            if total is not None:
                total = int(total)
            limit_val = last_meta.get("limit", limit)
            if isinstance(limit_val, str):
                limit_val = int(limit_val)
            has_more = last_meta.get("hasMoreRecords", True)
            if len(chunk) < limit_val:
                break
            if total is not None and len(all_data) >= total:
                break
            if has_more is False:
                break
            page += 1
        return {
            "status": last_status,
            "meta": {
                **last_meta,
                "page": 1,
                "limit": len(all_data),
                "total": len(all_data) if total is None else total,
            },
            "data": all_data,
        }

    def QueryAllPagesOffset(
        self,
        scope,
        end_point,
        operation=GET,
        limit=100,
        data_key="data",
    ):
        """
        GET all pages of an offset/limit paged endpoint and return the combined result.
        Response shape: { data_key: [...], total: N, offset: ..., limit: ..., ... }.
        """
        all_data = []
        offset = 0
        total = None
        last_response = {}
        while True:
            res = self.Query(
                scope=scope,
                end_point=end_point,
                operation=operation,
                params={"offset": offset, "limit": limit},
            )
            parsed = self.ParseJsonResponse(res)
            last_response = parsed if isinstance(parsed, dict) else {}
            chunk = last_response.get(data_key) or []
            if not isinstance(chunk, list):
                chunk = [chunk] if chunk is not None else []
            all_data.extend(chunk)
            total = last_response.get("total")
            if total is not None:
                total = int(total)
            if total is not None:
                if offset + len(chunk) >= total:
                    break
            elif len(chunk) < limit:
                break
            offset += limit
        return {
            **last_response,
            data_key: all_data,
            "offset": 0,
            "limit": limit,
            "total": total if total is not None else len(all_data),
        }

    def ParseJsonResponse(self, res: requests.Response):
        json_response = res.json()
        return json_response

    def MakeRequest(
        self,
        *,
        method: str,
        endpoint: str,
        headers: dict | None = None,
        query_parameters: dict | None = None,
        query_string: str | None = None,
        body=None,
        timeout: int | None = None,
        verify_ssl: bool = True,
    ) -> requests.Response:
        """Execute an arbitrary Cisco Secure Access API request with asset auth."""
        if self.token is None:
            self.GetToken()

        request_headers = {
            self.auth_header_name: BEARER_PREFIX + self.token,
            "Accept": "application/json",
        }
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)

        request_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if query_string:
            separator = "&" if "?" in request_url else "?"
            request_url = f"{request_url}{separator}{query_string.lstrip('?')}"

        return requests.request(
            method=method.upper(),
            url=request_url,
            headers=request_headers,
            params=query_parameters,
            json=body,
            timeout=timeout or HTTP_REQUEST_TIMEOUT_SEC,
            verify=verify_ssl,
        )

    def ListNetworkDevices(self):
        res = self.Query(scope="deployments", end_point="networkdevices", operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def DeleteNetworkDevice(self, origin_id: int):
        """DELETE deployments/v2/networkdevices/{originId}. Remove a network device."""
        end_point = f"networkdevices/{origin_id}"
        res = self.Query(
            scope="deployments",
            end_point=end_point,
            operation=DELETE,
            request_data=None,
        )
        if res.status_code in (200, 204) and not res.text.strip():
            return {"success": True, "message": "Network device removed"}
        return self.ParseJsonResponse(res)

    def GetNetworkDevice(self, origin_id: int):
        """
        Get a network device by origin ID.
        GET deployments/v2/networkdevices/{originId}. Requires deployments.networkdevices:read.
        See: https://developer.cisco.com/docs/cloud-security/get-network-device/
        """
        end_point = f"networkdevices/{origin_id}"
        res = self.Query(scope="deployments", end_point=end_point, operation=GET)
        return self.ParseJsonResponse(res)

    def ListSites(self):
        """
        List all Sites in the organization.
        GET deployments/v2/sites. Requires deployments.sites:read.
        See: https://developer.cisco.com/docs/cloud-security/list-sites/
        """
        res = self.QueryAllPages(
            scope="deployments",
            end_point="sites",
            operation=GET,
            limit=100,
            response_is_array=True,
        )
        return res["data"]

    def ListVirtualAppliances(self):
        res = self.QueryAllPages(
            scope="deployments",
            end_point="virtualappliances",
            operation=GET,
            limit=100,
            response_is_array=True,
        )
        return res["data"]

    def ListVPNSessions(self):
        res = self.QueryAllPagesOffset(
            scope=admin,
            end_point="vpn/userConnections",
            operation=GET,
            limit=1000,
        )
        data = res["data"]
        return data

    def ListRoamingComputers(self):
        res = self.QueryAllPages(
            scope="deployments",
            end_point="roamingcomputers",
            operation=GET,
            limit=100,
            response_is_array=True,
        )
        return res["data"]

    def GetRoamingComputer(self, device_id):
        """GET deployments/v2/roamingcomputers/{deviceId}. Returns posture/security status for the device."""
        end_point = f"roamingcomputers/{device_id}"
        res = self.Query(scope=deployments, end_point=end_point, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def ListSWGOverrideDeviceSettings(self, origin_ids: list):
        """
        List SWG override device settings for given origin IDs.
        POST deployments/v2/deviceSettings/SWGEnabled/list. Requires deployments.devices.swg:read.
        See: https://developer.cisco.com/docs/cloud-security/list-swg-override-device-settings/
        """
        end_point = "deviceSettings/SWGEnabled/list"
        body = {"originIds": origin_ids}
        res = self.Query(
            scope=deployments, end_point=end_point, operation=POST, request_data=body
        )
        return self.ParseJsonResponse(res)

    def SetSWGOverrideDeviceSettings(self, value: str, origin_ids: list):
        """
        Set SWG override device settings for given origin IDs.
        POST deployments/v2/deviceSettings/SWGEnabled/set. Requires deployments.devices.swg:write.
        See: https://developer.cisco.com/docs/cloud-security/set-swg-override-device-settings/
        """
        end_point = "deviceSettings/SWGEnabled/set"
        body = {"value": value, "originIds": origin_ids}
        res = self.Query(
            scope=deployments, end_point=end_point, operation=POST, request_data=body
        )
        return self.ParseJsonResponse(res)

    def DeleteSWGOverrideDeviceSettings(self, origin_ids: list):
        """
        Remove SWG override device settings for given origin IDs.
        POST deployments/v2/deviceSettings/SWGEnabled/remove. Requires deployments.devices.swg:write.
        See: https://developer.cisco.com/docs/cloud-security/delete-swg-override-device-settings/
        """
        end_point = "deviceSettings/SWGEnabled/remove"
        body = {"originIds": origin_ids}
        res = self.Query(
            scope=deployments, end_point=end_point, operation=POST, request_data=body
        )
        return self.ParseJsonResponse(res)

    def ListDestinationLists(self):
        result = self.QueryAllPages(
            scope=policies, end_point="destinationlists", operation=GET
        )
        return result["data"]

    def CreateDestinationList(self, body: dict):
        """
        Create a destination list in the organization.
        POST policies/v2/destinationlists. Requires policies.destinationLists:write.
        https://developer.cisco.com/docs/cloud-security/create-destination-list/

        Args:
            body: Request object with access, name, bundleTypeId (always 2 per API),
                  isGlobal (always false; global destination lists are not supported on create),
                  and optional destinations (max 500 items).

        Returns:
            Parsed JSON (typically includes status and data with the new list metadata).
        """
        res = self.Query(
            scope=policies,
            end_point="destinationlists",
            operation=POST,
            request_data=body,
        )
        return self.ParseJsonResponse(res)

    def GetDestinationsFromListById(self, destination_list_id):
        end_point_destination_list_id = (
            f"destinationlists/{destination_list_id}/destinations"
        )
        result = self.QueryAllPages(
            scope=policies, end_point=end_point_destination_list_id, operation=GET
        )
        return result["data"]

    def AddToDestinationList(self, destination_list_id, destination, comment=None):
        """
        Add one destination (and optional comment) to a destination list.
        API: POST policies/v2/destinationlists/{destinationListId}/destinations
        https://developer.cisco.com/docs/cloud-security/add-destinations-to-destination-list/

        Args:
            destination_list_id: The unique ID of the destination list.
            destination: Domain, URL, or IP (FQDN max 253 characters).
            comment: Optional comment for the destination.
        Returns:
            Full response dict with "status" and "data" (DestinationListObject).
        """
        end_point = f"destinationlists/{destination_list_id}/destinations"
        obj = {"destination": destination}
        if comment is not None:
            obj["comment"] = comment
        payload = [obj]
        res = self.Query(
            scope=policies, end_point=end_point, operation=POST, request_data=payload
        )
        return self.ParseJsonResponse(res)

    def RemoveDestinationsFromList(self, destination_list_id, destination_ids):
        end_point_destination_list_id = (
            f"destinationlists/{destination_list_id}/destinations/remove"
        )
        destination_remove_object = destination_ids
        res = self.Query(
            scope=policies,
            end_point=end_point_destination_list_id,
            operation=DELETE,
            request_data=destination_remove_object,
        )
        data = self.ParseJsonResponse(res)
        data = data["data"]
        return data

    def GetDomainStatus(self, domain):
        end_point_domain = f"domains/categorization/{domain}?showLabels"
        res = self.Query(scope=investigate, end_point=end_point_domain, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def GetDomainRiskScore(self, domain):
        end_point_domain = f"domains/risk-score/{domain}"
        res = self.Query(scope=investigate, end_point=end_point_domain, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def GetPassiveDNS(self, domain, offset=0, limit=PDNS_DEFAULT_LIMIT):
        """
        Get passive DNS (historical resolution) records for a domain.

        Fetches a single page so the caller controls volume via offset/limit
        instead of walking the whole collection. limit is clamped to
        [1, PDNS_MAX_LIMIT]; ask for PDNS_MAX_LIMIT to retrieve the full
        10000-record-capped set in one request.

        Returns a (records, page_info) tuple, where page_info carries the
        endpoint's offset/limit/totalNumRecords/hasMoreRecords so callers can
        page through results.
        """
        end_point_domain = f"pdns/name/{domain}"
        if not isinstance(limit, int) or limit < 1:
            limit = PDNS_DEFAULT_LIMIT
        limit = min(limit, PDNS_MAX_LIMIT)
        if not isinstance(offset, int) or offset < 0:
            offset = 0
        res = self.Query(
            scope=investigate,
            end_point=end_point_domain,
            operation=GET,
            params={"offset": offset, "limit": limit},
        )
        parsed = self.ParseJsonResponse(res)
        records = parsed.get("records") or parsed.get("data") or []
        page_info = parsed.get("pageInfo") or parsed.get("meta") or {}
        return records, page_info

    def ListIdentities(self, registration_type):
        end_point_identities = f"identities/registrations/{registration_type}"
        res = self.QueryAllPagesOffset(
            scope=deployments,
            end_point=end_point_identities,
            operation=GET,
            limit=250,
        )
        data = res["data"]
        return data

    def UpdateIdentities(self, identity_type, identities_list):
        """PUT identities/registrations/{type}. identity_type: 'device' or 'securityGroupTag'. identities_list: list of dicts (1-250)."""
        end_point = f"identities/registrations/{identity_type}"
        res = self.Query(
            scope=deployments,
            end_point=end_point,
            operation=PUT,
            request_data=identities_list,
        )
        data = self.ParseJsonResponse(res)
        return data

    def ListCertificatesForDevice(self, user_id, device_id):
        """GET ztna/users/{userId}/devices/{deviceId}/certificates (admin/v2). Returns deviceId and certificates list."""
        end_point = f"ztna/users/{user_id}/devices/{device_id}/certificates"
        res = self.Query(scope=admin, end_point=end_point, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def ListCertificatesForUser(self, user_id):
        """GET ztna/users/{userId}/deviceCertificates (admin/v2). Returns userId and devices (each with deviceId, certificates)."""
        end_point = f"ztna/users/{user_id}/deviceCertificates"
        res = self.Query(scope=admin, end_point=end_point, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def ListFirewallRules(self, offset=0, limit=10, rule_name=None, filters=None):
        """
        List access rules in the organization's Access policy.
        GET policies/v2/rules. Requires policies.rules:read.
        See: https://developer.cisco.com/docs/cloud-security/list-rules/
        """
        end_point = "rules"
        params = {"offset": offset, "limit": min(limit, 1000)}
        if rule_name is not None:
            params["ruleName"] = rule_name
        if filters is not None:
            params["filters"] = _encode_filters(filters)
        res = self.Query(
            scope=policies, end_point=end_point, operation=GET, params=params
        )
        data = self.ParseJsonResponse(res)
        return data

    def CreateRule(self, body):
        """
        Create an access rule on the organization's Access policy.
        POST policies/v2/rules. Requires policies.rules:write.
        See: https://developer.cisco.com/docs/cloud-security/create-rule/
        body: dict with ruleName, ruleConditions, ruleAction, ruleSettings (required);
              ruleDescription, rulePriority, ruleIsEnabled (optional).
        """
        end_point = "rules"
        res = self.Query(
            scope=policies, end_point=end_point, operation=POST, request_data=body
        )
        data = self.ParseJsonResponse(res)
        return data

    def ListNetworkTunnelGroups(
        self,
        offset=0,
        limit=10,
        filters=None,
        sort_by="name",
        sort_order="asc",
        include_statuses=False,
    ):
        """
        List Network Tunnel Groups in the organization.
        GET deployments/v2/networktunnelgroups. Requires deployments.networktunnelgroups:read.
        See: https://developer.cisco.com/docs/cloud-security/list-network-tunnel-groups/
        """
        end_point = "networktunnelgroups"
        params = {
            "offset": offset,
            "limit": min(max(1, limit), 200),
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "includeStatuses": "true" if include_statuses else "false",
        }
        if filters is not None:
            params["filters"] = _encode_filters(filters)
        res = self.Query(
            scope=deployments, end_point=end_point, operation=GET, params=params
        )
        data = self.ParseJsonResponse(res)
        return data

    def GetNetworkTunnelGroup(self, ntg_id: int):
        """
        Get a Network Tunnel Group by ID.
        GET deployments/v2/networktunnelgroups/{id}. Requires deployments.networktunnelgroups:read.
        See: https://developer.cisco.com/docs/cloud-security/get-network-tunnel-group/
        """
        end_point = f"networktunnelgroups/{ntg_id}"
        res = self.Query(scope=deployments, end_point=end_point, operation=GET)
        data = self.ParseJsonResponse(res)
        return data

    def ListResourceConnectors(
        self,
        offset=0,
        limit=10,
        filters=None,
        sort_by="originIpAddress",
        sort_order="asc",
    ):
        """
        List Resource Connectors for the organization.
        GET deployments/v2/connectorAgents. Requires deployments.resourceconnectors:read.
        See: https://developer.cisco.com/docs/cloud-security/list-connectors/
        """
        end_point = "connectorAgents"
        params = {
            "offset": offset,
            "limit": min(max(1, limit), 100),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        if filters is not None:
            params["filters"] = _encode_filters(filters)
        res = self.Query(
            scope=deployments, end_point=end_point, operation=GET, params=params
        )
        data = self.ParseJsonResponse(res)
        return data
