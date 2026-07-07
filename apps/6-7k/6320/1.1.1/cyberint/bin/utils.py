from typing import Any
from urllib.parse import urlparse


def remove_empty_elements(value: Any) -> Any:

    def empty(x: Any) -> bool:
        return x is None or x == {} or x == []

    if isinstance(value, dict):
        return {
            k: v for k, v in ((k, remove_empty_elements(v))
                              for k, v in value.items()) if not empty(v)
        }
    if isinstance(value, list):
        return [v for v in (remove_empty_elements(v) for v in value) if not empty(v)]
    return value


def validate_url(url: str):
    parsed_url = urlparse(url)
    if parsed_url.scheme != 'https':
        raise ValueError(f'URL Scheme must be https (got {parsed_url.scheme})')
    if not parsed_url.netloc:
        raise ValueError(f'Missing network location on url {url}')
