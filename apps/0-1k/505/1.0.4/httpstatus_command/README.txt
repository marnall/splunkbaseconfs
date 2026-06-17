Author: Nimish Doshi
********************

This is an example Splunk command called httpstatus that returns in realtime
the httpstatus code for URL's in your events. The httpstatus field goes into
your results table returned by interSplunk.

Usage:

<search that has a field named url> | httpstatus
<search that has a field containing a URL> |httpstatus url as <local-url-field>

NOTE: Make sure the url is without the protocol. For instance, www.google.com
is good, but https://www.google.com is not good.

The distribution comes with a sample_url.log file that gets indexed into your
sample indext. You can do things like:

index="sample" sourcetype="sampleurl"|dedup myurl|rename myurl as url|httpstatus|table url,httpstatus
index="sample" sourcetype="sampleurl"|dedup myurl|top httpstatus url as myurl|top httpstatus

Note that you must either have a url field in your events or create one using
url as <name> args. Also, if connection is refused or if the URL is not found,
a generic 0 code is assigned to the httpstatus field that you can then filter
out of our reports (search httpstatus!=0)

Also, since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of  (less than a 100) URLs
at a time or else the search will take a long time.


Installation:

The command httpstatus has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:

Copy the bin/httpstatus.py files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[httpstatus]
FILENAME = httpstatus.py

In authorize.conf add:

[capability::run_script_httpstatus]

[role_admin]
run_script_httpstatus = enabled


Restart Splunk to test the commmand.






