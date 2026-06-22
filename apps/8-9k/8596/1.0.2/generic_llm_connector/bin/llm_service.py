import json
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from llm_adapters import build_request, parse_response
from llm_config import load_runtime_configuration


def _decode_json_bytes(raw_bytes):
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _error_message_from_payload(payload):
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])

        if payload.get("message"):
            return str(payload["message"])

    return None


def post_json(request_dict):
    payload = json.dumps(request_dict["json"]).encode("utf-8")
    request = urllib_request.Request(
        request_dict["url"],
        data=payload,
        headers=request_dict["headers"],
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            response_payload = _decode_json_bytes(response.read())
    except HTTPError as exc:
        error_payload = _decode_json_bytes(exc.read())
        error_message = (
            _error_message_from_payload(error_payload) or exc.reason or exc.msg
        )
        raise ValueError(
            f"LLM request failed with HTTP {exc.code}: {error_message}"
        ) from exc
    except URLError as exc:
        reason = exc.reason if isinstance(exc.reason, str) else str(exc.reason)
        raise ValueError(
            f"LLM request failed to reach provider endpoint: {reason}"
        ) from exc

    if response_payload is None:
        raise ValueError("LLM provider returned a non-JSON response.")

    return response_payload


def invoke_llm(session_key, prompt, requested_connection, requested_model):
    runtime = load_runtime_configuration(
        session_key=session_key,
        requested_connection=requested_connection,
        requested_model=requested_model,
    )
    request_dict = build_request(
        provider_type=runtime["provider_type"],
        api_endpoint=runtime["api_endpoint"],
        api_key=runtime["api_key"],
        model=runtime["model"],
        max_tokens=runtime["max_tokens"],
        prompt=prompt,
    )
    try:
        response_payload = post_json(request_dict)
        return parse_response(runtime["provider_type"], response_payload)
    except ValueError as exc:
        raise ValueError(
            f"Connection '{runtime['connection_name']}' failed: {exc}"
        ) from exc
