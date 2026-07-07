import urllib.parse
from logging import Logger
from typing import Any
from urllib.parse import quote

from splunk_kv_store_db_services import UserConfiguration
from splunklib.client import Service, connect

APP_NAME = 'cyberark_audit_linux_x86_64'

# Maximum lengths for input validation
MAX_FIELD_LENGTH = 65536
MAX_GENERAL_FIELD_LENGTH = 2048


def create_service_connection(session_key: str, logger: Logger) -> Service:
    """Create and return a Splunk service connection."""
    logger.debug('Creating Splunk service connection')
    return connect(
        token=session_key,
        app=APP_NAME,
        owner='nobody',
    )


def extract_payload(request: dict[str, Any], logger: Logger) -> dict[str, Any]:
    """
    Extract payload from POST body (form) or query parameters.

    Args:
        request: The request dictionary containing form and query data
        logger: Logger instance

    Returns:
        Dictionary containing the merged payload data
    """
    payload = {}

    if not request:
        logger.debug('No request data available')
        return payload

    # Extract and merge form and query data
    _merge_request_data(payload, request, logger)

    # Decode and validate certificate and private key
    _decode_credentials(payload, logger)

    logger.debug(f'Final payload with {len(payload)} keys: {list(payload.keys())}')
    return payload


def _merge_request_data(payload: dict, request: dict, logger: Logger) -> None:
    """Merge form and query data into payload."""
    form_data = request.get('form')
    if form_data and isinstance(form_data, dict):
        logger.debug(f'Using form data with {len(form_data)} keys')
        payload.update(form_data)

    query_data = request.get('query')
    if query_data and isinstance(query_data, dict):
        logger.debug(f'Using query data with {len(query_data)} keys')
        payload.update(query_data)


def _decode_credentials(payload: dict, logger: Logger):
    """URL-decode certificate and private key if present."""
    for key in ['certificate', 'private_key']:
        if key in payload and payload[key]:
            try:
                decoded = urllib.parse.unquote(payload[key])
                if len(decoded) > MAX_FIELD_LENGTH:
                    logger.warning(f'{key} exceeds maximum allowed length')
                    payload[key] = ''
                else:
                    payload[key] = decoded
            except Exception as e:
                logger.warning(f'Failed to decode {key}')
                payload[key] = ''


def reset_app_configuration(service: Service, logger: Logger) -> None:
    """
    Reset app to unconfigured state when all integrations are deleted.

    Args:
        service: Splunk service instance
        logger: Logger instance
    """
    try:
        apps = service.apps
        app = apps[APP_NAME]
        app.update(configured=False)
        logger.info('App marked as unconfigured')
    except Exception as e:
        logger.warning('Failed to reset app configuration')


def _get_proxy_config(kv_store, secrets_manager, logger: Logger) -> dict | None:
    try:
        # Use the dedicated global proxy KV collection
        global_config = kv_store.get_global_proxy_config()

        if not global_config or not global_config.get('proxy_enabled'):
            logger.info('Global proxy is disabled')
            return None

        proxy_host = global_config.get('proxy_host')
        proxy_port = global_config.get('proxy_port')

        if not proxy_host:
            logger.warning('Proxy enabled but no host configured')
            return None

        proxy_username = None
        proxy_password = None
        try:
            proxy_username = secrets_manager.get_secret(f'proxy_username_{APP_NAME}')
            proxy_password = secrets_manager.get_secret(f'proxy_password_{APP_NAME}')
        except Exception:
            logger.info('No proxy credentials found for global proxy')

        proxy_url = f'{proxy_host}:{proxy_port}'
        if proxy_username and proxy_password:
            encoded_user = quote(proxy_username, safe='')
            encoded_pass = quote(proxy_password, safe='')
            proxy_url = f'{encoded_user}:{encoded_pass}@{proxy_url}'
        else:
            logger.info('Proxy username and password not available; using proxy without authentication')

        return {'http': f'http://{proxy_url}', 'https': f'http://{proxy_url}', 'verify': bool(global_config.get('proxy_verify_ssl', True))}

    except Exception as e:
        logger.error(f'Error building global proxy config: {e}', exc_info=True)
        return None
