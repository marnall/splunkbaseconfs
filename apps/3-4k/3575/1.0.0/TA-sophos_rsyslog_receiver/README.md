# README #

sophos_rsyslog_receiver v0.1

### What is this app for? ###

* Quick summary

The Sophos RSyslog Receiver app provides a method of integrating Sophos SG and XG appliances with Splunk via Syslog.
The appliances are configured to send syslog data to a syslog server which has a Splunk forwarder installed, the app will monitor the /var/syslog folder for logs and send them into Splunk with correct sourcetypes and into separate indexes

### How do I get set up? ###

To use this app you need:

- A syslog server with a splunk forwarder installed
- A sophos XG or SG UTM configured to send syslog to the above server

Once you have the above set up, you should then create the indexes in Splunk to which your events will be sent, these are:

- netwifi - wifi protection events
- netops - system health events
- netav - AV scanner events
- netids - IDS log events
- netproxy - web proxy log events
- netfw - firewall log events

Once the above indexes are created, this app should be installed on the forwarder, at this point, the contents of /var/syslog will then start to be forwarded to Splunk

### Important Note ###

This will cause the entire contents of /var/syslog to be forwarded, including subfolders.  If this is not the folder you store syslog, then the monitor stanza in inputs.conf should be changed

Also, ensure that you log into subfolders in order for the host field to be correctly identified, e.g. logs from:

/var/syslog/uk-server-1

Will have the host field set to the value uk-server-1