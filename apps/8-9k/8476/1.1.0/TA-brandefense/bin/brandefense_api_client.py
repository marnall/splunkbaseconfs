"""
Brandefense API Client for Splunk TA
Shared module for all Brandefense input scripts.
Uses only stdlib (urllib) - no external dependencies needed.
"""

import json
import os
import sys
import ssl
import time
import logging
import configparser
from urllib.request import Request, urlopen, build_opener, ProxyHandler, HTTPSHandler
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError


def setup_logging(name):
    """Set up logging that writes to stderr (Splunk captures stderr as internal logs)."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s level=%(levelname)s name=%(name)s %(message)s'
        ))
        logger.addHandler(handler)
    return logger


class CheckpointManager:
    """Manages checkpoint files for tracking last processed records."""

    def __init__(self, input_name, app_dir=None):
        if app_dir is None:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.checkpoint_dir = os.path.join(app_dir, 'checkpoint')
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.checkpoint_file = os.path.join(self.checkpoint_dir, f'{input_name}.json')
        self._data = self._load()

    def _load(self):
        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def save(self):
        tmp_file = self.checkpoint_file + '.tmp'
        with open(tmp_file, 'w') as f:
            json.dump(self._data, f)
        os.replace(tmp_file, self.checkpoint_file)


class BrandefenseAPIClient:
    """API client for Brandefense API v1."""

    BASE_URL = "https://api.brandefense.io/api/v1"

    def __init__(self, api_key, base_url=None, logger=None, request_delay=1,
                 proxy_config=None, ssl_verify=False):
        self.api_key = api_key
        self.base_url = (base_url or self.BASE_URL).rstrip('/')
        self.logger = logger or setup_logging('brandefense_api')
        self.request_delay = float(request_delay)

        if ssl_verify:
            self.ssl_context = ssl.create_default_context()
        else:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        self._opener = self._build_opener(proxy_config)

    def _build_opener(self, proxy_config):
        """Build a URL opener with optional proxy and SSL context."""
        handlers = [HTTPSHandler(context=self.ssl_context)]

        if proxy_config:
            host = proxy_config['host']
            port = proxy_config.get('port', '')
            username = proxy_config.get('username', '')
            password = proxy_config.get('password', '')

            if username:
                userinfo = f"{quote(username, safe='')}:{quote(password, safe='')}@"
            else:
                userinfo = ''

            port_part = f":{port}" if port else ''
            proxy_url = f"http://{userinfo}{host}{port_part}"

            handlers.append(ProxyHandler({
                'http': proxy_url,
                'https': proxy_url,
            }))
            self.logger.info(f"Using proxy: {host}{port_part}")
        else:
            # Empty ProxyHandler prevents env var proxy leakage
            handlers.append(ProxyHandler({}))

        return build_opener(*handlers)

    def _make_request(self, url, max_retries=3, retry_delay=5):
        """Make an HTTP GET request with retry logic for rate limits and transient errors."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        for attempt in range(max_retries):
            try:
                req = Request(url, headers=headers, method='GET')
                response = self._opener.open(req, timeout=60)
                data = json.loads(response.read().decode('utf-8'))
                return data
            except HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                if e.code == 429:
                    retry_after = int(e.headers.get('Retry-After', retry_delay * (attempt + 1)))
                    self.logger.warning(f"Rate limited (429), waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    continue
                elif e.code in (500, 502, 503, 504):
                    wait = retry_delay * (attempt + 1)
                    self.logger.warning(f"Server error {e.code}, attempt {attempt+1}/{max_retries}, waiting {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    self.logger.error(f"HTTP {e.code}: {body}")
                    raise
            except URLError as e:
                wait = retry_delay * (attempt + 1)
                self.logger.warning(f"URL error: {e.reason}, attempt {attempt+1}/{max_retries}, waiting {wait}s")
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                raise
            except Exception as e:
                wait = retry_delay * (attempt + 1)
                self.logger.error(f"Request failed: {e}, attempt {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                raise

        return None

    def get(self, endpoint, params=None):
        """Make a single GET request to the API."""
        url = f"{self.base_url}{endpoint}"
        if params:
            params = {k: str(v) for k, v in params.items() if v is not None}
            url = f"{url}?{urlencode(params)}"
        return self._make_request(url)

    def get_paginated_cursor(self, endpoint, params=None, stop_fn=None, max_pages=None):
        """
        Paginate using cursor/page-based pagination (audit logs, incidents, intelligences).
        Follows the 'next' URL until null or stop_fn returns True.
        Yields individual result items.
        """
        page_count = 0

        # Build initial URL
        url = f"{self.base_url}{endpoint}"
        if params:
            clean = {k: str(v) for k, v in params.items() if v is not None}
            url = f"{url}?{urlencode(clean)}"

        while url:
            if max_pages and page_count >= max_pages:
                self.logger.info(f"Reached max pages limit ({max_pages})")
                break

            data = self._make_request(url)
            if not data or 'results' not in data:
                break

            results = data['results']
            if not results:
                break

            should_stop = False
            for item in results:
                if stop_fn and stop_fn(item):
                    should_stop = True
                    break
                yield item

            if should_stop:
                break

            url = data.get('next')
            page_count += 1
            time.sleep(self.request_delay)

    def get_paginated_search_after(self, endpoint, params=None, stop_fn=None, max_pages=None):
        """
        Paginate using search_after pagination (IOCs).
        Yields individual result items.
        """
        page_count = 0
        base_params = dict(params) if params else {}

        while True:
            if max_pages and page_count >= max_pages:
                self.logger.info(f"Reached max pages limit ({max_pages})")
                break

            url = f"{self.base_url}{endpoint}"
            clean = {k: str(v) for k, v in base_params.items() if v is not None}
            if clean:
                url = f"{url}?{urlencode(clean)}"

            data = self._make_request(url)
            if not data or 'results' not in data:
                break

            results = data['results']
            if not results:
                break

            should_stop = False
            for item in results:
                if stop_fn and stop_fn(item):
                    should_stop = True
                    break
                yield item

            if should_stop:
                break

            search_after = data.get('search_after')
            if not search_after or not data.get('next'):
                break

            base_params['search_after'] = search_after
            page_count += 1
            time.sleep(self.request_delay)


def read_config(app_dir=None):
    """
    Read Brandefense configuration.
    Reads default/brandefense.conf first, then local/brandefense.conf overrides.
    """
    if app_dir is None:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    config = {}

    for conf_dir in ['default', 'local']:
        conf_file = os.path.join(app_dir, conf_dir, 'brandefense.conf')
        if os.path.exists(conf_file):
            parser = configparser.ConfigParser()
            parser.read(conf_file)
            if 'settings' in parser:
                for key, value in parser['settings'].items():
                    config[key] = value

    return config


def should_run(checkpoint, interval_seconds, logger=None):
    """
    Check if enough time has elapsed since the last successful run.
    Returns True if the script should proceed, False if it should skip.
    Updates 'last_run_time' in checkpoint on return True (caller must save after work).
    """
    now = time.time()
    last_run = checkpoint.get('last_run_time', 0)
    elapsed = now - last_run

    if elapsed < interval_seconds:
        if logger:
            remaining = int(interval_seconds - elapsed)
            logger.info(f"Skipping run, {remaining}s remaining until next collection")
        return False

    checkpoint.set('last_run_time', now)
    return True


def get_proxy_config(config):
    """
    Extract proxy configuration from config dict.
    Returns a dict {host, port, username, password} if proxy is enabled and host is set.
    Returns None otherwise.
    """
    enabled = config.get('proxy_enabled', 'false').lower() == 'true'
    if not enabled:
        return None

    host = config.get('proxy_host', '').strip()
    if not host:
        return None

    return {
        'host': host,
        'port': config.get('proxy_port', '').strip(),
        'username': config.get('proxy_username', '').strip(),
        'password': config.get('proxy_password', '').strip(),
    }
