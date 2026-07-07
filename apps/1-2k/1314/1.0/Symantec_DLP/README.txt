This App is configured for an index with the name of "dlp" so you will need to create the appropriate stanza in your inputs.conf file to direct all the traffic to the below port into the correct index.

From the Symantec DLP system, you will need to setup and configure the "Log to a Syslog Server" response rule under Manage > Response Rules.

Host = <Splunk Indexer IP>

Port = <listening udp port>

Message = ID: $INCIDENT_ID$, Policy Violated: $POLICY$, Count: $MATCH_COUNT$, Protocol: $PROTOCOL$, Recipient: $RECIPIENTS$, Sender: $SENDER$, Severity: $SEVERITY$, Subject: $SUBJECT$, Target: $TARGET$, Filename: $FILE_NAME$, Blocked: $BLOCKED$, Endpoint: $ENDPOINT_MACHINE$

Level = 7 - Debugging

The above "Message" will allow this app to work right out of the box.  You may add additional output from Symantec as desired. You will just have to add the additional Field Extractions in Splunk for your new queries to work.


