[SETTINGS]
URL = <value> # URL of SnapAttack API
SEND_STATS = <true|false> # Whether to send detection hits metadata to SnapAttack
SEND_LOG = <true|false> # Whether to include full matching log with hits
MAX_SEARCH_TIME_SEC = <int> # The maximum allowed runtime for a search
JOB_SIZE_LIMIT_MB = <int> # The maximum allowed size on disk for a search job
MAX_RESULTS = <int> # The maximum number of hits to include when running a deployed detection

[RANK]
TEMP_FILE_DIR = <value> # The location on disk to stage bulk ranking results (if SEND_LOG is enabled)
MAX_CONCURRENT_SEARCHES = <value> # The maximum number of concurrent searches allowed during a job execution
MAX_REACHBACK_SEC = <value>  # Maximum lookback time (in Seconds) for a job query.

[PROXY]
HTTP_URL = <value> # URL for proxying http connections (supports basic auth via https://username:password@proxyurl.com syntax)
HTTPS_URL = <value> # URL for proxying https connections (supports basic auth via https://username:password@proxyurl.com syntax)