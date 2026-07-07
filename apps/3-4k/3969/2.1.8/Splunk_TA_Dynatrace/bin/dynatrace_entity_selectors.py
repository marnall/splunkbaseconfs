import re
from typing import Any, Callable, List


ENTITY_SELECTOR_FIELD = "dynatrace_entity_selectors_v2_textarea"

_ENTITY_SELECTOR_DELIMITERS = re.compile(r"[,\r\n]+")


def _entity_selector_parts(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [
            entity_type.strip()
            for entity_type in _ENTITY_SELECTOR_DELIMITERS.split(value)
            if entity_type.strip()
        ]

    if isinstance(value, (list, tuple, set)):
        return [
            entity_type
            for raw_entity_type in value
            for entity_type in _entity_selector_parts(raw_entity_type)
        ]

    entity_type = str(value).strip()
    return [entity_type] if entity_type else []


def select_entity_types(value: Any) -> List[str]:
    return _entity_selector_parts(value)


def _get_optional_arg(get_arg: Callable[[str], Any], field: str) -> Any:
    try:
        return get_arg(field)
    except (AttributeError, KeyError):
        return None


def get_selected_entity_types(helper: Any) -> List[str]:
    # Compatibility for a customer with a divergent source that stored API v2
    # entity selectors under this textarea-style key.
    return select_entity_types(_get_optional_arg(helper.get_arg, ENTITY_SELECTOR_FIELD))
