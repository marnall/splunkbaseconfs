[jira_issue://<name>]
expand_fields = Comma-separated list of entities to expand (optional - more infos: https://docs.atlassian.com/software/jira/docs/api/REST/latest/)
index = (Default: default)
interval = Time interval of input in seconds.
issue_fields = Comma-separated list of Jira issue fields to collect (Default: summary,description,project,creator,assignee,reporter)
jql = The JQL (Jira Query Language) search filter defines which Jira issues to collect (more infos: http://confluence.atlassian.com/display/JIRA/Advanced+Searching)
last_updated_start_time = The start time for the input defines which Jira issues should be collected based on their last updated time. Format: 'YYYY-MM-DD hh:mm' (UTC). Default: 1 week ago
service_account = The Jira Account to use
