from llm_validators import is_truthy


ADDON_NAME = "generic_llm_connector"
DEFAULT_MAX_TOKENS = 1024


def safe_get_all(load_entries, empty_value):
    try:
        return load_entries()
    except Exception as exc:
        error_text = str(exc)
        if "Config file:" in error_text and "does not exist" in error_text:
            return empty_value
        raise


def _credential_realm(conf_name):
    if conf_name == "generic_llm_connector_provider":
        return f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{conf_name}"
    return None


def resolve_max_tokens(connection):
    raw_value = str(connection.get("max_tokens", "") or "").strip()
    if not raw_value:
        return DEFAULT_MAX_TOKENS

    try:
        max_tokens = int(raw_value)
    except ValueError as exc:
        raise ValueError("Max Tokens must be a positive integer.") from exc

    if max_tokens <= 0:
        raise ValueError("Max Tokens must be a positive integer.")

    return max_tokens


def resolve_connection_and_model(connections, requested_connection, requested_model):
    if requested_connection:
        connection = connections.get(requested_connection)
        if not connection:
            raise ValueError(f"Connection '{requested_connection}' was not found.")
    else:
        connection = next(
            (entry for entry in connections.values() if is_truthy(entry.get("is_default"))),
            None,
        )

    if not connection:
        raise ValueError("No default connection is configured.")

    return (
        connection["provider"],
        requested_model or connection["model"],
        connection["name"],
    )


def load_conf_stanzas(session_key, conf_name):
    from solnlib import conf_manager

    manager = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=_credential_realm(conf_name),
    )
    conf = safe_get_all(lambda: manager.get_conf(conf_name), None)
    if conf is None:
        return {}

    return {
        stanza_name: {"name": stanza_name, **stanza}
        for stanza_name, stanza in safe_get_all(conf.get_all, {}).items()
    }


def clear_default_flag(session_key, connection_names):
    """Set ``is_default`` to ``0`` for each named connection stanza."""
    if not connection_names:
        return

    from solnlib import conf_manager

    manager = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=_credential_realm("generic_llm_connector_connection"),
    )
    conf = manager.get_conf("generic_llm_connector_connection")
    for name in connection_names:
        conf.update(name, {"is_default": "0"})


def load_runtime_configuration(session_key, requested_connection, requested_model):
    connections = load_conf_stanzas(session_key, "generic_llm_connector_connection")
    provider_name, model_name, connection_name = resolve_connection_and_model(
        connections=connections,
        requested_connection=requested_connection,
        requested_model=requested_model,
    )
    connection = connections[connection_name]

    provider = load_provider_by_name(session_key, provider_name)

    return {
        "provider_type": provider["provider_type"],
        "api_endpoint": provider["api_endpoint"],
        "api_key": provider["api_key"],
        "model": model_name,
        "max_tokens": resolve_max_tokens(connection),
        "connection_name": connection_name,
    }


def load_provider_by_name(session_key, provider_name):
    providers = load_conf_stanzas(session_key, "generic_llm_connector_provider")
    provider = providers.get(provider_name)
    if not provider:
        raise ValueError(f"Provider '{provider_name}' was not found.")
    return provider
