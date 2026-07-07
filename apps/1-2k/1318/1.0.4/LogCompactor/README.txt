LogCompactor sends emails of Linux/Unix syslogs and Windows EventLogs in html format.  It will compact log events and provide a count of same events.

There are 2 Perl scripts and 2 shell scripts.
The prerequisites for the Perl scripts are the following packages:
Carp
English
POSIX
Getopt::Long
PerlIO::gzip
Text::CSV::Slurp
Digest::MD5
Mail::Sendmail


The scripts will install to /opt/splunk/etc/apps/LogCompactor/bin/
Below are the script names and purpose:
eventlogcompactorwrapper.sh - This is a wrapper script that is executed by a Splunk scheduled search.
eventlogcompactor.pl - This is the Perl script that compacts and emails Windows EventLogs.
syslogcompactorwrapper.sh - This is a wrapper script that is executed by a Splunk scheduled search.
syslogcompactor.pl - This is the Perl script that compacts and emails Linux/Unix syslogs.


Instructions for installation:
1) Install the LogCompactor add-on
2) Go to the /opt/splunk/etc/apps/LogCompactor/bin/ directory and run the following commands:
    perl -c eventlogcompactor.pl
    perl -c syslogcompactor.pl
    If either of these commands fail, you will likely need to install additional Perl modules.
3) Symlink, or copy, eventlogcompactorwrapper.sh and syslogcompactorwrapper.sh to /opt/splunk/bin/scripts/
4) For each scheduled search, you will need a corresponding wrapper script.  Make a copy of the wrapper script and rename it to a filename that you will put in the script section of the scheduled search.  You will do this for each search that you schedule.
4a) Edit the wrapper script and modify the values for --emailto --emailfrom --smtpserver and --threshold.  The threshold option will only display logs that are repeated the specified number of times. You may want to start with a threshold value of 1 until you get a better understanding of your logs. 
5) Create a new eventtype in Splunk for the search that you would like to run.  I recommend a query that displays everything that is not explicitly ignored.
6) Create a new scheduled search within Splunk under the LogCompactor Application.  
6a) Enter a search for the eventtype you created in the previous step.
6b) Configure the time range and schedule.
6c) Set the condition to only alert if the number of events is greater than 0.
6d) Check the checkbox under "Run a script" and type in the filename of the wrapper script you copied in step 4.
6e) Save the scheduled search.
7) Enjoy
