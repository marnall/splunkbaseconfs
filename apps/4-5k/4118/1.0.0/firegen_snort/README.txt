Firegen for Snort App version 1.0.

Copyright (C) 2018 Adrian Grigorof All Rights Reserved.

The Firegen for Snort app provides several dashboards with statistics compiled from data recorded by Snort and stored in MySQL database by Barnyard2.


Configuration instructions:

Snort may be installed on a different server than Splunk but Splunk needs to have access to the MySQL database that stores the Snort events. In our case, we have a dedicated Snort server with a Splunk heavy forwarder installed to send the events to the indexer and the Splunk DB Connect App is installed on the heavy forwarder.

Configure Snort 2.9.9.x, Barnyard2, PulledPork and BASE as described in https://s3.amazonaws.com/snort-org-site/production/document_files/files/000/000/122/original/Snort_2.9.9.x_on_Ubuntu_14-16.pdf

The document describes the installation in full details for both Ubuntu 14 and 16.

Barnyard2 is an open source interpreter for Snort unified2 binary output files. Its primary use is allowing Snort to write to disk in an efficient manner and leaving the task of parsing binary data into various formats to a separate process that will not cause Snort to miss network traffic. - https://github.com/firnsy/barnyard2. Barnyard2 also stores the Snort events into a MySQL database that will be used by the Splunk DB Connect.

Pulled Pork provides support for Snort and Suricata rule management such as automated downloading, parsing, state modification - https://github.com/shirkdog/pulledpork

BASE is the Basic Analysis and Security Engine. It is based on the code from the Analysis Console for Intrusion Databases (ACID) project. This application provides a web front-end to query and analyze the alerts coming from a SNORT IDS system. BASE is just optional and it is not need it by the Splunk app.

Install the Splunk DB Connect App from Splunkbase: https://splunkbase.splunk.com/app/2686/. The role of DB Connect is to extract the Snort events stored in the MySQL database and send them to a Splunk index. Configure the DB Connect as follows:

1. In the Configuration tab click on New Connection and fill up the details specific to your database. 
2. In the Data Lab tab, click New Input
3. Select the connection created in the step above and the database where the snort data is stored. In our case the connection is called snort_mysql and the database is called "snort"
4. In the SQL Editor window enter:

SELECT event.cid,event.timestamp,SUBSTRING_INDEX(snort.sensor.hostname,":",1) as "host",INET_NTOA(iphdr.ip_src) AS "src_ip",INET_NTOA(iphdr.ip_dst) AS "dst_ip",event.signature,signature.sig_gid,signature.sig_sid,signature.sig_name AS "description"
FROM `snort`.`event`,`snort`.`sensor`,`snort`.`signature`,`snort`.`iphdr`
WHERE event.cid > ?
AND event.signature=signature.sig_id AND event.sid=sensor.sid AND event.sid=sensor.sid AND event.cid=iphdr.cid
ORDER BY event.cid ASC

If your database is not called "snort" you need to adjust the SQL statement accordingly (i.e. replace snort.sensor.hostname with your_database.sensor.hostname.

5. Configure the Settings as follows:
Template (default)
Input type: Rising
Rising Column: cid
Checkpoint value: Unlock & Exit
Timestamp: Current index time
Query timeout: 30

6. Click on the Execute SQL to verify the SQL command (the query may return "no results")
7. Click Next to view the settings and Finish if everything is ok.
8. Install the Firegen for Splunk app and launch the app to initiate the setup process. The setup is requesting confirmation for the index used to store Snort events. By default is called "snort". The setup also can be used to specify an internal subnet. The app will use the internal subnet to identify internal servers.

For support and comments/suggestions, please contact Adrian Grigorof, adigrio@gmail.com or support@firegen.com.
