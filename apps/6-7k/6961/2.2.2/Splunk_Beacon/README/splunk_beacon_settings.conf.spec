[logging]
loglevel = 

[proxy]
# Whether to enable an outbound proxy for Guard Detect requests (0/1).
# If set to 1 (Enabled), an HTTPS proxy URL must be provided.
enable_proxy = 
# Full HTTPS proxy URL (HTTPS only).
# Examples (preferred without credentials):
#   https://proxy.example.com:8443
# Note: Credentials can be embedded (e.g., https://user:pass@proxy.example.com:8443),
# but using the fields below is recommended. If both are provided, the fields takes precedence.
https_proxy_url = 
# Optional proxy username (recommended instead of embedding in URL)
proxy_username = 
# Optional proxy password (stored encrypted; recommended instead of embedding in URL)
proxy_password = 