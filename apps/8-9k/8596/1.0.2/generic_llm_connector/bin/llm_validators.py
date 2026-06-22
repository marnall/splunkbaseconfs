def is_truthy(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


def ensure_provider_not_in_use(provider_name, connection_entries):
    for entry in connection_entries:
        if entry.get("provider") == provider_name:
            raise ValueError(
                f"Provider '{provider_name}' cannot be deleted while connections reference it."
            )


def find_existing_default_connections(payload, connection_entries, current_name=None):
    """Return names of other connections currently marked as default.

    If the incoming *payload* does not set ``is_default``, no conflict is
    possible and an empty list is returned.  Otherwise, every connection
    whose ``is_default`` flag is truthy — except the one being saved
    (*current_name*) — is included so the caller can clear those flags
    before persisting.
    """
    if not is_truthy(payload.get("is_default")):
        return []

    return [
        entry["name"]
        for entry in connection_entries
        if entry.get("name") != current_name and is_truthy(entry.get("is_default"))
    ]
