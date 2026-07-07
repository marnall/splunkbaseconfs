[slack_alert_name]
* (Unique) name for your Slack Webhook alert.

action.slack_webhook = <string>
* Slack Incoming Webhook URL
* (required)

action.slack_message = <string>
* Text of the Slack message to send. Slack formatting and "\n" for a newline are accepted, as well as Splunk token substitutions as described in https://docs.splunk.com/Documentation/Splunk/6.5.2/Alert/EmailNotificationTokens.
* (required)