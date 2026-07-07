[jira_comments_collector://<name>]
site_url = If your remote Jira URL is https://mycompany.atlassian.net, enter "mycompany.atlassian.net" in this textfield (without the quotes).
jql = Defaults to the logic "all issues updated in the past 2 min". The JQL must be URL-encoded, e.g. "updated > -2m" is translated to "updated+%3E+-2m" (withouth the quotes).
service_account = Configure your service account in Configure page.

[jira_issues_collector://<name>]
site_url = If your remote Jira URL is "https://mycompany.atlassian.net/", enter "mycompany.atlassian.net" in this textfield (without the quotes).
jql = Defaults to the logic "all issues updated in the past 2 min". The JQL must be URL-encoded, e.g. "updated > -2m" is translated to "updated+%3E+-2m" (without the quotes).
fields = Comma-separated values. Feel free to add / remove fields to your liking. There will always be the fields "id", "key", "status", and "updated", which serve as default. DO NOT add the field "comment".
service_account = Configure your service account in Configure page.