from constants import NA


def is_valid_value(value):
    """Check if the field value is valid (not 'N/A' or empty)."""
    value = value.strip() if value else ''
    return value not in ('', "''", NA)


def get_valid_entity_identifier(entity_key, entity_title):
    """Determines and returns the first valid entity identifier if found,
      otherwise None if neither is valid."""
    for identifier in (entity_key, entity_title):
        if is_valid_value(identifier):
            return identifier
    return None
