# About The Add-On WebexTeams_AlertAction

The WebexTeams_AlertAction Splunk Add-on is an alert action that can pass alert results to any Webex Teams (formerly Spark) id, which includes individual users, rooms, and workspaces. The add-on has the option to pass the event contents as a json payload, or as a csv attachment.

When an alert triggers, the WebexTeams_AlertAction makes an HTTP POST request on the Teams URL. The WebexTeams_AlertAction passes JSON formatted information about the alert in the body of the POST request.

Data Payload

POST request's JSON data payload includes the following details.
•	Search ID or SID for the saved search that triggered the alert
•	Search Name
•	Alert severity
•	Link to search results
•	Search owner and app
•	Search results <Optional>
•	CSV attachment<Optional>

Example
{
  "sid": "scheduler__admin__search__TestTeams_at_1580871900_994",
  "search_name": "TestTeams",
  "owner": "admin",
  "search_uri": "/servicesNS/admin/search/saved/searches/TestTeams",
  "app": "search",
  "results": {
    "rows": [
      {
        "dc": "rcdn",
        "host": "vbongoni",
        "source": "localhost"
      },
      {
        "dc": "alln",
        "host": "vbongoni",
        "source": "localhost"
      },
      {
        "dc": "mtv",
        "host": "vbongoni",
        "source": "localhost"
      }
    ]
  }
}

Configure a Webex Teams alert action
Set up a Webex Teams when selecting alert actions for an alert.
Steps
1.	Create a new alert	- From the Search page in the Search and Reporting app, select Save As > Alert. Enter alert details and configure triggering and throttling as needed.
2.	Edit an existing alert - 	From the Alerts page in the Search and Reporting app, select Edit>Edit actions for an existing alert.
3.	From the Add Actions menu, select Webex Teams alert action.
4.	Type a URL for the Webex Teams alert action.
5.	Enter Authorization Bearer token
6.	Enter Room ID
7.	Select alert severity
8.	Select include result option to send results to Teams.
9.	Select attach csv option to send results as an attachment to Teams.
10.	Click Save.


#Support
Splunk version supported : 8.0, 7.3, 7.3, 7.1

# Support
vbongoni@cisco.com
