import os
import sys
import json
import logging

# Add app's bin directory to path for bundled packages (requests, urllib3)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from splunk.persistconn.application import PersistentServerConnectionApplication

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger('fetch_collections_handler')

HIDDENPASSWORD = '********'


class FetchCollectionsHandler(PersistentServerConnectionApplication):
    """
    Custom REST handler using PersistentServerConnectionApplication pattern.
    1. Receives api_key, platform_base_url, insights_base_url, proxy from POST body
    2. Generates a token via POST {platform_base_url}/api/apikeys/token
    3. Calls GET {insights_base_url}/api/collections?export=true&type=collection-view with Bearer token
    4. Returns the flat list response to the frontend
    """

    def __init__(self, command_line, command_arg):
        super(FetchCollectionsHandler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            logger.info('FetchCollectionsHandler called with method: {}'.format(args.get('method', 'unknown')))
            return self.handle_request(args)

        except Exception as e:
            logger.error('FetchCollectionsHandler handle error: {}'.format(str(e)))
            return self._response(500, {'error': str(e)})

    def _parse_query_params(self, args):
        """Convert Splunk's query_parameters list format to a simple dict.
        Splunk sends: [["key1","val1"],["key2","val2"]] or [{"key1":"val1"}]
        """
        params = {}
        query = args.get('query_parameters', args.get('query', []))

        if isinstance(query, dict):
            return query
        if isinstance(query, list):
            for item in query:
                if isinstance(item, list) and len(item) == 2:
                    params[item[0]] = item[1]
                elif isinstance(item, dict):
                    params.update(item)
        return params

    def _read_api_key_from_storage(self, session_key):
        """Read the real API key from Splunk storage/passwords when UI sends masked value."""
        try:
            import splunklib.client as client
            service = client.connect(token=session_key, app='fpins', owner='nobody')
            for sp in service.storage_passwords.list():
                if sp.username == 'api_key':
                    real_key = sp.clear_password
                    if real_key and real_key not in ['', '__notset__']:
                        logger.info('Found valid API key in storage/passwords')
                        return real_key
        except Exception as e:
            logger.error('Failed to read API key from storage/passwords: {}'.format(str(e)))
        return None

    def _parse_payload(self, args):
        """Parse JSON payload from POST body. Falls back to query params for compatibility."""
        # Try POST body (payload) first
        payload_raw = args.get('payload', '')
        if payload_raw:
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                if isinstance(payload, dict):
                    return payload
            except Exception as e:
                logger.error('Failed to parse JSON payload: {}'.format(str(e)))
        # Fallback to query parameters
        return self._parse_query_params(args)

    def handle_request(self, args):
        try:
            params = self._parse_payload(args)
            logger.info('FetchCollectionsHandler params received: {}'.format(list(params.keys())))

            api_key = params.get('api_key', '')
            platform_base_url = params.get('platform_base_url', '')
            insights_base_url = params.get('insights_base_url', '')
            proxy = params.get('proxy', '')

            # If API key is masked (re-entry), read real key from storage/passwords
            if api_key == HIDDENPASSWORD:
                logger.info('API key is masked, attempting to read from storage/passwords')
                session_key = args.get('session', {}).get('authtoken', '') or args.get('system_authtoken', '')
                if session_key:
                    real_key = self._read_api_key_from_storage(session_key)
                    if real_key:
                        api_key = real_key
                        logger.info('Using API key from storage/passwords (re-entry)')
                    else:
                        return self._response(400, {
                            'error': 'Could not retrieve saved API key. Please re-enter your API Key.'
                        })
                else:
                    return self._response(400, {
                        'error': 'No session token available. Please re-enter your API Key.'
                    })

            if not api_key or not platform_base_url or not insights_base_url:
                return self._response(400, {
                    'error': 'Missing required fields: api_key, platform_base_url, insights_base_url'
                })

            # Build proxies dict (mirrors config.build_proxies_dict in config.py)
            proxies = {'http': proxy, 'https': proxy} if proxy else None

            # Step 1: Generate token
            token_url = 'https://{}/api/apikeys/token'.format(platform_base_url)
            headers = {'X-API-KEY': api_key}
            logger.info('Generating token...')
            token_resp = requests.post(token_url, headers=headers, proxies=proxies, timeout=30)
            token_resp.raise_for_status()
            token = token_resp.json().get('token', '')
            logger.info('Token generated successfully')

            if not token:
                return self._response(400, {'error': 'Token generation returned empty token'})

            # Step 2: Fetch collections
            collections_url = 'https://{}/api/collections?export=true&type=collection-view'.format(insights_base_url)
            auth_headers = {'Authorization': 'Bearer {}'.format(token)}
            logger.info('Fetching collections...')
            coll_resp = requests.get(collections_url, headers=auth_headers, proxies=proxies, timeout=60)
            coll_resp.raise_for_status()
            collections = coll_resp.json()
            logger.info('Collections fetched successfully, count: {}'.format(
                len(collections) if isinstance(collections, list) else 'N/A'))

            # Step 3: Fetch SIEM UI config (which ppCodes to show + export field rules)
            ui_config_url = 'https://{}/api/siemconfiguration/ui'.format(insights_base_url)
            logger.info('Fetching SIEM UI config...')
            ui_resp = requests.get(ui_config_url, headers=auth_headers, proxies=proxies, timeout=30)
            ui_resp.raise_for_status()
            ui_config = ui_resp.json()
            logger.info('SIEM UI config fetched successfully, count: {}'.format(
                len(ui_config) if isinstance(ui_config, list) else 'N/A'))

            # Step 4: Fetch PP Code display names
            ppcode_url = 'https://{}/api/ppcode'.format(insights_base_url)
            logger.info('Fetching PP Code display names...')
            ppcode_resp = requests.get(ppcode_url, headers=auth_headers, proxies=proxies, timeout=30)
            ppcode_resp.raise_for_status()
            ppcodes = ppcode_resp.json()
            logger.info('PP Codes fetched successfully, count: {}'.format(
                len(ppcodes) if isinstance(ppcodes, list) else 'N/A'))

            return self._response(200, {
                'collections': collections,
                'uiConfig': ui_config,
                'ppcodes': ppcodes
            })

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 500
            logger.error('HTTP error fetching collections: {}'.format(str(e)))
            return self._response(status, {
                'error': 'API request failed: {}'.format(str(e)),
                'status': status
            })
        except requests.exceptions.Timeout:
            logger.error('Timeout fetching collections')
            return self._response(504, {'error': 'Request timed out'})
        except Exception as e:
            logger.error('FetchCollectionsHandler error: {}'.format(str(e)))
            return self._response(500, {'error': str(e)})

    def _response(self, status, body):
        return {
            'status': status,
            'payload': json.dumps(body),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
