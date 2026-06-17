Author: Nimish Doshi
********************

Ever wonder if an user@address in your event has a finger server running?
This could be one of your own addresses in your data center where running a
finger server is supposed to be prohibited. This is a Splunk command
called fingerstatus that returns in realtime a status to see if finger
response is available for the user@address in question. It takes input a
user@address field, which you can create by using
|eval finger_address = <some user@address in your event>
and returns an fingerstatus field. Only if a connection and response is made
does a real value get returned for the created fingerstatus field. A timeout of
3 seconds is used in the code that you can adjust. A value of "none" is
returned upon timeout.

Usage:

<search that has a finger_address field> | fingerstatus
<search that has a field that contains a host or ip> | fingerstatus finger_address as <local fieldname>

The distribution comes with a finger.log file that gets
indexed into your sample index. You can do things like:

index="sample" sourcetype="finger_addresses" address!=""|dedup address|rename
 address as finger_address|fingerstatus|table finger_address, fingerstatus

Note that you must either have a finger_address field in your events or 
create one using args finger_address as <local fieldname>. If a connection
is refused or if the address is not found, the status will be "none"

Since this is going to the internet to get the status in realtime,
it is best to run this command only with a handful of (less than a 100)
addresses at a time or else the search will take a long time.


Installation:

The command fingerstatus has been configured in the TA to run out of the box
with read role for the whole system. Just untar gunzip this into the 
$SPLUNK_HOME/etc/apps directory and restart Splunk.

*****************************************************************

If you want to configure it manually, perform the following:

Copy the  bin/fingerstatus.py  files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[fingerstatus]
FILENAME = fingerstatus.py

In authorize.conf add:

[capability::run_script_fingerstatus]

[role_admin]
run_script_fingerstatus = enabled


Restart Splunk to test the commmand.






