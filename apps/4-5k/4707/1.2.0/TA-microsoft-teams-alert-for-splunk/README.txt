This is an add-on for [Splunk](https://www.splunk.com/).

This custom alert action add-on
send a customized message to a Microsoft Teams talk room
based on a triggered alert action in Splunk.

Note - This alert action integrates against the Microsoft Teams Incoming Webhook Connector.
https://docs.microsoft.com/en-us/microsoftteams/platform/concepts/connectors/connectors-using

# Installation

App installation requires admin priviledges.

* Navigate to "Manage apps" and click "Install app from file"
* Upload the app bundle

# Configuration

## Get Incoming Webhook URL for your Teams 

You should get an access token for LINE Notify API.
https://docs.microsoft.com/en-us/microsoftteams/platform/concepts/connectors/connectors-using

And also, you can configure proxy and logging settings.

# LICENSE

[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)

# Releases history

- version 1.0.0: initial version
- version 1.0.1: Splunk Cloud vetting failed due to https not enforced, https is now enforced and webhook url must not contain https://
