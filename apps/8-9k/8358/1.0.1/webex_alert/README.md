# Webex Alert Action for Splunk

Send alert messages from Splunk to Webex Teams rooms.

## Installation

1. Install via Splunk Web: Settings → Apps → Manage Apps → Install app from file
2. Upload `webex_alert.tar.gz`
3. Restart Splunk
4. Install Python requests: `$SPLUNK_HOME/bin/splunk cmd python -m pip install requests --break-system-packages`

## Configuration

1. Get Bot Token from https://developer.webex.com/my-apps
2. Add bot to your Webex room
3. Get Room ID
4. Create alert and add "Send Webex Message" action
5. Configure bot token, room ID, and message

## Message Tokens

Use `$field_name$` in messages to insert search result values.

Example: `Alert! Count: $count$, Host: $host$`

## Support

- Plain text messages
- Markdown formatted messages
- Token substitution from search results
