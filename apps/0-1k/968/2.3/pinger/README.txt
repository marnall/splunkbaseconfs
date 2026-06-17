Author: Paul Stout
Version: 2.3
________________________

This add-on allows monitoring of web resources in Splunk.  Give the add-on a list of resources to monitor and Splunk
will tell you the HTTP status code returned, time to connect, time to serve the request, and bytes sent.

Installation:

Installing Pinger requires either a full Splunk instance or a heavy forwarder
because the scripted input is in Python.

Extract the tarball into $SPLUNK_HOME/etc/apps.  Once extracted, review pinger/default/pinger.conf.spec and pinger.conf.example
to understand the configuration format.  Edit pinger/local/pinger.conf to add monitor stanzas.  Edit pinger/local/inputs.conf
to enable/disable global monitoring and change the frequency.  Monitoring more websites should use longer intervals (30 - 60s)
whereas fewer monitors may be run more freqwuently.

Once you have configured the monitors and verified data in Splunk, you may create alerts for pages returning less data than expected,
taking longer to connect than expected, or returning different HTTP status codes than expected.

** Note for Windows

Windows uses different path delimiters from *NIX or Mac.  You must recreate
the scripted input in local/inputs.conf and reverse the direction of the
slashes.  i.e.:

[script://./bin/heartbeat.py]

should become:

[script://.\bin\heartbeat.py]

on Windows ONLY. Be sure that you clone the stanza in inputs.conf and don't
edit the default!

Of course, if you're completely stuck please reach out to Paul Stout <pstout@splunk.com>.

CHANGELOG

1.2:
	First public version
1.3:
	Resolved issue with spaces in site label
2.0:
	Added lookupdns attribute
	Added dashboard
	Added setup script for search heads
	Disabled scheduled searches for distributed deployment
	Resolved an issue with default locations
	Tested on Mac, Windows.  Docs updated for a Windows annoyance
	Resolved issue with spaces in label.  Note to self, check all of them
	Resolved an issue with Boolean attributes (only respected "true")
	Resolved in issue where DNS lookup time was counted in connect time
	Added ability to mark production vs non, external vs internal
2.1:
	Added timeout parameter--granular control to reduce false positives
	Updated main dashboard to show errors by location
	Added error chart to main dashboard
	Corrected eventtype visibility issue
	More granular error checking, passes the actual Python exception/message
	Can distinguish between socket and http errors
2.2:
	Corrected an issue created in 2.1 wherein Pinger will fail in certain conditions.
2.3:
	Squashed a bug with https monitoring
