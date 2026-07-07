Splunk Alert Action that allows you to send messages to MQTT broker securely

Author: Gary Croker

Version: 1.0.5

Updates history:

[1.0.0] 

- Initial release 
- Includes paho v2.1.1.dev, splunk-sdk-python v2.0.2

[1.0.1]
- Bug fixes

[1.0.3]
- update splunk-sdk-python v2.0.2

[1.0.4]
- binary file declartions
- update splunk-sdk-python v2.1.0

[1.0.5]
- check appinspect details and compatability with splunk v10.x

Installation:

- Install this TA on your Search Head or SHC, it is an alert action TA

- If using SSL and SHC deploy your certificates from deployer 

- Navigate to the configuration page of this add-on and configure connection to your MQTT broker. It is mandatory to use password authentication in this add-on, optional to use SSL and certificates. SSL and certificates is highly recommended. CA Certificate method is also available.

If using SSL tick the box and enter the full path and filenames of both certificate and key to use

- Click Save

Alert action configuration:

- Create new alert or edit an existing one

- Find the "Trigger Action" menu and click to "Add Actions"

- Select "Alert to MQTT"

- Specify MQTT Topic you want to send a message

- Write message you want to send to MQTT Topic in the form below. Also you can use Splunk tokens in your message. Full list of available tokens you can find here https://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModAlertsLog#Pass_search_result_values_to_alert_action_tokens

- Choose the protocol version you want to use - defaults to v3.1

- All sessions to brokers are clean session connections, means broker does not retain details. Client ID is this TA name and random 6 Alphanumeric

- SSL enter the paths and filenames of both certificate and key. CA Certificate method is also available.

What is MQTT you can read here https://en.wikipedia.org/wiki/MQTT
