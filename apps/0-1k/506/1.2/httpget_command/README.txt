Author: Nimish Doshi
********************

This is an example Splunk command called httpget that returns in realtime
the first 1024 bytes for httpget response for URL's in your events.
The httpget field goes into your results table returned by interSplunk.
<Note: Since 1024 bytes are returned from each URL, results can take a long
time>

Usage:

<search that a has field named url> | httpget
<search that contains a field containing a url | httpget url as <local-field>

The distribution comes with a sample_url.log file that gets indexed into your
sample indext. You can do things like:

index="sample" sourcetype="sampleurl"|dedup myurl|rename myurl as url|httpget|table url, httpget

index="sample" sourcetype="sampleurl"|dedup myurl|httpget url as myurl|table myurl, httpget

Note: This assumes you have an index called sample. Either create an index
called sample from Splunk Manager or change the local/inputs.conf file to use
an index you already have to test with the sample events.

Note that you must either have a url field in your events or create one using
the eval command. Also, if connection is refused or if the URL is not found,
a "" is assigned to the httpget field that you can then filter
out of our reports (search httpget!="")

Also, since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of  (less than a 100) URLs
at a time or else the search will take a long time.


Installation:

The command httpget has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:

Copy the bin/httpget.py files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[httpget]
FILENAME = httpget.py

In authorize.conf add:

[capability::run_script_httpget]

[role_admin]
run_script_httpget = enabled


Restart Splunk to test the commmand.






