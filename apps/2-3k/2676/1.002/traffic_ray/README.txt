Traffic Ray
===========

== Author ==

Gleb Esman
glebesman@gmail.com
http://www.mensk.com/
http://trafficray.com/


== Description ==

Traffic Ray analyses real time HTTP WEB traffic via Apache Web logs generated on Web hosting servers (including WHM and Cpanel based) and offers visual dashboards representing WEB activity trends and hit patterns across all hosted websites and visitor's IP addresses.

It helps you to uncover malicious hits, suspicious incoming activity patterns, spammy attacks and coordinated penetration attacks targeting any of the hosted websites.
Additionally to that Traffic Ray app helps to discover inefficiencies within actively operating websites and specific pages that leads to excessive bandwidth consumption and reduced server performance.

Traffic Ray allows you to filter stats and visualizations by specific IP address, Hosted website name as well as by entering fragments of Splunk query directly into the dashboard input.
Summary information tables offers extra sorting and drilldown features to dig deeper into details of every IP address or specific Website activity.


== Installation and Setup ==

Traffic Ray uses standard Apache Web server logfiles as the main source of data.
These logs files usually match Splunk sourcetypes of: 'access_combined' or 'access_combined_wcookie'.
Before you can see your Web traffic data within Traffic Ray you need to create index to store data from your apache Web logs and create data inputs.

- Install Traffic Ray app first.
   - Login to your Splunk instance as admin.
   - Go to Apps -> Manage Apps and follow installation instructions available at that screen to install Traffic Ray app.

- Create index (or indexes) to store data from your apache Web logs.
   - Login to your Splunk instance as admin
   - Go to: Settings -> Indexes -> [New].
   - Enter the index name - make sure it starts with 'apache_', for example: 'apache_domlogs' or 'apache_acc_logs'
     Traffic Ray app uses the following base query to retrive data:
     'index=apache_* sourcetype=access_combined*  ... ' -- and hence make sure your indexes are named as apache_*
   - You may leave all other fields empty/at their default values.
   - Press [Save]

- Create data inputs to point to directories on your server where Apache log files are generated (or received from forwarder).
   - Locate Apache web logs on your server. Run this command (as root user) to get an idea about the web logs location if you're not sure:
     lsof -nP -c apache2 -c httpd | grep -i s_log
   - To proceed with instructions lets assume that you've created an index named: 'apache_domlogs'
     and the location of your apache web logs on a server is: '/usr/local/apache/domlogs/'
   - Login to your Splunk instance as admin
   - Create Data input. Go to:
     Settings -> Data Inputs -> Files & directories -> [New]
   - "File or Directory" = /usr/local/apache/domlogs/*
   - "Blacklist" = (log\.offset|bytes_log|\-ftp_log|\-(200[0-9]|201[0-3])|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug)\-2014)
     This blacklist regex allows you to exclude FTP logs, irrelevant files and files dated older that September 2014.
     This allows you to limit amount of data inflow into Splunk to avoid overloading your Splunk license limit.
     Adjust it as you see fit.
   - Click [Next] button.
   - Sourcetype: click [Select], [Select Sourcetype], Web, access_combined
   - App Context -> [Traffic Ray]
   - Host -> [Regular Expression on path]
   - "Regular Expression" = [\\/]([^\\/A-Z]+\.[^\-A-Z]+)
     This regular expression allows Traffic Ray to extract domain or subdomain name from the name of the actual log file.
   - Index -> [apache_domlogs]
   - Press [Review] button
   - Press [Submit] button.

Once you completed creation of data input Splunk start indexing your data and you may navigate to Traffic Ray dashboards and start seeing stats almost immediately.


== More Information ==

More information and instructions are available at Traffic Ray website:
http://trafficray.com/


== Consulting ==

I am available for consulting and app development assignments.
Please contact me for assistance:
  Gleb Esman
  glebesman@gmail.com
  http://www.mensk.com/
