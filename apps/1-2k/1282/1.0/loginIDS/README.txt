-------------------------------------------------------------------------------
LoginIDS-Splunk-App
-------------------------------------------------------------------------------

This App is designed to display the output of the program LoginIDS. 
LoginIDS can analyzes logfiles of several services like the SSH-Server sshd
and learn the login behavior of users. After learning the "normal" login
behavior of a user, LoginIDS will report changes to that behavior. Those
changes generate Alerts that are indexed by the LoginIDS-App and can then be
displayed.

The displays in this app include a overview, listing all alerts that occurred
in an user defined time frame. Additional there is a graph which shows alerts
over time and pie-charts giving detailed information over how alerts are split
between the different hosts.
The efficiency dashboard displays how many alerts where generated and how
many logfile entries where analyzed by LoginIDS.
An additional form can be used to search for the alert and connection history
of a particular user.

The program LoginIDS can be found at: https://git.lrz.de/?p=LoginIDS.git or
https://freecode.com/projects/loginids

