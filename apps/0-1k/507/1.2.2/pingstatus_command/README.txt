Author: Nimish Doshi
********************

This is an example Splunk command called pingstatus that returns in realtime
the ping status for IP, DNS, or URLs in your events. The pingdelay field goes
into your results table returned by interSplunk.

Note that this code uses public domain code ping.py
by Matthew Dixon Cowles and Jens Diemer

Note that Splunk must be running with root (or sudo splunk start) access to
call the ICMP protocol.

Usage:

<search that has a field named url> | pingstatus
<search that has a field that contains IP or host> | pingstatus url as <local-field>

The distribution comes with a sample_url.log file that gets indexed into your
sample indext. You can do things like:

index="sample" sourcetype="sampleurl"|dedup myurl|rename myurlpingstatus as url|table url, pingdelay

sourcetype=<your IP access logs>|dedup ip|pingstatus url as ip|search pingdelay!=""|table ip, pingdelay

Note that you must either have a url field in your events or create one using
the args to pingstatus. If connection is refused or if the URL is not found,
there will be no delay in your results. You can filter this out by using
(pingdelay!="") so that you can find all addresses that responded to your ping.
Also, since the delay is usually less than 1 MS, Splunkweb may only show it
as 0.0.

Since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of (less than a 100) URLs
at a time or else the search will take a long time.


Installation:

The command pingstatus has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:


Copy the bin/pingstatus.py bin/ping.py and bin/ping.pyc  files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[pingstatus]
FILENAME = pingstatus.py

In authorize.conf add:

[capability::run_script_pingstatus]

[role_admin]
run_script_pingstatus = enabled


Restart Splunk to test the commmand.


*****************
Experimental pingstatus.py

If you want a ping version that can iterate several times and send pings to
the same address to get an everage ping delay, see experimental_pingstatus.py
in the bin directory. If the code meets your needs, rename this file
to pingstatus.py, modify the code to meet your environment if needed, and
test it. This was updated by Arkady Zilberberg and is provided as is with
no warranty.







