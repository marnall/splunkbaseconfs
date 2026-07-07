# fb_ctf (Facebook Capture The Flag)

The FB_CTF Splunk app is a set of dashboards and queries designed to help administer a CTF compitition using the FB_CTF game engine.  The engine does have some of the same capabilities native to it, but not in as nearly a easy way to navigate.

## Prerequisites
This app has been tested for use in a single node deployment of Splunk Enterprise 7.0.  I see no reason why this shouldn't work in a distributed architecture but just never bothered to test it because you shouldn't really need a distributed architecture for a simple CTF compitition.

In order for this to work, the FB_CTF engine must already be installed on the hosting server.  The hosting server must be reconfigured to allow an external user to connect to it using mySQL (TCP/3306).  By default the FB_CTF engine prevents this from happening with the mySQL configuration, and possibly with the firewall.  Additionally, a read-only mySQL user must be created with remote login capabilities.

On the Splunk server, the Splunk DB Connect application must be installed and configured first.  Create an identity that is able to login to the mySQL server, and then create the connection to that server.  The default database should be ctf and the connection must be called "FBCTF"

## Operation
Once the app is installed and enabled, ensure that you verify connectivity to the ctf mySQL database.  After that, there isn't a lot to do.  A query runs every 10 minutes to get a current list of levels and teams.  You may have to go into the DB Connect application and reset all of the checkpoint values for the rising value column back to 0.

Detailed instructions can be found in the attached installation guide (also located in $APP_HOME/appserver/static/)
