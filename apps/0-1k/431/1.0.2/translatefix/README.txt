Author: Glenn Sinclair
**********************

This is an example Splunk command called translatefix that takes a bunch of FIX
events in csv format (indexed by Splunk) and translates the FIX codes to human
readable text.


Usage:

<some search> | translatefix

You will then get human readable events.

Installation:

Copy the bin/translatefix.py and bin/translatefix.cfg files to your
$SPLUNK_HOME/etc/system/bin directory. Then, in your local
$SPLUNK_HOME/etc/system/local directory, create or edit existing authorize.conf
and commands.conf.

In commands.conf add:

[translatefix]
FILENAME = translatefix.py

In authorize.conf add:

[capability::run_script_translatefix]

[role_admin]
run_script_translatefix = enabled


Restart Splunk to test the commmand. If you want to change, remove, or add
your own slogans, edit slogans.txt

Default slogans come from Splunk T-Shirts and new ones are from Gerald K.




