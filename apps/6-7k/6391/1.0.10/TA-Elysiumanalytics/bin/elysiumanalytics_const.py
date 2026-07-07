import os

# API Endpoints
CLUSTER_ENDPOINT = "/api/v2/statements"
COMMAND_ENDPOINT = "/api/v2/statements/<statement_handle>"


# App Name
APP_NAME = __file__.split(os.sep)[-3]



# Command execution configs
COMMAND_TIMEOUT_IN_SECONDS = 300
COMMAND_SLEEP_INTERVAL_IN_SECONDS = 10

USER_AGENT_CONST = "ElysiumAnalytics-AddOnFor-Splunk-1.0.0"
