[get_events://<name>]
personal_access_token = This can be obtained via GitLab > Profile Settings > Access Tokens. N.B: The token must have permissions to access both the api and read_user in order to obtain everything it needs.
project_id = Enter a Project ID to collect data for a specific project. N.B. The inputs need to be configured on a per-project basis to guarantee event collection. A single input across all projects is limited
get_ci_trace_log = Get CI trace log when job fails