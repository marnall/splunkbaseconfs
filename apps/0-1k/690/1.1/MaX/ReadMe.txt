Summary
=================
This  app is an example of how to Splunk for Mail server management including Exchange 2003 and 2007.


Envirnoment
=================
This App was developed in the linux envirnoment and therefore references to absolute path 
and charset configuration in props.conf may need to be adjusted for windows platforms


Data Input Sources
=================
Please put your exchange 2003 tracking log in $SPLUNK_HOME/etc/apps/Max/Exchange_2003.
Please put your exchange 2007 tracking log in $SPLUNK_HOME/etc/apps/Max/Exchange_2007.
You can modify the monitor path in inputs.conf, but please don't change the sourcetype.


DISCLAIMER OF WARRANTIES
=================
This app only provdes information for user's reference.
Mail server management is a professional skill.
The author is not responsible for the any result of action took by users.
