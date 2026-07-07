# OpenLDAP® Add-on for Splunk®


* OpenLDAP Add-on for Splunk provides CIM compliant field extractions and data enrichment for your OpenLDAP data.


# Version 1.2.2


# Release Notes


1.2.2: January 2019
- Minor fixes to pass AppInspect

1.2.1: January 2019
- Only updated version reference (1.x.x instead of 1.x) to meet standards

1.2: April 2017
- Scheduled saved searches are now enabled by default	
- Documentation has been modified
		
1.1: March 2017
- Fixed a typo in a scheduled saved search (a dedup was missing)

1.0: March 2017
- Initial release
	
		
# Install OpenLDAP Add-on for Splunk:


	Deploy OpenLDAP Add-on for Splunk on your Splunk platform. 
	
	
	In distributed environments, OpenLDAP Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s). In this scenario, both scheduled saved searches need to be disabled on Indexer(s). This can be done from Settings : Searches, reports, and alerts : Status having "OpenLDAP Add-on for Splunk" as app context.
	
		
# Collect OpenLDAP logs


	Your Splunk Universal Forwarder deployed on the server hosting OpenLDAP should be configured to monitor OpenLDAP's logs and forward it to your Splunk Indexer or Intermediate Forwarder.


	To achieve this, a local inputs.conf should be manually configured or deployed via a Deployment Server to monitor openldap.log file which default location is /var/log/openldap/ directory.


	A sample configuration is provided in the Add-on README directory:


	[monitor:///var/log/openldap/openldap.log]	
	sourcetype = openldap:access


	If needed, please refer to "Monitor files and directories using the Universal Forwarder" on Splunk Docs.


	OpenLDAP data can be indexed in the default main index as well as in a dedicated one.


	If data is indexed in a dedicated index, this index must be searchable by default by the relevant role. This can be configured under Settings: Access controls : Roles : <Role to edit> : OpenLDAP dedicated index (if any) must be added to "Indexes" as well as to "Indexes searched by default".
	
	
# KV store collections dynamically updated by scheduled saved searches

	
	This Add-on maintains two KV store lookups.
	
	
	The "openldap_user_lookup" maintains a mapping between the connection code ("conn") and its related user ("cn") from BIND events such as:
	
	
	slapd[6088]: conn=1 op=3 BIND dn="cn=user1,ou=methodes,ou=projects,dc=example,dc=com" method=128
	
	
	The "openldap_src_lookup" maintains a mapping between the connection code ("conn") and its related source IP ("src_ip") from ACCEPT events such as:
	
	
	slapd[6088]: conn=1 fd=276 ACCEPT from IP=192.126.1.10:56570 (IP=10.10.10.10:636)
	
	
	The goal of maintaining such lookups is to provide CIM compliant fields for authentication event datasets.
	
	
	The error number ("err") provides the LDAP result code returned from the operation performed.
	
	
	The event containing the error number is straightforward:
	
	
	slapd[6088]: conn=1 op=3 RESULT tag=97 err=49 text=
	
	
	Therefore, it had to be enriched with "src", "dest", and "user" fields using automatic lookups for authentication event datasets.
	
	
	To update these lookups, two scheduled saved searches – "Update openldap_src_lookup KV Store collection" and "Update openldap_user_lookup KV Store collection" - run every two minutes.
	
	
	You might want to populate these lookups with older data. To do this, simply execute both scheduled saved searches once on a wider time frame.
	
	
	This can be achieved from Settings : Searches, reports, and alerts : Run (App context: OpenLDAP Add-on for Splunk).
	
	
# OpenLDAP service restart

	
	Note that the connection id used in both user and source IP lookups is not unique. It is rebuilt whenever openldap is restarted.
	
	
	That scenario has not been integrated to the add-on yet.
	
	
	If the openldap service is restarted, both lookups will be progressively updated by the scheduled searches but the remaining mappings will provide erroneous results.
	
	
	In that case, both KV store lookups should be purged.
	
	
	This can be achieved by executing the following searches:
	
	
	"| inputlookup openldap_user_lookup | eval key=_key | WHERE NOT key=_key | outputlookup openldap_user_lookup"
	
	
	"| inputlookup openldap_src_lookup | eval key=_key | WHERE NOT key=_key | outputlookup openldap_src_lookup"
	
	
	The drawback of purging these lookups is that it will not be possible to retrieve mappings in historical searches.


# Sourcetype:


	The configured sourcetype is "openldap:access"


# CIM Tags:


	Authentication
	
	
# Reference:


	https://www.centos.org/docs/5/html/CDS/cli/8.0/Configuration_Command_File_Reference-Access_Log_and_Connection_Code_Reference-Access_Log_Content.html


# For any help on this Add-on, contact splunk@nomios.fr



