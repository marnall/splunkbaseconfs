from collections import OrderedDict
from collections.abc import Mapping


def str_to_bool(s):
    return str(s).lower() in ("true", "1", "yes")


def get_nested(data: Mapping, keys: list):
    for key in keys:
        if isinstance(data, Mapping) and key in data:
            data = data[key]
        else:
            return None
    return data


def sanitize_command_option(value):
    if not isinstance(value, str):
        return value
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1].strip()
    return value


def prefix_builder(prefix: str, text: str) -> str:
    return f"{prefix}{text}"


def build_report(fields_prefix: str, mapping: dict, data: dict) -> dict:
    return OrderedDict(
        (prefix_builder(fields_prefix, key), get_nested(data, path))
        for key, path in mapping.items()
    )
