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

import json

from soar_sdk.app import App
from soar_sdk.asset import AssetField
from soar_sdk.asset import BaseAsset
from soar_sdk.exceptions import ActionFailure

from .sse_api_client import SSE_API

# Pagination / validation limits
MAX_LIMIT_NETWORK_TUNNEL_GROUPS = 200
MAX_LIMIT_FIREWALL_RULES = 1000
MAX_LIMIT_RESOURCE_CONNECTORS = 100
MAX_IDENTITIES_UPDATE = 250
MAX_SWG_ORIGIN_IDS = 100
MAX_DESTINATIONS_CREATE_DESTINATION_LIST = 500
_DESTINATION_CREATE_TYPES = frozenset({"domain", "url", "ipv4"})

# Domain status code -> human-readable description
DOMAIN_STATUS_DESCRIPTIONS = {-1: "Malicious", 1: "Benign", 0: "Unclassified"}


def _parse_json_param(value: str, param_name: str, *, allow_list: bool = False):
    """Parse a JSON string; raise ValueError with param_name in message."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"{param_name} must be valid JSON: {e}") from e
    if allow_list and not isinstance(parsed, list):
        raise ValueError(f"{param_name} must be a JSON array")
    return parsed


def _parse_make_request_json_object(value: str | None, param_name: str) -> dict | None:
    """Parse an optional make request JSON object parameter."""
    if value is None or not str(value).strip():
        return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ActionFailure(
            f"Invalid JSON in the {param_name} parameter: {value}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ActionFailure(f"The {param_name} parameter must be a JSON object.")
    return parsed


def _parse_make_request_query_parameters(
    value: str | None,
) -> tuple[dict | None, str | None]:
    """Parse query parameters as a JSON object or pass through a raw query string."""
    if value is None or not str(value).strip():
        return None, None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None, str(value).lstrip("?")
    if not isinstance(parsed, dict):
        raise ActionFailure("The query_parameters parameter must be a JSON object.")
    return parsed, None


def _parse_make_request_body(value: str | None):
    """Parse an optional make request JSON body."""
    if value is None or not str(value).strip():
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ActionFailure(f"Invalid JSON in the body parameter: {value}") from exc


def _parse_optional_filters(params) -> dict | None:
    """Return parsed filters dict from params.filters, or None if missing/empty."""
    raw = getattr(params, "filters", None)
    if not raw or not str(raw).strip():
        return None
    return _parse_json_param(str(raw).strip(), "filters")


def _clamp_offset_limit(params, max_limit: int) -> tuple[int, int]:
    """Return (offset, limit) clamped to valid range; limit capped by max_limit."""
    offset = max(0, params.offset)
    limit = min(max(1, params.limit), max_limit)
    return offset, limit


def _output_from_api_data(OutputModel, data: dict):
    """Build OutputModel instance from API dict, keeping only keys that exist on the model."""
    fields = getattr(OutputModel, "model_fields", None) or getattr(
        OutputModel, "__fields__", {}
    )
    return OutputModel(**{k: data[k] for k in data if k in fields})


def _stringify_item_values(items, value_keys: tuple[str, ...]):
    """
    Coerce selected value fields of a list of dicts to strings.

    Cisco returns rule condition/setting values as JSON strings, booleans, or
    numbers, but the SOAR output schema only allows ``Optional[str]``. Stringify
    the value fields (rendering booleans json-style) so the typed output model
    can parse the response without losing information.
    """
    if not isinstance(items, list):
        return items
    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized_item = dict(item)
            for key in value_keys:
                value = normalized_item.get(key)
                if value is not None and not isinstance(value, str):
                    if isinstance(value, bool):
                        normalized_item[key] = "true" if value else "false"
                    else:
                        normalized_item[key] = str(value)
            normalized.append(normalized_item)
        else:
            normalized.append(item)
    return normalized


def _parse_comma_list(s: str) -> list[str]:
    """Split comma-separated string into non-empty stripped strings."""
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _destinations_for_create_destination_list(
    destinations_json: str | None,
) -> list[dict] | None:
    """
    Parse and validate destinations_json for POST /destinationlists.
    Returns a list suitable for the API body, or None if omitted/blank.
    """
    if destinations_json is None or not str(destinations_json).strip():
        return None
    parsed = _parse_json_param(
        str(destinations_json).strip(), "destinations_json", allow_list=True
    )
    if len(parsed) > MAX_DESTINATIONS_CREATE_DESTINATION_LIST:
        raise ValueError(
            f"destinations_json must contain at most "
            f"{MAX_DESTINATIONS_CREATE_DESTINATION_LIST} destinations"
        )
    out: list[dict] = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"destinations_json[{i}] must be a JSON object")
        dest = item.get("destination")
        typ = item.get("type")
        if dest is None or typ is None:
            raise ValueError(
                f"destinations_json[{i}] must include destination and type fields"
            )
        dest_s = str(dest).strip()
        typ_s = str(typ).strip()
        if not dest_s:
            raise ValueError(f"destinations_json[{i}] destination must be non-empty")
        if typ_s not in _DESTINATION_CREATE_TYPES:
            raise ValueError(
                f"destinations_json[{i}] type must be one of: "
                f"{', '.join(sorted(_DESTINATION_CREATE_TYPES))}"
            )
        row: dict = {"destination": dest_s, "type": typ_s}
        if item.get("comment") is not None:
            row["comment"] = str(item["comment"])
        out.append(row)
    return out


def _normalize_destination_for_match(value: str) -> str:
    return (value or "").strip().lower()


def _find_added_destination_row(
    rows: list,
    *,
    destination: str,
    comment: str | None,
) -> dict | None:
    """
    After POST add, the API returns only list metadata. Match the new row from
    GET destinations by destination string (and comment when unique).
    """
    if not isinstance(rows, list) or not rows:
        return None
    want = _normalize_destination_for_match(destination)
    matches_dest: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _normalize_destination_for_match(str(row.get("destination") or "")) != want:
            continue
        matches_dest.append(row)
    if not matches_dest:
        return None
    if comment is not None:
        with_comment = [r for r in matches_dest if (r.get("comment") or "") == comment]
        if with_comment:
            matches_dest = with_comment

    return sorted(
        matches_dest, key=lambda row: str(row.get("createdAt") or ""), reverse=True
    )[0]


def _parse_origin_ids(s: str, max_count: int = MAX_SWG_ORIGIN_IDS) -> list[int]:
    """Parse comma-separated origin IDs; validate count and integer values."""
    parts = _parse_comma_list(s)
    if len(parts) < 1:
        raise ValueError("origin_ids must contain at least one origin ID")
    if len(parts) > max_count:
        raise ValueError(f"origin_ids must contain at most {max_count} origin IDs")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            raise ValueError(
                f"origin_ids must be comma-separated integers; invalid: {p!r}"
            ) from None
    return result


def flatten_field(obj_list, field_name, separator="."):
    """
    Flatten a nested dict field into top-level keys on each object in the list.
    Modifies obj_list in place. Skips objects that lack field_name or where value is not a dict.
    """
    if not isinstance(obj_list, list):
        return obj_list
    for obj in obj_list:
        if field_name not in obj:
            continue
        if not isinstance(obj[field_name], dict):
            continue
        nested_dict = obj.pop(field_name)
        for key, value in nested_dict.items():
            if key in obj:
                continue
            obj[key] = value
    return obj_list


class Asset(BaseAsset):
    base_url: str = AssetField(default="https://api.sse.cisco.com")
    client_id: str = AssetField(
        sensitive=False, description="Client ID for authentication"
    )
    client_secret: str = AssetField(
        sensitive=True, description="Client Secret key for authentication"
    )
    auth_header_name: str = AssetField(
        default="Authorization",
        description="HTTP header name for the Bearer token (value is always sent as 'Bearer {token}')",
    )
    default_destination_list_id: str = AssetField(
        description="Default destination list ID to use for automated domain/URL blocking",
        required=False,
    )

    def get_client(self) -> SSE_API:
        return SSE_API(
            self.base_url,
            self.client_id,
            self.client_secret,
            auth_header_name=self.auth_header_name,
        )


app = App(
    name="Cisco Secure Access",
    app_type="information",
    logo="logo.svg",
    logo_dark="logo_dark.svg",
    product_vendor="Cisco",
    product_name="Cisco Secure Access",
    publisher="Splunk",
    appid="48ce45b2-0de5-474f-be52-8266350325cd",
    fips_compliant=False,
    asset_cls=Asset,
)


def test_connectivity(asset: Asset) -> None:
    """
    Test connectivity against the Cisco Secure Access API.
    Get a token to ensure connectivity, and valid configuration.
    https://developer.cisco.com/docs/cloud-security/create-authorization-token/
    """
    client = asset.get_client()
    if not client.GetToken():
        raise Exception("Unable to get auth token")
