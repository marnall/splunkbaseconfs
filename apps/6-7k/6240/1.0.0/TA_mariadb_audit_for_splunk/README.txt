MariaDB Audit Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(authentication) for MariaDB Audit in Splunk.

The field extraction only accepts local csv file logging from MariaDB Audit.

================================================
Configuring MariaDB Audit
================================================

1. Install and configure audit setting in my.conf (usually in /etc/my.cnf):
Following installation steps for reference, please review and adjust for your needs:

a. If you are using MySQL community server edition 5.X, extract and get the binary file server_audit.so, then copy to mysql plugin directory:
wget https://downloads.mariadb.org/f/mariadb-5.5.68/bintar-linux-x86_64/mariadb-5.5.68-linux-x86_64.tar.gz/from/http%3A//mirror.mephi.ru/mariadb/?serve -O mariadb-5.5.68-linux-x86_64.tar.gz
tar -zvxf mariadb-5.5.68-linux-x86_64.tar.gz

cp  ./mariadb-5.5.68-linux-x86_64/lib/plugin/server_audit.so /usr/lib64/mysql/plugin/

# Check plugin dir, default /usr/lib64/mysql/plugin/ for rpm installation
mysql -u root -p
SHOW GLOBAL VARIABLES LIKE 'plugin_dir';

2. Enter mysql console, and install the plugin:
INSTALL PLUGIN server_audit SONAME 'server_audit.so';
show variables like '%audit%';

3. Edit my.cnf to configure audit settings: 
vi /etc/my.cnf
server_audit_events='CONNECT'
server_audit_logging=on
server_audit_file_path = /var/log/mysql/
server_audit_file_rotate_size=200000000
server_audit_file_rotations=200
server_audit_file_rotate_now=ON

4. Create the log directory, grant permission to mysql process:
mkdir -p /var/log/mysql/
chown -R mysql:mysql /var/log/mysql
systemctl restart mysqld

Ref: https://mariadb.com/kb/en/mariadb-audit-plugin-log-format/

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head and forwarder(MariaDB DB Server), and optionally installed on Indexer/Heavy Forwarder.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as mariadb:audit:csv.

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