import configparser
import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import splunk.rest
from splunk.persistconn.application import PersistentServerConnectionApplication


APP_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR_NAME = os.path.basename(APP_ROOT)


def resolve_splunk_home():
    configured_path = os.environ.get("SPLUNK_HOME")
    if configured_path:
        return os.path.realpath(configured_path)
    return os.path.realpath(os.path.join(APP_ROOT, "..", "..", ".."))


SPLUNK_HOME = resolve_splunk_home()
LOG_DIR = Path(SPLUNK_HOME) / "var" / "log" / APP_DIR_NAME
LOG_PATH = str(LOG_DIR / "oilgas_ai_rest.log")
APPLICATION_JSON = "/".join(("application", "json"))
CONF_STANZA_NAME = "connection"
CONF_FILE_NAME = "ai_chat_settings"
CREDENTIAL_REALM = "oilgas_ai_config"
CREDENTIAL_NAME = "provider_api_key"

LOG_DIR.mkdir(parents=True, exist_ok=True)

try:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s",
        filename=LOG_PATH,
        filemode="a",
    )
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s",
    )

LOGGER = logging.getLogger("oilgas_ai_rest")


def trim_to_string(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8").strip()
        except Exception:
            return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def build_path(*segments):
    normalized_segments = []
    for segment in segments:
        normalized = trim_to_string(segment).strip("/")
        if normalized:
            normalized_segments.append(normalized)
    return "/" + "/".join(normalized_segments)


def quote_path_segment(value):
    return urllib.parse.quote(trim_to_string(value), safe="")


def detect_app_name():
    config = configparser.ConfigParser()
    for candidate in (
        os.path.join(APP_ROOT, "local", "app.conf"),
        os.path.join(APP_ROOT, "default", "app.conf"),
    ):
        if not os.path.exists(candidate):
            continue
        try:
            config.read(candidate)
        except Exception:
            continue
        if config.has_option("package", "id"):
            value = trim_to_string(config.get("package", "id"))
            if value:
                return value
    return os.path.basename(APP_ROOT)


APP_NAME = detect_app_name()


class RestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = int(status)
        self.message = trim_to_string(message) or "Request failed"


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    normalized = trim_to_string(value).lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return default


def parse_int(value, default=None):
    normalized = trim_to_string(value)
    if not normalized:
        return default
    try:
        return int(float(normalized))
    except Exception:
        return default


def parse_float(value, default=None):
    normalized = trim_to_string(value)
    if not normalized:
        return default
    try:
        return float(normalized)
    except Exception:
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def parse_json_object(value, field_name):
    normalized = trim_to_string(value)
    if not normalized:
        return {}
    try:
        parsed = json.loads(normalized)
    except Exception as exc:
        raise RestError(500, "Invalid %s JSON in app configuration: %s" % (field_name, exc))
    if not isinstance(parsed, dict):
        raise RestError(500, "%s must be a JSON object in app configuration." % field_name)
    return parsed


def merge_dicts(base, extra):
    result = {}
    for key, value in (base or {}).items():
        result[key] = value

    for key, value in (extra or {}).items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def stringify_context(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=True)
    except Exception:
        return trim_to_string(value)


def build_effective_system_prompt(system_prompt, context_text):
    prompt_parts = []
    normalized_system = trim_to_string(system_prompt)
    normalized_context = trim_to_string(context_text)

    if normalized_system:
        prompt_parts.append(normalized_system)

    if normalized_context:
        prompt_parts.append(
            "Use the following Splunk dashboard context when it is relevant to the user's question:\n\n"
            + normalized_context
        )

    return "\n\n".join(prompt_parts).strip()


def normalize_history(history):
    if not isinstance(history, list):
        return []

    normalized = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = trim_to_string(item.get("role")).lower()
        if role not in ("user", "assistant"):
            continue
        content = trim_to_string(item.get("content"))
        if not content:
            continue
        normalized.append({
            "role": role,
            "content": content,
        })

    return normalized[-12:]


def normalize_provider_type(value):
    normalized = trim_to_string(value).lower()
    if normalized in ("anthropic", "gemini", "ollama"):
        return normalized
    return "openai_compatible"


def validate_endpoint_url(endpoint_url, provider_type):
    parsed = urllib.parse.urlparse(trim_to_string(endpoint_url))
    if not parsed.scheme or not parsed.netloc:
        raise RestError(400, "Endpoint URL must be an absolute URL.")

    if parsed.scheme == "https":
        return parsed.geturl()

    is_local_ollama = (
        parsed.scheme == "http"
        and provider_type == "ollama"
        and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    )
    if is_local_ollama:
        return parsed.geturl()

    raise RestError(
        400,
        "Endpoint URL must use HTTPS. Plain HTTP is allowed only for local Ollama endpoints on localhost.",
    )


def build_splunkd_url(path):
    base = splunk.rest.makeSplunkdUri()
    if path.startswith("/"):
        return base + path
    return base + "/" + path


def perform_json_request(url, method, headers, payload, timeout_ms, verify_tls):
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url=url, data=body, method=method.upper())
    for key, value in (headers or {}).items():
        if trim_to_string(key) and value is not None:
            request.add_header(str(key), str(value))

    ssl_context = None
    if url.lower().startswith("https://") and not verify_tls:
        ssl_context = ssl._create_unverified_context()

    timeout_seconds = max(3, int(timeout_ms / 1000))

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
            context=ssl_context,
        ) as response:
            raw_body = response.read()
            body_text = raw_body.decode("utf-8", errors="replace") if raw_body else ""
            content_type = trim_to_string(response.headers.get("Content-Type")).lower()
            if APPLICATION_JSON in content_type:
                return json.loads(body_text) if body_text else {}
            if body_text.startswith("{") or body_text.startswith("["):
                try:
                    return json.loads(body_text)
                except Exception:
                    return body_text
            return body_text
    except urllib.error.HTTPError as exc:
        error_text = ""
        try:
            error_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            error_text = trim_to_string(exc.reason)

        parsed_error = None
        if error_text.startswith("{") or error_text.startswith("["):
            try:
                parsed_error = json.loads(error_text)
            except Exception:
                parsed_error = None

        message = extract_error_message(parsed_error) if parsed_error is not None else trim_to_string(error_text)
        if not message:
            message = trim_to_string(exc.reason) or ("HTTP %s" % exc.code)
        raise RestError(exc.code, message)
    except urllib.error.URLError as exc:
        raise RestError(502, "Could not reach the configured AI endpoint: %s" % trim_to_string(exc.reason))


def perform_splunk_get(path, system_token):
    headers = {
        "Authorization": "Splunk " + trim_to_string(system_token),
        "Content-Type": APPLICATION_JSON,
    }
    url = build_splunkd_url(path)
    return perform_json_request(
        url=url,
        method="GET",
        headers=headers,
        payload=None,
        timeout_ms=15000,
        verify_tls=False,
    )


def get_password_entity_path(realm, name):
    entity_name = ":".join((
        quote_path_segment(realm),
        quote_path_segment(name),
        "",
    ))
    return build_path(
        "servicesNS",
        "nobody",
        quote_path_segment(APP_NAME),
        "storage",
        "passwords",
        entity_name,
    )


def load_api_key(system_token):
    try:
        payload = perform_splunk_get(get_password_entity_path(CREDENTIAL_REALM, CREDENTIAL_NAME) + "?output_mode=json", system_token)
    except RestError as exc:
        if exc.status == 404:
            return ""
        raise

    entries = payload.get("entry") if isinstance(payload, dict) else None
    if not entries:
        return ""

    content = entries[0].get("content") if isinstance(entries[0], dict) else {}
    if not isinstance(content, dict):
        return ""
    return trim_to_string(content.get("clear_password") or content.get("password"))


def normalize_connection_settings(content):
    content = content if isinstance(content, dict) else {}
    settings = {
        "provider_type": normalize_provider_type(content.get("provider_type")),
        "endpoint_url": trim_to_string(content.get("endpoint_url")),
        "model": trim_to_string(content.get("model")),
        "auth_mode": trim_to_string(content.get("auth_mode")).lower() or "bearer",
        "auth_header_name": trim_to_string(content.get("auth_header_name")) or "Authorization",
        "auth_header_prefix": "" if content.get("auth_header_prefix") is None else str(content.get("auth_header_prefix")),
        "request_timeout_ms": clamp(parse_int(content.get("request_timeout_ms"), 60000) or 60000, 3000, 180000),
        "verify_tls": parse_bool(content.get("verify_tls"), True),
        "temperature": parse_float(content.get("temperature"), None),
        "max_tokens": parse_int(content.get("max_tokens"), None),
        "extra_headers": parse_json_object(content.get("extra_headers_json"), "extra_headers_json"),
        "extra_params": parse_json_object(content.get("extra_params_json"), "extra_params_json"),
    }

    if not settings["endpoint_url"]:
        raise RestError(500, "Endpoint URL is not configured. Open AI Config and save a provider endpoint.")
    settings["endpoint_url"] = validate_endpoint_url(
        settings["endpoint_url"],
        settings["provider_type"],
    )

    if settings["auth_mode"] not in ("bearer", "header_value", "none"):
        settings["auth_mode"] = "bearer"

    return settings


def load_connection_settings(system_token):
    path = build_path(
        "servicesNS",
        "nobody",
        quote_path_segment(APP_NAME),
        "configs",
        "conf-" + CONF_FILE_NAME,
        CONF_STANZA_NAME,
    ) + "?output_mode=json"

    try:
        payload = perform_splunk_get(path, system_token)
    except RestError as exc:
        if exc.status == 404:
            raise RestError(500, "AI configuration has not been saved yet. Open AI Config and save the provider settings first.")
        raise

    entries = payload.get("entry") if isinstance(payload, dict) else None
    if not entries or not isinstance(entries[0], dict):
        raise RestError(500, "AI configuration is missing. Open AI Config and save the provider settings.")

    content = entries[0].get("content") if isinstance(entries[0].get("content"), dict) else {}
    return normalize_connection_settings(content)


def build_auth_headers(settings, api_key):
    auth_mode = trim_to_string(settings.get("auth_mode")).lower()
    normalized_key = trim_to_string(api_key)
    if auth_mode == "none" or not normalized_key:
        return {}

    header_name = trim_to_string(settings.get("auth_header_name")) or "Authorization"
    header_prefix = settings.get("auth_header_prefix")
    header_prefix = "" if header_prefix is None else str(header_prefix)

    if auth_mode == "bearer" and not header_prefix:
        header_prefix = "Bearer "
    if auth_mode == "bearer" and trim_to_string(header_prefix).lower() == "bearer":
        header_prefix = "Bearer "

    return {
        header_name: header_prefix + normalized_key if header_prefix else normalized_key,
    }


def build_openai_messages(history, current_message, system_prompt):
    messages = []
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt,
        })

    for item in history:
        messages.append({
            "role": item["role"],
            "content": item["content"],
        })

    messages.append({
        "role": "user",
        "content": current_message,
    })
    return messages


def build_openai_payload(settings, message, history, system_prompt):
    payload = {
        "messages": build_openai_messages(history, message, system_prompt),
    }

    if settings.get("model"):
        payload["model"] = settings["model"]
    if settings.get("temperature") is not None:
        payload["temperature"] = settings["temperature"]
    if settings.get("max_tokens") is not None:
        payload["max_tokens"] = settings["max_tokens"]

    return merge_dicts(payload, settings.get("extra_params"))


def build_anthropic_payload(settings, message, history, system_prompt):
    if not settings.get("model"):
        raise RestError(400, "Model is required for the Anthropic protocol.")

    messages = []
    for item in history:
        messages.append({
            "role": item["role"],
            "content": item["content"],
        })
    messages.append({
        "role": "user",
        "content": message,
    })

    payload = {
        "model": settings["model"],
        "messages": messages,
        "max_tokens": settings.get("max_tokens") or 1024,
    }
    if settings.get("temperature") is not None:
        payload["temperature"] = settings["temperature"]
    if system_prompt:
        payload["system"] = system_prompt

    return merge_dicts(payload, settings.get("extra_params"))


def build_gemini_payload(settings, message, history, system_prompt):
    contents = []
    for item in history:
        contents.append({
            "role": "model" if item["role"] == "assistant" else "user",
            "parts": [{"text": item["content"]}],
        })

    contents.append({
        "role": "user",
        "parts": [{"text": message}],
    })

    payload = {
        "contents": contents,
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}],
        }

    generation_config = {}
    if settings.get("temperature") is not None:
        generation_config["temperature"] = settings["temperature"]
    if settings.get("max_tokens") is not None:
        generation_config["maxOutputTokens"] = settings["max_tokens"]
    if generation_config:
        payload["generationConfig"] = generation_config

    return merge_dicts(payload, settings.get("extra_params"))


def build_ollama_payload(settings, message, history, system_prompt):
    if not settings.get("model"):
        raise RestError(400, "Model is required for the Ollama protocol.")

    payload = {
        "model": settings["model"],
        "messages": build_openai_messages(history, message, system_prompt),
        "stream": False,
    }

    options = {}
    if settings.get("temperature") is not None:
        options["temperature"] = settings["temperature"]
    if settings.get("max_tokens") is not None:
        options["num_predict"] = settings["max_tokens"]
    if options:
        payload["options"] = options

    return merge_dicts(payload, settings.get("extra_params"))


def extract_text(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts = []
        for item in value:
            item_text = extract_text(item)
            if item_text:
                parts.append(item_text)
        return "\n".join(parts).strip()

    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return trim_to_string(value.get("text"))
        if isinstance(value.get("content"), str):
            return trim_to_string(value.get("content"))
        if isinstance(value.get("output_text"), str):
            return trim_to_string(value.get("output_text"))
        if isinstance(value.get("response"), str):
            return trim_to_string(value.get("response"))
        if isinstance(value.get("parts"), list):
            return extract_text(value.get("parts"))
        if isinstance(value.get("message"), dict):
            return extract_text(value.get("message"))
        if isinstance(value.get("message"), str):
            return trim_to_string(value.get("message"))
        if isinstance(value.get("content"), list):
            return extract_text(value.get("content"))

    return ""


def extract_error_message(payload):
    if payload is None:
        return ""

    if isinstance(payload, dict):
        error_value = payload.get("error")
        if isinstance(error_value, dict):
            nested = trim_to_string(error_value.get("message") or error_value.get("detail"))
            if nested:
                return nested
        if isinstance(error_value, str):
            return trim_to_string(error_value)

        for key in ("message", "detail", "details", "error_msg"):
            if isinstance(payload.get(key), str):
                return trim_to_string(payload.get(key))

    return extract_text(payload)


def extract_message(payload):
    if isinstance(payload, str):
        return payload.strip()

    if not isinstance(payload, dict):
        return extract_text(payload)

    for field in ("message", "markdown", "answer", "output_text", "text", "response"):
        value = payload.get(field)
        if value:
            extracted = extract_text(value)
            if extracted:
                return extracted

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        for key in ("message", "delta"):
            extracted = extract_text(first_choice.get(key))
            if extracted:
                return extracted
        extracted = extract_text(first_choice.get("text"))
        if extracted:
            return extracted

    content = payload.get("content")
    if isinstance(content, list):
        extracted = extract_text(content)
        if extracted:
            return extracted

    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        first_candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        extracted = extract_text(first_candidate.get("content"))
        if extracted:
            return extracted
        extracted = extract_text(first_candidate.get("output"))
        if extracted:
            return extracted

    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if not isinstance(item, dict):
                continue
            if trim_to_string(item.get("role")).lower() != "assistant":
                continue
            extracted = extract_text(item.get("content"))
            if extracted:
                return extracted

    return extract_text(payload)


def call_provider(settings, api_key, request_payload):
    provider_type = settings["provider_type"]
    message = trim_to_string(request_payload.get("message"))
    if not message:
        raise RestError(400, "Message is required.")

    history = normalize_history(request_payload.get("history"))
    context_text = stringify_context(request_payload.get("context"))
    system_prompt = build_effective_system_prompt(
        request_payload.get("system_prompt"),
        context_text,
    )

    headers = {
        "Content-Type": APPLICATION_JSON,
    }
    headers.update(build_auth_headers(settings, api_key))

    for header_name, header_value in settings.get("extra_headers", {}).items():
        normalized_name = trim_to_string(header_name)
        normalized_value = trim_to_string(header_value)
        if normalized_name and normalized_value:
            headers[normalized_name] = normalized_value

    if provider_type == "anthropic" and "anthropic-version" not in {
        trim_to_string(key).lower() for key in headers.keys()
    }:
        headers["anthropic-version"] = "2023-06-01"

    if provider_type == "anthropic":
        payload = build_anthropic_payload(settings, message, history, system_prompt)
    elif provider_type == "gemini":
        payload = build_gemini_payload(settings, message, history, system_prompt)
    elif provider_type == "ollama":
        payload = build_ollama_payload(settings, message, history, system_prompt)
    else:
        payload = build_openai_payload(settings, message, history, system_prompt)

    try:
        response_payload = perform_json_request(
            url=settings["endpoint_url"],
            method="POST",
            headers=headers,
            payload=payload,
            timeout_ms=settings["request_timeout_ms"],
            verify_tls=settings["verify_tls"],
        )
    except RestError as exc:
        if exc.status == 401:
            raise RestError(
                401,
                "External AI provider returned 401 Unauthorized. Check endpoint URL, auth mode, auth header name/prefix, and stored API key in AI Config. Upstream message: "
                + exc.message,
            )
        if exc.status == 403:
            raise RestError(
                403,
                "External AI provider returned 403 Forbidden. The credentials were accepted but the model or endpoint may not be allowed. Upstream message: "
                + exc.message,
            )
        raise

    message_text = extract_message(response_payload)
    if not message_text:
        raise RestError(502, "The AI provider returned no message content.")

    return {
        "message": message_text,
        "provider": provider_type,
        "model": settings.get("model", ""),
    }


class AiChatRestHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()
        self.command_line = command_line
        self.command_arg = command_arg

    def handleStream(self, handle, in_string):
        return None

    def parse_arg(self, arg):
        try:
            return json.loads(arg)
        except Exception:
            raise RestError(400, "Request payload must be valid JSON.")

    def parse_payload(self, payload):
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return payload
        normalized = trim_to_string(payload)
        if not normalized:
            return {}
        try:
            parsed = json.loads(normalized)
        except Exception:
            raise RestError(400, "Request body must be valid JSON.")
        if not isinstance(parsed, dict):
            raise RestError(400, "Request body must be a JSON object.")
        return parsed

    def resolve_runtime_settings(self, request_payload, system_token):
        mode = trim_to_string(request_payload.get("mode")).lower()
        if mode != "test_connection":
            settings = load_connection_settings(system_token)
            api_key = load_api_key(system_token)
            return settings, api_key

        raw_connection = request_payload.get("connection")
        if not isinstance(raw_connection, dict):
            raise RestError(400, "Test connection requires a connection object.")

        settings = normalize_connection_settings({
            "provider_type": raw_connection.get("provider_type"),
            "endpoint_url": raw_connection.get("endpoint_url"),
            "model": raw_connection.get("model"),
            "auth_mode": raw_connection.get("auth_mode"),
            "auth_header_name": raw_connection.get("auth_header_name"),
            "auth_header_prefix": raw_connection.get("auth_header_prefix"),
            "request_timeout_ms": raw_connection.get("request_timeout_ms"),
            "verify_tls": raw_connection.get("verify_tls"),
            "temperature": raw_connection.get("temperature"),
            "max_tokens": raw_connection.get("max_tokens"),
            "extra_headers_json": json.dumps(raw_connection.get("extra_headers") or {}),
            "extra_params_json": json.dumps(raw_connection.get("extra_params") or {}),
        })

        api_key = trim_to_string(request_payload.get("api_key"))
        use_stored_credential = request_payload.get("use_stored_credential")
        if use_stored_credential is None:
            use_stored_credential = request_payload.get("use_stored_secret")
        if not api_key and parse_bool(use_stored_credential, False):
            api_key = load_api_key(system_token)

        return settings, api_key

    def json_response(self, payload, status):
        return {
            "payload": payload,
            "headers": {
                "Content-Type": APPLICATION_JSON,
            },
            "status": int(status),
        }

    def handle(self, arg):
        try:
            request = self.parse_arg(arg)
            method = trim_to_string(request.get("method")).upper() or "GET"
            if method != "POST":
                return self.json_response({"error": "Only POST is supported for this endpoint."}, 405)

            system_token = trim_to_string(request.get("system_authtoken"))
            if not system_token:
                raise RestError(500, "System auth token was not provided by Splunk.")

            payload = self.parse_payload(request.get("payload"))
            try:
                settings, api_key = self.resolve_runtime_settings(payload, system_token)
            except RestError as exc:
                if exc.status == 401:
                    raise RestError(
                        500,
                        "Splunk could not read the AI configuration or secret with the system auth token."
                    )
                raise

            if settings.get("auth_mode") != "none" and not api_key:
                raise RestError(500, "No API key is stored. Open AI Config and save a secret for the selected provider.")

            LOGGER.info(
                "Dispatching AI request via provider=%s endpoint=%s",
                settings.get("provider_type"),
                settings.get("endpoint_url"),
            )
            runtime_payload = payload
            if trim_to_string(payload.get("mode")).lower() == "test_connection":
                runtime_payload = {
                    "message": "Reply with a very short acknowledgement that the AI connection works.",
                    "history": [],
                    "context": "",
                    "system_prompt": "You are validating connectivity for a Splunk AI integration. Reply in one short sentence."
                }

            response_payload = call_provider(settings, api_key, runtime_payload)
            if trim_to_string(payload.get("mode")).lower() == "test_connection":
                response_payload["test_success"] = True
            return self.json_response(response_payload, 200)
        except RestError as exc:
            LOGGER.warning("AI REST request failed: %s", exc.message)
            return self.json_response({"error": exc.message}, exc.status)
        except Exception:
            LOGGER.exception("Unhandled AI REST error")
            return self.json_response(
                {"error": "Internal server error while processing the AI request."},
                500,
            )
