Note that you can add entries for other cli commands that Nexus N9000 supports.Simply add a command in input.txt or create a new input file for required cli commands. It is also advised to use a unique sourcetype for each typeof input  so that you can better categorize and search for them later. For
consistency, consider using "cisco:nexus:<REFERENCE>" where "<REFERENCE>" is an arbitrary string

you need to pass parameters to below given  command line arguments to collect.py


 -inputFile  : Name of input file containing cli commands to run.This file should be in /bin directory of the App.
 
To add a new input file, one needs to add following stanza in default/inputs.conf file.

[script://./bin/Collect.py -inputFile input_new.txt]
index = main
sourcetype = nexus:<REFERENCE>
disabled = 1
interval = 300
passAuth = admin

This app is also configured to receive syslog on udp port 514 with default splunk settings for syslog  and then re-direct the logs to the app by replacing the sourcetype and index names.

[udp://514]
index = main
sourcetype = syslog


