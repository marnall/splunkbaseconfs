Author: Nimish Doshi
********************

This is an example Splunk command called slogan that adds random Splunk slogans
to your results table. The add-on was written strictly for entertainment value.

Usage:

<some search> | slogan |table _raw splunk_slogan

You will then get a new field called splunk_slogan with your results. You can
do things like:

<some search> | slogan | top splunk_slogan limit=100
<some search> | slogan | stats count by splunk_slogan

Installation:

Untar/gunzip (tar zxvf) the add-on into $SPLUNK_HOME/etc/apps

Restart Splunk to test the commmand. If you want to change, remove, or add
your own slogans, edit slogans.txt






