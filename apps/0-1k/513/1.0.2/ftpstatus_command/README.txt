Author: Nimish Doshi
********************

Ever wonder if an address in your event has an anonymous ftp server running?
This could be one of your own addresses in your data center where running an
anonymous ftp site is supposed to be prohibited. This is a Splunk command
called ftpstatus that returns in realtime a status to see if anonymous ftp is
running on the address in question. It takes input an ftp_address field, which
you can create by using |eval ftp_address = <some address in your event>
and returns an ftpstatus field. Only if an anonymous connection is made does
a connected value get returned for the created ftpstatus field. A timeout of
3 seconds is used in the code that you can adjust.

Usage:

<search that has a ftp_address field> | ftpstatus
<search that has a field containing a host or IP> | ftpstatus ftp_address as <local_field>

The distribution comes with a sample_addresses.log file that gets
indexed into your sample index. You can do things like:

index="sample" sourcetype="sample_addresses" address!=""|rename
 address as ftp_address|ftpstatus|table ftp_address, ftpstatus

Note that you must either have a ftp_address field in your events or 
create one using the args ftp_address as address. If connection is refused
or if the address is not found, the status will be not_connected.

Since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of (less than a 100)
addresses at a time or else the search will take a long time.


Installation:

The command ftpstatus has been configured in the TA to run out of the box with
read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:


Copy the  bin/ftpstatus.py  files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[ftpstatus]
FILENAME = ftpstatus.py

In authorize.conf add:

[capability::run_script_ftpstatus]

[role_admin]
run_script_ftpstatus = enabled


Restart Splunk to test the commmand.






