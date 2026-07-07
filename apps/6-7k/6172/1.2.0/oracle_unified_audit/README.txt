Oracle Unified Audit App for Splunk
by DATAPLUS
www.dataplus-al.com


1. REQUIREMENTS

1.1 Splunk requirements

This app uses Splunk DB Connect App to retrieve unified audit events from the Oracle database.
Connectivity to Oracle must have been configured (Oracle JDBC driver) for Splunk DB Connect App.

1.2 Oracle DB requirements 

An Oracle user is required to retrieve audit events from Splunk. Name of the user is optional.

Oracle SQL commands:
-----------------------------------------------------
create user AUDSPLUNK identified by <your_password>;
grant CREATE SESSION to AUDSPLUNK;
grant select on SYS.UNIFIED_AUDIT_TRAIL to AUDSPLUNK;
-----------------------------------------------------

Depending on volume and purge policies of Oracle audit trail, an index may be required on the Oracle table:
------------------------------------------------------------------------------------------------------
create index EVENT_TIMESTAMP_IDX on AUDSYS.AUD$UNIFIED (event_timestamp) tablespace <tablespace_name>;
------------------------------------------------------------------------------------------------------

2. SETUP

2.1 App Install

UI Install:
Install online from SplunkBase, or from the downloaded file.

OS (manual) Install:
To install manually extract the compressed package and put the main folder oracle_unified_audit 
under $SPLUNK_HOME/etc/apps folder. Restart Splunk.

2.2 Create the Index

Create a Splunk index to store Oracle unified audit events. Default index name is ora_unf_aud.
If using another than default, you must change the default index name in all macros (macros.conf) 
of this App and also in the DB Input entry (db_inputs.conf) for Splunk DB Connect 

2.3 Splunk DB Connect Data Input

* Create a DBx Identity
* Create a DBx Connection  
* Create a DBx Input

Template files are deployed for identities.conf, db_connections.conf and db_inputs.conf.
For UI install use the content of templates. For OS install rename the template files.
Environment specific settings to set up are indicated in each template.

Reminder:
EVENT_TIMESTAMP_UTC is the event timestamp on UTC, "rising" column and timestamp for _time field.
Ingestion of the UTC timestamp to Splunk's _time column uses the: 
DBx series 3.x.x - db_connections.conf, timezone = UTC
DBx series 2.x.x - props.conf, TZ = UTZ 

2.4 Oracle Application Schemas 

Edit the app_schema_lookup lookup definitions on lookup table file db_app_schema.csv, single field
APP_SCHEMA, to define your Oracle applications schema names. This will complete the right (1=True) 
value of transformed field SEO_APP for audit events related to objects of your Oracle applications.


3. APPLICATION

3.1 App fields

* Oracle fields of system view UNIFIED_AUDIT_TRAIL
* Oracle environment sys_context extracted or hardcode values
* Splunk transformed - SEO fields

3.2 Search Extra Options (SEO) fields

Logical 0/1 (false/true) fields. Transformed in App macros (macros.conf).
Define security events categorization.

SEO_SEC		Security events
SEO_ACC		Logon access events
SEO_ORA		Oracle (SYS-owned) objects events
SEO_DDL		Data definition events
SEO_DML		Data manipulation events
SEO_SE		Select, Execute and Read events
SEO_ERR		Error events
SEO_APP		Application schemas events
SEO_CURR_USER	Top-SQL execution event


4. DATAPLUS

Oracle database security software solutions and services

https://www.dataplus-al.com
