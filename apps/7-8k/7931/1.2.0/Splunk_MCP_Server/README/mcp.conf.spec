# mcp.conf.spec
# Configuration specification for MCP (Model Context Protocol) server

[server]
* This stanza configures the MCP server settings

timeout = <float>
* Timeout in seconds for requests to Splunk
* Default: 60.0
* Range: 1.0-300.0

saia_timeout = <float>
* Timeout in seconds for all Splunk AI Assistant API-backed tools
* Default: 200.0
* Range: 1.0+

max_row_limit = <integer>
* The maximum number of rows that can be returned in a single search query
* Default: 1000
* Range: 1-1000000

default_row_limit = <integer>
* The default maximum number of rows to return in a search query when not specified
* Default: 100
* Range: 1-1000000

ssl_verify = <string|boolean>
* Whether to verify SSL certificates for outgoing HTTPS requests
* Default: true

require_encrypted_token = <boolean>
* Whether bearer tokens must be RSA-encrypted with the server public key.
* If true, non-decryptable tokens are rejected (401). If false, non-decryptable accepted.
* Default: true

legacy_token_grace_days = <integer>
* Temporary migration window (days) during which legacy plaintext and prior-key tokens are accepted.
* 0 disables the compatibility window entirely.
* Minimum: 0
* Default: 180

mcp_token_max_lifetime_seconds = <integer>
* Maximum allowed lifetime (seconds) for tokens minted by /services/mcp_token.
* Token requests with expires_on beyond this ceiling are rejected (fail closed).
* Minimum: 1
* Default: 15552000

mcp_token_default_lifetime_seconds = <integer>
* Default lifetime (seconds) applied when /services/mcp_token is called without expires_on.
* Must be <= mcp_token_max_lifetime_seconds; clamped to max if it exceeds it.
* Minimum: 1
* Default: 15552000

token_key_reload_interval_seconds = <float>
* How often (seconds) TokenCrypto refreshes cached RSA encryption keys from KV Store.
* Ensures key rotations performed by other cluster nodes are picked up promptly.
* Minimum: 0
* Default: 300

cui_enforce_jwt_validation = <boolean>
* Enforce strict JWT signature and claim validation for incoming CUI assertions before token exchange.
* When true, assertions that fail validation are rejected before /oauth2/v1/token is called.
* Default: true

cui_allowed_jwt_algs = <string>
* Comma-separated list of JWT signing algorithms accepted for CUI assertions.
* Default: RS256

cui_jwks_by_issuer = <string>
* JSON dictionary mapping issuer URL to its JWKS URL for CUI JWT validation.
* If an issuer is absent, the server derives the JWKS URL as {issuer}/oauth2/v1/keys.
* Default: {}

cui_jwt_clock_skew_seconds = <integer>
* Allowed clock skew (seconds) when validating the exp claim of CUI JWTs.
* Minimum: 0
* Default: 60

[rate_limits]
* This stanza configures request admission controls for /services/mcp.
* `global` is used for tools/call rate limiting.
* `admission_global` controls pre-auth endpoint admission and may be 0 (disabled).
* All values below except `admission_global` must be greater than zero, otherwise requests fail closed (503).

global = <integer>
* Global tools/call requests allowed per 60-second window.
* Default: 600

admission_global = <integer>
* Global pre-auth /services/mcp requests allowed per 60-second window.
* 0 disables this global admission cap.
* Default: 0

tenant_authenticated = <integer>
* Requests allowed per authenticated token per 60-second window.
* Default: 240

tenant_unauthenticated = <integer>
* Requests allowed per source IP (unauthenticated traffic) per 60-second window.
* Default: 60

circuit_breaker_failure_threshold = <integer>
* Consecutive 5xx responses before opening the circuit.
* Default: 20

circuit_breaker_cooldown_seconds = <integer>
* Seconds to keep circuit open before admitting requests again.
* Default: 30
