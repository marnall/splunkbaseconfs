Author: Nimish Doshi

Gunzip/Untar this distribution to $SPLUNK_HOME/etc/apps. Then, assuming you
have a internet connection on the Splunk machine, enable inputs in default's
inputs.conf. Restart Splunk.

This application indexes RSS headlines from the NBA and ESPN NBA. It also
shows embedded web pages for NBA and Bleacher Report NBA in the default
dashboard.The user can click on a title and get to the event. From the event,
the usercan use the field picker to show the link field and from the
pulldown workflow action of the link field, click on Read Article to read
the article.

This has been tested on Unix. To run this on Windows, make sure you have
Python in your path, the RSS feed parser in the bin directory can run on
Windows, and you can exectute the rss_nba.bat and rss_espn_basket.bat scripts
from the command line.

Debugging:

Make sure that rss_nba.sh and rss_espn_basket.sh in the bin directory can run
from the commmand line before attempting to run this app.

