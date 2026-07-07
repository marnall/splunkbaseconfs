""" App name defined here """
APP_NAME = "TA-SpyCloud"
USER_AGENT = "SplunkAddOn/3.3.3"

DEFAULT_START_DATE = "1970-01-01"

MSG_NOT_RUNNING = "Status Code: N/A. Not running on this system"
MSG_RUNNING = "Status Code: N/A. Running on this system"
MSG_PROXY_407 = "Status Code: 407. Cannot connect to proxy. Verify proxy URL, credentials, and network reachability."
MSG_PROXY_GENERIC = "Status Code: N/A. Cannot connect to proxy. Verify proxy settings."
MSG_FORBIDDEN_IP = "IP Address Not Allowed: Your source IP is not on your SpyCloud allowlist. Please contact your SpyCloud administrator to add your IP address to the allowlist, or check if your network configuration has changed."
MSG_FORBIDDEN_KEY = "Invalid API Key: The API key is incorrect, disabled, or deactivated. Please verify your API key is correct, check with your SpyCloud administrator if the key is still active, or generate a new API key from the SpyCloud portal."
MSG_RATE_LIMIT = "API Quota Exceeded: You have reached your API rate limit. Please wait a few minutes before trying again, or contact your SpyCloud administrator to review your usage limits."
MSG_UNEXPECTED_API = "Status Code: N/A. Unexpected error contacting SpyCloud API."
MSG_API_PREFIX = "Status Code: N/A. Received error from SpyCloud API."

MSG_KV_NOT_FOUND = "Status Code: N/A. KV Store checkpoint not found, starting load at 1970-01-01"