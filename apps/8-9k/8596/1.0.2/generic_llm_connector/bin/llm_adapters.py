ANTHROPIC_VERSION = "2023-06-01"


def build_request(provider_type, api_endpoint, api_key, model, max_tokens, prompt):
    if provider_type == "OpenAI-compatible":
        return {
            "url": api_endpoint,
            "headers": {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            "json": {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            },
        }

    if provider_type == "Anthropic-compatible":
        return {
            "url": api_endpoint,
            "headers": {
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            "json": {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            },
        }

    raise ValueError(f"Unsupported provider type '{provider_type}'.")


def parse_response(provider_type, payload):
    if provider_type == "OpenAI-compatible":
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Malformed OpenAI-compatible response payload.") from exc

    if provider_type == "Anthropic-compatible":
        try:
            for block in payload["content"]:
                if block.get("type") == "text":
                    return block["text"]
        except (KeyError, TypeError) as exc:
            raise ValueError("Malformed Anthropic-compatible response payload.") from exc
        raise ValueError("Anthropic-compatible response did not contain a text block.")

    raise ValueError(f"Unsupported provider type '{provider_type}'.")
