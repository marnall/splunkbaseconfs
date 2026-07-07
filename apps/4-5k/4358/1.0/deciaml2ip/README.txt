Author: Mohammadreza sarai 
info@besaman.com
********************

This is a Splunk command called decimal2ip that returns a decimal notation for
all your IP data in your events. A new field called ipdecimal<optional number>
is returned.

Usage:

<some search that has a IP addresses> | dec2ip

Example:

sourcetype=access_common|dec2ip|table ip, ipdecimal

Note that you must have an ip addresses in your events for the decimaltoip field
to exist in your results.

Installation:

The command dec2ip has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:

Copy the bin/dec2ip.py fil to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[dec2ip]
filename = dec2ip.py

In authorize.conf add:

[capability::run_script_dec2ip]

[role_admin]
run_script_dec2ip = enabled


Restart Splunk to test the commmand.






