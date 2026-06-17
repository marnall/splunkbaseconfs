Splunk for Oracle Audit Trail

Author: Balazs Vamos <vamos.balazs@zuriel.hu>
Version: 1.1
Last modified: 2011-12-22


Release notes
=============

1.1 - 2011-12-22
  - New sourcetype: oracle_syslog. Sourcetype is generated at index time based on the format of events sent
    via standard syslog input.
  - Modified menu structure
  - Default index on Search page has been set
  - Workflow for searching Oracle Error Messages based on RETURNCODE field
  - Fixed field name (oracle_actionname) in 'Top audit actions' saved report
  - Default input added. TCP:9996, sourcetype=syslog, index=oracleaudit

1.0 - 2011-12-17 - Initial release


Description
===========

With Splunk for Oracle Audit Trail application you can analyze your Oracle Audit Trails sent via syslog. 
It contains predefined field extractions, field value lookups, form searches, charts and reports.


Usage
=====

There is a predefined syslog input on port TCP 9996. You can configure your syslog daemon (rsylsog, 
syslog-ng, etc.) to send Oracle syslog to this port. To change por edit local/inputs.conf.
This app will recognize Oracle Audit Trails sent via syslog and will set sourcetype to oracle_syslog.
Key-value pairs will be extracted from the Oracle syslog message.
