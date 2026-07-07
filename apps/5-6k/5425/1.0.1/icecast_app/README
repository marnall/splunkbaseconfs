# Icecast App for Splunk
Splunk app containing configuration items, field extractions, and useful visualizations for Icecast logs.

# Prerequisites
First, configure all Icecast servers you wish to ingest logs from to send logs to port 514 of your Splunk instance. Both TCP and UDP inputs are supported.

# Install
Download the app from Splunkbase and restart Splunk instance. Select the Icecast App from the Apps dropdown, and follow the link labeled "Continue to app setup page" to complete installation. Enter the IP address or addresses of the Icecast servers as a comma-separated list, or use the * wildcard to accept logs from any device connecting on port 514 (not recommended, as this is the default syslog port). Uncheck the box labeled "TCP Connection" to recieve logs over UDP. Enter the name of the index you wish to ingest Icecast logs into. Click submit, and you'll immediately begin recieving logs.

In order to use the included visualizations, you'll need to upload a lookup CSV file containing your weekly radio schedule. This file should have the headers:

    time,sunday,monday,tuesday,wednesday,thursday,friday,saturday

and each line should take the form:

    <<NUMERICAL HOUR IN 24HR FORMAT>>,<<SUNDAY SHOWNAME>>,<<MONDAY SHOWNAME>>,<<TUESDAY SHOWNAME>>,<<WEDNESDAY SHOWNAME>>,<<THURSDAY SHOWNAME>>,<<FRIDAY SHOWNAME>>,<<SATURDAY SHOWNAME>>

If there is no show at a given day and hour, that entry on the CSV can be left blank. If there are no shows for a given hour, it is not necessary to include a line with that hour in the lookup CSV.

Upload the file to Splunk under the icecast_app context, and enter the name of the lookup file in the appropriate field in the visualizations.
