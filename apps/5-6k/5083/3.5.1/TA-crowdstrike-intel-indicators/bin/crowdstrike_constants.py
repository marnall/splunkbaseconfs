
# Base URLs
# US Commercial
us_commercial_base = "https://api.crowdstrike.com"

# US GovCloud
govcloud_base = "https://api.laggar.gcw.crowdstrike.com"

# GovCloud2
govcloud2_base = "https://api.us-gov-2.crowdstrike.mil"

# EU Cloud
eucloud_base = "https://api.eu-1.crowdstrike.com"

# US Commercial Cloud 2
us_commercial2_base = "https://api.us-2.crowdstrike.com"

# API variables
timeout = (30, 600)
rate_limit_retries = 3
rate_limit_backoff = 5
max_indicators_per_page = 9000  # CrowdStrike API max is 10000; 9000 provides margin

# Default start epoch — 2010-01-01 00:00:00 UTC
# Used when no checkpoint exists and no user-configured start_date
default_start_epoch = 1262304000
