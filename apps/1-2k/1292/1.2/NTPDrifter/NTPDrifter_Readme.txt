Readme File for NTPDrifter

NTPDrifter is a splunkapp that you deploy to a universal forwarder to measure the NTP drift between the
servers local clock and the time given by your local NTP source.

If does not correct for any time difference, it just tells you what it is.

Ways to use the data are given at the bottom of this readme.

Requirements
cscript.exe must be available on your target hosts
NTP Source hostname must be edited into the VB script as indicated.
Target hosts must be able to query NTP ie no firewall.

CAUTION - Standard disclaimer applies in this case.
This script/SplunkApp has no brain, you must use your own before executing it.
I accept no liablilty for dame to yours or any one elses computer network system as a result of using this app.
You use this app at your own risk.

copyright 2012
Conradejohnston@gmail.com

version control
v1.0 24th Nov 2012 - Initial release
v1.2 29th Nov 2012 - Removed Client/location specifc dependancies/quirks for uplaod to splunkbase

Tested ok on:
Windows XP
Windows 7
Windows 2003 R2
Windows 2008 R2

Deployment:
Deploy using deployment server to target your windows servers.

Splunk Requirements:
The app will write its data to an index named "windows_perfmon"
Sourcetype is ntp_drift
I have the interval set to 360s. This way you can see the servers drifting inbetween NTP sync operations
All these requriements can obviosuly be changed to suit your environment.
The location of the script is assumed to be the default install

Usage:

Daily Alert
I have a an alert that runs daily that runs the following search...

index=windows_perfmon sourcetype="ntp_drift" | head 500 | dedup host | rex "(?i):ntpDrift=(?P<ntpDrift>[^\\]]+)" | sort +ntpDrift, +host | head 10  | append [ search index=windows_perfmon sourcetype="ntp_drift" | head 500 | dedup host | rex "(?i):ntpDrift=(?P<ntpDrift>[^\\]]+)" | sort +ntpDrift, +host | reverse | head 10] | table host, ntpDrift

The time window is -15mins to now, and the search sends an email everytime it runs with the data returned inline as a list.

The list is emailed to an operations team whose job it is check and resolve any issues with NTP on the servers.

Historical Tracking
The data can also be graphed overtime to show how well your servers are tracking and whether you need tweak your NTP configuration.

index=windows_perfmon sourcetype="ntp_drift" host="<HOSTMASK>" | eval host=lower(host) | rex "(?i):ntpDrift=(?P<ntpDrift>[^\\]]+)" | timechart span=6min max(ntpDrift) by host

Choose line chart, labels and such to suit.





