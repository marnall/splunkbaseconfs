Percona Server for MySQL Audit Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(authentication) for Percona Server for MySQL Audit in Splunk.

The field extraction only accepts local csv file logging from Percona Server for MySQL Audit.

================================================
Configuring Percona Server for MySQL Audit
================================================

1. Install and configure audit setting in my.conf (usually in /etc/my.cnf):
Following installation steps for reference, please review and adjust for your needs:

a. If you are using MySQL community server edition 8.X, extract and get the binary file audit_log.so, then copy to mysql plugin directory:
wget https://downloads.percona.com/downloads/Percona-Server-LATEST/Percona-Server-8.0.26-16/binary/redhat/8/x86_64/percona-server-server-8.0.26-16.1.el8.x86_64.rpm
mkdir Percona-Server
mv percona-server-server-8.0.26-16.1.el8.x86_64.rpm Percona-Server/
cd Percona-Server/
rpm2cpio percona-server-server-8.0.26-16.1.el8.x86_64.rpm | cpio -idmv
cp ./usr/lib64/mysql/plugin/audit_log.so /usr/lib64/mysql/plugin/

2. Enter mysql console, and install the plugin:
mysql -u root -p
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

3. Edit my.cnf to configure audit settings: 
vi /etc/my.cnf
plugin-load       = audit_log.so
audit_log_file    = /var/log/mysql/audit.log
audit_log_format  = CSV
audit_log_policy  = LOGINS
audit_log_handler = FILE

4. Create the log directory, grant permission to mysql process:
mkdir -p /var/log/mysql/
chown -R mysql:mysql /var/log/mysql
systemctl restart mysqld

Ref: https://www.percona.com/doc/percona-server/8.0/management/audit_log_plugin.html

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head and forwarder(Percona Server for MySQL DB Server), and optionally installed on Indexer/Heavy Forwarder.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as percona:mysql:audit:csv.

================================================
Known Limitations
================================================

N/A



================================================
Getting Support
================================================

This is an open source project and no active support is provided. If there is any issues, email to info@cybersecthreat.com during weekday business hours (GMT+8).




================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0.0   | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|