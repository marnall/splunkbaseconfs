Author: Nimish Doshi
********************

This is a Splunk command called ip2decimal that returns a decimal notation for
all your IP data in your events. A new field called ipdecimal<optional number>
is returned.

Usage:

<some search that has a IP addresses> | ip2decimal

Example:

sourcetype=access_common|ip2decimal|table ip, ipdecimal

Note that you must have an ip addresses in your events for the ipdecimal field
to exist in your results.

Installation:

The command ip2decimal has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:

Copy the bin/ip2decimal.py fil to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[ip2decimal]
filename = ip2decimal.py

In authorize.conf add:

[capability::run_script_ip2decimal]

[role_admin]
run_script_ip2decimal = enabled


Restart Splunk to test the commmand.






