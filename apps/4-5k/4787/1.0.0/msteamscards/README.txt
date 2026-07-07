###########################################################
####	Microsoft Teams Alert Cards for Splunk
###########################################################

####	Version Info
This Version:	1.0.0
Release Date:	11/21/2019
App Author:	GROUND Security

####	System Requirements
1) The Splunk server that this alert app runs on needs to be able to send outbound requests to Teams on port 443/tcp.
2) App tested with Splunk Enterprise v8.0.0
3) This lightweight app will run on any server that Splunk is able to run on.

####	How to Use
Note: full instructions available at https://www.groundsecurity.com/splunk-app-microsoft-teams-alert-cards/
1) Install app on Search Head(s).
2) Add “Send MessageCard to Teams” action to an alert.
3) Configure action fields:
	a) Teams Webhook URL: generate from Teams channel
	b) Card Title: this text will show as the card's title
	c) Card Subtitle: this text will show as the card's subtitle
	d) Card Image URL: URL to image to be displayed as part of the card
	e) Card Theme Hex Color: 6-digit hex code for color theme (don't include # sign)
4) Save action and save alert.
5) Pass a field titled "messagetext" in the search for your alert to be sent as the text in the Card.

####	Need Support?
Run the search:	index=_internal *msteams*
Look for the error code that the script exits with.
Email support at info@groundsecurity.com if needed.