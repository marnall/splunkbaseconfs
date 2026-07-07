** Quick Guide | TL;DR **

Scroll down to read the full set of instructions (some content is repeated)

The EZproxy log format is customisable so you can either use the suggested config below - this will format the logs in a specific way and will have the appropriates props.conf and transforms.conf files to extract the fields to suit the app) or if you look at the instructions page or README file, it will advise on the appropriate field mappings. 

Note - any values in all CAPS, you will need to change e.g. "monitor://PATH TO INSTALL DIRECTORY\EZProxy\messages.txt" - this will need to be updated to your install path "monitor://var/log/EZproxy/messages.txt" 

Requirements:
	The applications only needs to be installed on a Search Head - note, you might need to set a props.conf on your Indexer if you are experiencing issues with time formatting/zones.
	In order to get most of the app, it's recommended that you install the User Agent Strings (https://splunkbase.splunk.com/app/1843/) application by Aplura LLC (please check license for suitability) in order to use the Browser/Client analysis dashboards.
	The app assumes that the index containing the EZproxy logs is searched by default.

config.txt
Add the following lines into your EZproxy config.txt (tested on EZproxy 6.5.1 GA) 

#Audit Config
Audit Most
Option LogUser
Option StatusUser

#EZProxy Logs
LogFormat %t\t%h\t%u\t%{ezproxy-groups}i\t%{ezproxy-session}i\t%{ezproxy-protocol}i\t%m\t%s\t%U\t%T\t%v\t%{user-agent}i\t%{referer}i\t%b
LogFile -strftime PATH TO INSTALL DIRECTORY\logs\ezp%Y%m.log

#SPU Logs
LogSPU -strftime LOGDIRECTORY\spu%Y%m%d.log %t\t%h\t%u\t%{ezproxy-groups}i\t%{ezproxy-session}i\t%s\t%{ezproxy-spuaccess}i\t%v\t%U\t%{user-agent}i\t%{referer}i

#Messages
Option RecordPeaks

#EZProxy Log Format

Other Settings

Location -file=GeoLite2-City.mmdb
Option BlockCountryChange

IntruderIPAttempts -interval=5 -expires=15 10
IntruderUserAttempts -interval=5 -expires=15 10
UsageLimit -enforce -interval=15 -expires=120 -MB=200 Global

/config.txt


Universal Forwarder - inputs.conf

[monitor://PATH TO INSTALL DIRECTORY\audit]
disabled = false
index = INDEX
sourcetype = ezproxy:audit

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\logs]
disabled = false
index = INDEX
sourcetype = ezproxy:urls
followTail = 0

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\messages.txt]
disabled = false
index = INDEX
sourcetype = ezproxy:messages

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\spu]
disabled = false
index = INDEX
sourcetype = ezproxy:spu

** /** Quick Guide | TL;DR **




** Instructions **

The EZproxy log format is customisable so you can either use the suggested config in the Quick Guide - this will format the logs in a specific way and has the appropriate props.conf and transforms.conf files to extract the fields in a CIM compliant way to suit the app. 

Alternatively, if you look at the instructions below it will advise on how to name the sourcetype and which field mappings to use. You will need to update the field extractions for SPU and URL logs. 


Requirements:
        The applications only needs to be installed on a Search Head - note, you might need to set a props.conf on your Indexer if you are experiencing issues with time zones.
        Splunk should be configured to send emails.
        In order to get most of the app, it's recommended that you install the User Agent Strings application by Dave Shpritz in order to use the Browser/Client analysis dashboards.
        Assumes that the index that contains EZproxy logs is searched by default.


Audit Logs - sourcetype=ezproxy:audit

Set the following config directives in your EZproxy config

Audit Most	
Option LogUser	
Option StatusUser

Field		CIM Model	CIM Compliant	Mapped to	Alias	Auto Lookup
Date/Time	Authentication	no		datetime		
Event		Authentication	yes		action_orig		action
IP		Authentication	yes		src		src_ip	
Username	Authentication	yes		user		
Session		Authentication	no		sessionid		
Other		Authentication	no		actionstatus		

If using a different log options, you may need to also set an event type of "sourcetype=ezproxy:audit" to "authentication" 


SPU Logs - sourcetype=ezproxy:spu

SPU - Starting Point URL - they can help you identify how people arrive on your EZproxy server, which sites are most popular etc. 

LogSPU -strftime LOGDIRECTORY*\spu%Y%m%d.log %t\t%h\t%u\t%{ezproxy-groups}i\t%{ezproxy-session}i\t%s\t%{ezproxy-spuaccess}i\t%v\t%U\t%{user-agent}i\t%{referer}i 

*adjust the path relevant to your installation 

Field			CIM Model	CIM Compliant	Mapped to	Alias
%t			Web		no		datetime	
%h			Web		yes		src	
%u			Web		yes		user	
%{ezproxy-groups}i	Web		no		ez_groups	
%{ezproxy-session}i	Web		no		sessionid	
%s			Web		yes		status	
%U			Web		yes		url		spu_url
%v			Web		yes		site		spu_site
%{user-agent}i		Web		yes		http_user_agent	
%{referer}i		Web		yes		http_referrer	



Logs - sourcetype=ezproxy:urls

LogFormat %t\t%h\t%u\t%{ezproxy-groups}i\t%{ezproxy-session}i\t%{ezproxy-protocol}i\t%m\t%s\t%U\t%T\t%v\t%{user-agent}i\t%{referer}i\t%b
LogFile -strftime PATH TO INSTALL DIRECTORY**\logs\ezp%Y%m.log 

**adjust the path relevant to your installation 

Field			CIM Model	CIM Compliant	Mapped to	Alias
%t			Proxy		no		datetime	
%h			Proxy		yes		src		src_ip
%u			Proxy		yes		user	
%{ezproxy-groups}i	Proxy		no		groups	
%{ezproxy-session}i	Proxy		no		sessionid	
%{ezproxy-protocol}i	Proxy		no		protocol	
%m			Proxy		yes		http_method	
%s			Proxy		yes		status	
%U			Proxy		yes		url	
%T			Proxy		yes		duration	
%v			Proxy		yes		site	
%{user-agent}i		Proxy		yes		http_user_agent	
%{referer}i		Proxy		yes		http_referrer	http_referer
%b			Proxy		yes		bytes	

If using a different log format, you will need to delete the existing field extractions and create a new one using the schema above.


Messages - sourcetype=ezproxy:messages

You can't change the messages format, but you can config EZproxy to record additional log messages, one is RecordPeaks, this checks the maximum number of users sessions, concurrent transfer and virtual hosts every minute and if a new peak value is reached it will write to the the messages.log file.

Option RecordPeaks 


Other Settings

There are settings that you should consider setting to improve the security of your EZproxy service. The following settings will block a session*** if the users country changes within a single session, block an IP/User for repeated failed authentication attempts and enforce a usage limit (set as appropriate to your organisation). 

***you will need some additional files on your installation - see Block Country Change for further info. 

Location -file=GeoLite2-City.mmdb
Option BlockCountryChange

IntruderIPAttempts -interval=5 -expires=15 10
IntruderUserAttempts -interval=5 -expires=15 10
UsageLimit -enforce -interval=15 -expires=120 -MB=200 Global


Further info is available on the OCLC Website
Intruder IP - https://help.oclc.org/Library_Management/EZproxy/Configure_resources/IntruderIPAttempts
Intruder Username - https://help.oclc.org/Library_Management/EZproxy/Configure_resources/IntruderUserAttempts
Usage Limit - https://help.oclc.org/Library_Management/EZproxy/Configure_resources/UsageLimit


Universal Forwarder Setup- inputs.conf 
You'll need to install a Universal forwarder to collect/forward the logs to your Splunk instance, below is a suggested configuration for inputs.conf

[monitor://PATH TO INSTALL DIRECTORY\audit]
disabled = false
index = INDEX
sourcetype = ezproxy:audit

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\logs]
disabled = false
index = INDEX
sourcetype = ezproxy:urls
followTail = 0

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\messages.txt]
disabled = false
index = INDEX
sourcetype = ezproxy:messages

[monitor://PATH TO INSTALL DIRECTORY\EZProxy\spu]
disabled = false
index = INDEX
sourcetype = ezproxy:spu


Links

EZproxy Website - https://www.oclc.org/en/ezproxy.html/
EZproxy Support Website - https://help.oclc.org/Library_Management/EZproxy

** /Instructions **
