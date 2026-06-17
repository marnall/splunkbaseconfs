Author: Nimish Doshi
********************

Ever wonder if what the route of an address in your logs is from your Splunk
server? This could be one of your own addresses in your data centers or one
that is remote to other sites and you want to trace the route.
This add on is a traceroute Splunk command that takes an address field (ip
or hostname) in your events and traces the route to the address from the
Splunk indexer. It uses a default of 2 second timeouts per hop, 20 hops max,
and stops searching after it finds 5 non-responsive addresses per IP query. All
of this is configurable in the Python command. Credit goes to Leonid Grinberg
for providing a sample to build the code from
https://github.com/leonidg/Poor-Man-s-traceroute. Results go to a new field
called traceroute in the [num] address [num] address ... format.
Note: the command requires root (sudo) or Administrator access to run. If you
start Splunk as a root user, you must continue to use it as root as root now
owns the Splunk index files. Do not go back and forth from root to the
normal user.

Usage:

<search that has field called address (containing an ip or host)> | traceroute
<search that has field containing an ip or host | traceroute address as <local-field>

The distribution comes with a traceroute.log file that gets
indexed into your sample index. You can do things like:

index=sample sourcetype="traceroute_addresses"|traceroute|table address,
traceroute

index=sample sourcetype="traceroute_addresses"|dedup address|traceroute|table
 address, traceroute


Note that you must either have an address field in your events or 
create one using the "address as <local-fieldname>" argument to the command.

Since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of (less than a 20)
addresses at a time as the search will take a long time.


Installation:

The command traceroute has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:


Copy the  bin/traceroute.py  files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[traceroute]
FILENAME = traceroute.py

In authorize.conf add:

[capability::run_script_traceroute]

[role_admin]
run_script_traceroute = enabled


Restart Splunk (as root) to test the commmand.







