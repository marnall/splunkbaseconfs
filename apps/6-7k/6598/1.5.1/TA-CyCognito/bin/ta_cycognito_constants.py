"""This file contains constants used by all files."""

ASSETS_ENDPOINT = "/v1/assets"
ISSUES_ENDPOINT = "/v1/issues"
RESOLVED_ISSUES_ENDPOINT = "/v1/resolved-issues"
ASSET_TYPES = ['webapp', 'iprange', 'ip', 'domain', 'cert']

DEFAULT_LOG_LEVEL = "INFO"

STATUS_FORCELIST = list(range(500, 600)) + [429]
REQ_TIMEOUT = 180    # In seconds
PAGE_LIMIT = 1000
SSL_VERIFY = True
