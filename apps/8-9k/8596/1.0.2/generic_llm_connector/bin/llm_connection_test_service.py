from llm_adapters import build_request, parse_response
from llm_config import load_provider_by_name, resolve_max_tokens
from llm_service import post_json


TEST_CONNECTION_PROMPT = "Reply with OK only."


def test_connection(session_key, payload):
    provider_name = str(payload.get("provider", "") or "").strip()
    if not provider_name:
        raise ValueError("Provider is required for Test Connection.")

    model_name = str(payload.get("model", "") or "").strip()
    if not model_name:
        raise ValueError("Model is required for Test Connection.")

    provider = load_provider_by_name(session_key, provider_name)
    max_tokens = resolve_max_tokens(payload)

    request_dict = build_request(
        provider_type=provider["provider_type"],
        api_endpoint=provider["api_endpoint"],
        api_key=provider["api_key"],
        model=model_name,
        max_tokens=max_tokens,
        prompt=TEST_CONNECTION_PROMPT,
    )
    response_payload = post_json(request_dict)
    parse_response(provider["provider_type"], response_payload)

    return {"status": "ok", "message": "Connection test succeeded."}
