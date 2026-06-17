Author: Nimish Doshi
********************

Ever wonder if an address in your event can be connected via telnet?
This could be one of your own addresses in your data center where running a
telnet server is supposed to be prohibited. This is a Splunk command
called telnetstatus that returns in realtime a status to see if a telnet
server is running on the address in question. It takes input a telnet_address
field, which you can create by using |eval telnet_address = <some address in
your event> and returns a telnetstatus field.

Here are the possible values for telnet status:
LoginFound means a connection is made and the login prompt was presented.
LoginNotFound means a connection is made and the login prompt was not
presented.
None means no connection was made.

The timeout for connection as well as for finding a login prompt is set to 3
seconds in the Python code and it can be reconfigured in the code as needed.
Note that no attempt is actually made to login to the connected server.

Usage:

<search that has a telnet_address fieldname> | telnetstatus
<search that has a fieldname containing a host or ip> | telnetstatus teletnet_address as <local_fieldname>


The distribution comes with a telnet.log file that gets
indexed into your sample index. You can do things like:

index="sample" sourcetype="telnetlog" address!=""|dedup address|rename
 address as telnet_address|telnetstatus|table telnet_address, telnetstatus

Note that you must either have a telnet_address field in your events or 
create one using the telnet_address as <fieldname> argument. If connection is
refused or if the address is not found, the status will be None

Since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of (less than a 100)
addresses at a time or else the search will take a long time.


Installation:

The command ftpstatus has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:



Copy the  bin/telnetstatus.py  files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[telnetstatus]
FILENAME = telnetstatus.py

In authorize.conf add:

[capability::run_script_telnetstatus]

[role_admin]
run_script_telnetstatus = enabled


Restart Splunk to test the commmand.






