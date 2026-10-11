[previdian://<name>]
api_token = <string> API token sent as X-API-Token. Required.
base_url = <string> Previdian host. Default https://previdian.com.
tier = <string> pro or enterprise. Must match the token.
collect_kevs = <boolean> Sync the KEV catalog. Default true.
collect_notifications = <boolean> Index Watch notifications. Default true.
collect_priority = <boolean> Refresh the Priority lookup. Default true.
collect_observations = <boolean> Index Enterprise raw observations. Default false.
collect_infrastructure = <boolean> Index Enterprise attacker infrastructure. Default false.
collect_attackers = <boolean> Index Enterprise attacker summaries. Default false.
python.version = python3
