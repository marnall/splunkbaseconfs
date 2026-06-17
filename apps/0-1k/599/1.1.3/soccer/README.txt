Author: Nimish Doshi

Gunzip/Untar this distribution to $SPLUNK_HOME/etc/apps. Then, assuming you
have a internet connection on the Splunk machine, enable inputs in default's
inputs.conf. Restart Splunk.

This application indexes RSS headlines from FIFA and Soccer News.
It also shows embedded web pages for World Soccer News and Soccer News in the
default dashboard. The user can click on a title and get to the event.
From the event, the user can use the field picker to show the link field
and from the pulldown workflow action of the link field, click on Read
Article to read the article.

This has been tested on Unix. To run this on Windows, make sure you have
Python in your path, the RSS feed parser in the bin directory can run on
Windows, and you can execute the rss_fifa.bat and rss_espn_soccer.bat
scripts from the command line. The bat scripts assume that %SPLUNK_HOME%
is set. Either set it in the scripts themselves or in your environment
variables (e.g., set SPLUNK_HOME=C:\Program Files\Splunk).



Debugging:

Make sure that rss_fifa.sh and rss_soccernews.sh in the bin directory can
run from the commmand line before attempting to run this app.
