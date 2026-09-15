VERSION
1.0

DESCRIPTION
This is an Add-On for RFC 5424 syslog data formatted according to the specifications of IEC62351-14. It does the following actions:
1. Parses the incoming log
2. Normalization of the parsed data to make it CIM-compliant

INSTALLATION
Set sourcetype="ge_vernova_syslog" for all GE Renewable inputs.

Parsing
AVAILABLE FIELDS
The following fields from the log's header are extracted:

extracted filed				Equivalent RFC 5424 field
prival  					prival (enclosed by the less-than and greater-than signs)
appname 					APP-NAME
procid  					PROCID
msgid   					MSGID
host    					HOSTNAME

GE Renewable private parameters within the IEC@62351 structured data element. 

SEARCH TRICKS
To extract the FACILITY and SEVERITY values from the PRIVAL value:
    sourcetype="ge_vernova_syslog" | `convert_facility_severity`

To convert FACILITY values into text descriptions:
    sourcetype="ge_vernova_syslog" | `convert_facility_severity` | lookup facility_lookup facility

To convert SEVERITY values into text descriptions:
    sourcetype="ge_vernova_syslog" | `convert_facility_severity` | lookup severity_lookup severity

NORMALIZATION

Logging attributes			Alerts data model			Authentication data model
Severity 					severity					-
ID 							id							-
Text 						body						-
ProdName 					src							src
Source 						app							app
UsrID 						-							user
