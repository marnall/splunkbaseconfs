README - SMS Text Alerting add-on for Splunk

This app will allow you to receive text alerts from Splunk - no matter which network you're on!
It leverages a* cloud-based communications service to send texts via a HTTPS connection.

* Soon to be more.


----------------------------------------------------------------------------------------------
SUPPORTED COMMUNICATIONS SERVICES:
Twilio - www.twilio.com - textalert-twilio.py


----------------------------------------------------------------------------------------------
SETUP:
This add-on does NOTHING by default! Follow these steps to get text alerts:
1. Get an account and phone number at one of the communications services listed above
2. Copy <SPLUNK_HOME>/etc/apps/textalert/bin/textalert-<service>.py to SPLUNK_HOME/bin/scripts
3. Edit <SPLUNK_HOME>/bin/scripts/textalert-<service>.py and input:
3a. Communications Service Username/Password
3b. TO phone number (recipient of SMS Text Message)
3c. FROM phone number (sender of message, often must be your communications service phone no.)
4. Set up an alert and use textalert-<service>.py as the "Run a Script" option


----------------------------------------------------------------------------------------------
CHANGE LOG:
v0.1 - Support for Twilio, self-install


----------------------------------------------------------------------------------------------
FUTURE FEATURES?
Please submit feedback on splunk-base.splunk.com! Some future features should include:
- Support for sending via other communications services (Tropo, Google Voice)?
- Proxy support?
- Automated set-up?
- UI management of alerts?


