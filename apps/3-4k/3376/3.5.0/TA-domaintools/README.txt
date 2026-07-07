
# DomainTools for Splunk
Author: **DomainTools LLC**
Version: **3.5.0**
Source type(s): **None**
Input requirements: **None**
Index-time operations: **False**
Supported product(s): **DomainTools API**

## Using this Add-on:
Configuration: **Manual**
Ports for automatic configuration: **None**
Scripted input setup: **Not Applicable**

## Installation
For complete details, including support contacts and a free API trial, visit domaintools.com/splunk

Please review the deployment guide to get started. You'll find the guide at the above URL and also in the /resources folder of this app.


## Custom search commands
### domaintools mode='mode' [field='field'] 'domain'

	This command is used to query the DomainTools API. The 'field' option is only used with the Iris APIs.

Ad-Hoc Modes

	domain_profile - Domain Profile API
		Basic registrant, server, and registration data for a domain name, plus preview data for other products

	hosting_history - Hosting History API
		Provides the registrar, IP and name server history for a domain name

	ip_monitor - IP Monitor API
		Receive notification when there are new and/or deleted domains on a given IP Address

	reputation - Domain Reputation API
		Provides risk scores based on a domain's proximity to known-bad domains

	risk - Domain Risk Score API
		Provides risk scores and threat predictions based on DomainTools Proximity and Threat Profile algorithms

	whois - Whois Lookup API
		Whois records for domain names and IP addresses

	whois_history - Whois History API
		Historical Whois records

	whois_parsed - Parsed Whois API
		Parsed results for Whois records for domain names and IP addresses

	registrant_alert - Registrant Monitor API
		Receive notification when specific people or organizations register, renew or delete domain names

	reverse_ip - Reverse IP API
		List of domains that share the same network host

	reverse_ns - Reverse Name Server API
		List of domains that share the same primary name server

	reverse_whois - Reverse Whois API
		Provides a list of domain names with Whois records that match a specific query

Enrichment Modes

	iris_enrich - Iris Enrich API


	whois_reputation - Parsed Whois API & Domain Reputation API
		Parsed results for Whois records for domain names and IP addresses
		Provides risk scores based on a domain's proximity to known-bad

	whois_risk - Parsed Whois API & Domain Risk Score API
		Parsed results for Whois records for domain names and IP addresses
		Provides risk scores and threat predictions based on DomainTools Proximity and Threat Profile algorithms

### tldextract 'url'
Returns the extracted domain name from the tldextract third-party python library

Url:
		- A URL or domain.

## Scheduled Searches

### DomainTools Enterprise - Domain Name Queue Builder KV Store
Enabled: **False**
Schedule: **Every 5 Minutes**
Search:

	| `dt_base_search` | eval _key=domain|tldextract domain_field=domain | eval domain=lower(domain)| search NOT rank=* AND domain=* AND domain!=*in-addr.arpa | lookup whois_lookup_queue _key OUTPUT domain AS domainInQ|search NOT domainInQ=*|dedup domain|eval key=domain|table key domain fooyn queued|eval queued=if(isnull(queued) OR NOT queued>0,now(),queued), fooyn=if(isnull(fooyn) OR NOT fooyn>0,now(),fooyn)|outputlookup key_field=key whois_lookup_queue

Description:

	This query will add domains to the whois_lookup_queue KV table to be enriched

### DomainTools Enterprise - API Enrichment First Pass KV Store
Enabled: **False**
Schedule: **Every 5 Minutes**
Search:

	|from inputlookup:whois_lookup_queue| lookup whois_lookup_history domain OUTPUT domain AS domainInHistory|search NOT domainInHistory=*|sort - queued|head `cron_limit`|`dt_api_enrich_cmd` |  rename orig_domain AS key | eval created = strptime(parsed_whois_created_date, "%Y-%m-%dT%H:%M:%S") | eval expires=strptime(parsed_whois_expired_date, "%Y-%m-%dT%H:%M:%S") | eval retrieved=now() | eval qwaittime=(retrieved-queued)|eval updated=strptime(parsed_whois_updated_date, "%Y-%m-%dT%H:%M:%S")  |rename parsed_whois_name_servers AS nameservers, parsed_whois_registrar_name AS registrar, parsed_whois_contacts_registrant_country AS registrant_country, parsed_whois_contacts_registrant_email AS registrant_email, parsed_whois_contacts_registrant_org AS registrant_org, parsed_whois_contacts_admin_country AS admin_country, parsed_whois_contacts_admin_email AS admin_email, parsed_whois_contacts_tech_email AS technical_email, parsed_whois_contacts_tech_country AS technical_country, parsed_whois_contacts_tech_email AS technical_email| table key domain fooyn qwaittime queued retrieved created expires updated nameservers registrant registrar registrant_country registrant_email registrant_org admin_country admin_email technical_country technical_email risk_score components|outputlookup key_field=key whois_lookup_history|collect index=whois sourcetype=Whois:DomaintoolsApp

Description:

### DomainTools Enterprise - API Enrichment Second Pass KV Store
Enabled: **False**
Schedule: **Every 6 Hours**
Search:

	|from inputlookup:whois_lookup_queue| lookup whois_lookup_history domain OUTPUT domain AS domainInHistory|eval sinceTime=now()-`max_age_queue_item_minutes`*60|search NOT domainInHistory=* AND domain=*|where queued<sinceTime|sort - queued|head `cron_limit`|`dt_api_enrich_cmd` |  eval key = domain | eval created = strptime(parsed_whois_created_date, "%Y-%m-%dT%H:%M:%S") | eval expires=strptime(parsed_whois_expired_date, "%Y-%m-%dT%H:%M:%S") | eval retrieved=now() | eval qwaittime=(retrieved-queued)|eval updated=strptime(parsed_whois_updated_date, "%Y-%m-%dT%H:%M:%S")  |rename parsed_whois_name_servers AS nameservers, parsed_whois_registrar_name AS registrar, parsed_whois_contacts_registrant_country AS registrant_country, parsed_whois_contacts_registrant_email AS registrant_email, parsed_whois_contacts_registrant_org AS registrant_org, parsed_whois_contacts_admin_country AS admin_country, parsed_whois_contacts_admin_email AS admin_email, parsed_whois_contacts_tech_email AS technical_email, parsed_whois_contacts_tech_country AS technical_country, parsed_whois_contacts_tech_email AS technical_email| table key domain fooyn qwaittime queued retrieved created expires updated nameservers registrant registrar registrant_country registrant_email registrant_org admin_country admin_email technical_country technical_email risk_score components|outputlookup key_field=key whois_lookup_history

Description:

### DomainTools Iris - Domain Name Queue Builder KV Store
Enabled: **True**
Schedule: **Every 5 Minutes**
Search:

	| dt_base_search | eval orig_domain=domain|tldextract domain_field=domain | search NOT rank=* AND domain=* | lookup iris_lookup_queue _key OUTPUT domain AS domainInQ|search NOT domainInQ=*|dedup domain|eval key=domain|table key domain fooyn queued|eval queued=if(isnull(queued) OR NOT queued>0,now(),queued), fooyn=if(isnull(fooyn) OR NOT fooyn>0,now(),fooyn)|outputlookup key_field=key iris_lookup_queue`

Description:

	This query will add domains to the iris_lookup_queue KV table to be enriched


### DomainTools Iris - API Enrichment First Pass KV Store
Enabled: **True**
Schedule: **Every 5 Minutes**
Search:

	|from inputlookup:iris_lookup_queue| lookup iris_lookup_history domain OUTPUT domain AS domainInHistory|eval sinceTime=now()-`max_age_queue_item_minutes`*60|search NOT domainInHistory=* AND domain=*|where queued>=sinceTime|sort - queued|head `cron_limit`|`dt_api_enrich_cmd` | table key, domain, fooyn, qwaittime, queued, retrieved, registrant_contact_org, ip_2_asn_1, redirect_domain, alexa, registrant_contact_state, google_analytics, ip_1_country_code, ip_1_isp, admin_contact_name, billing_contact_state, technical_contact_postal, technical_contact_fax, _time, whois_url, billing_contact_name, technical_contact_phone, name, adsense, registrant_contact_phone, soa_email_1, technical_contact_name, ip_2_address, email_domain_2, admin_contact_fax, technical_contact_country, email_domain_1, create_date, website_response, active, registrar, technical_contact_state, admin_contact_phone, billing_contact_fax, name_server_1_host, registrant_contact_name, additional_whois_email_1, registrant_contact_street, admin_contact_city, billing_contact_city, name_server_2_ip_1, name_server_2_domain, registrant_name, registrant_contact_postal, data_updated_timestamp, admin_contact_org, name_server_1_ip_1, ip_2_isp, tld, registrant_org, risk_score, billing_contact_street, billing_contact_phone, admin_contact_postal, registrant_contact_country, admin_contact_country, registrant_contact_city, ip_1_asn_1, spf_info, admin_contact_street, registrant_contact_fax, technical_contact_street, redirect, billing_contact_postal, admin_contact_state, billing_contact_org, technical_contact_org, ip_1_address, billing_contact_country, technical_contact_city, name_server_2_host, ip_2_country_code, name_server_1_domain, expiration_date, mx_1_ip_1, ssl_info_1_hash, ssl_info_1_organization, priority, mx_1_domain, ssl_info_1_subject, mx_1_host, admin_contact_email_1, registrant_contact_email_1, name_server_2_ip_2, technical_contact_email_1, name_server_1_ip_2, note, proximity, threat_profile, threat_profile_malware, threat_profile_phishing, threat_profile_spam|outputlookup key_field=key iris_lookup_history


Description:

### DomainTools Iris - API Enrichment Second Pass KV Store
Enabled: **True**
Schedule: **Once per hour**
Search:

	|from inputlookup:iris_lookup_queue| lookup iris_lookup_history domain OUTPUT domain AS domainInHistory|eval sinceTime=now()-`max_age_queue_item_minutes`*60|search NOT domainInHistory=* AND domain=*|where queued<sinceTime|sort - queued|head `cron_limit`|`dt_api_enrich_cmd` | table key, domain, fooyn, qwaittime, queued, retrieved, registrant_contact_org, ip_2_asn_1, redirect_domain, alexa, registrant_contact_state, google_analytics, ip_1_country_code, ip_1_isp, admin_contact_name, billing_contact_state, technical_contact_postal, technical_contact_fax, _time, whois_url, billing_contact_name, technical_contact_phone, name, adsense, registrant_contact_phone, soa_email_1, technical_contact_name, ip_2_address, email_domain_2, admin_contact_fax, technical_contact_country, email_domain_1, create_date, website_response, active, registrar, technical_contact_state, admin_contact_phone, billing_contact_fax, name_server_1_host, registrant_contact_name, additional_whois_email_1, registrant_contact_street, admin_contact_city, billing_contact_city, name_server_2_ip_1, name_server_2_domain, registrant_name, registrant_contact_postal, data_updated_timestamp, admin_contact_org, name_server_1_ip_1, ip_2_isp, tld, registrant_org, risk_score, billing_contact_street, billing_contact_phone, admin_contact_postal, registrant_contact_country, admin_contact_country, registrant_contact_city, ip_1_asn_1, spf_info, admin_contact_street, registrant_contact_fax, technical_contact_street, redirect, billing_contact_postal, admin_contact_state, billing_contact_org, technical_contact_org, ip_1_address, billing_contact_country, technical_contact_city, name_server_2_host, ip_2_country_code, name_server_1_domain, expiration_date, mx_1_ip_1, ssl_info_1_hash, ssl_info_1_organization, priority, mx_1_domain, ssl_info_1_subject, mx_1_host, admin_contact_email_1, registrant_contact_email_1, name_server_2_ip_2, technical_contact_email_1, name_server_1_ip_2, note, proximity, threat_profile, threat_profile_malware, threat_profile_phishing, threat_profile_spam|outputlookup key_field=key iris_lookup_history

Description:


### DomainTools Enterprise - Whois Index Populator
Enabled: **False**
Schedule: **Every 5 Minutes**
Search:

	| `dt_base_search` | eval orig_domain=domain|tldextract domain_field=domain | eval domain=lower(domain) | search NOT rank=* AND domain=* AND domain!=*in-addr.arpa |eval _key=domain|table *|lookup `dt_lookup_history` _key|search risk_score=*|table key domain fooyn qwaittime queued retrieved created expires updated nameservers registrant registrar registrant_country registrant_email registrant_org admin_country admin_email technical_country technical_email risk_score components _time|collect index=whois sourcetype=Whois:DomaintoolsApp

### DomainTools Iris - Whois Index Populator
Enabled: **False**
Schedule: **Every 5 Minutes**
Search:

	| `dt_base_search` | eval orig_domain=domain|tldextract domain_field=domain | eval domain=lower(domain) | search NOT rank=* AND domain=* |eval _key=domain|table *|lookup iris_lookup_history _key|search risk_score=*|collect index=whois sourcetype=Whois:DomaintoolsApp


### DomainTools Threat Hunting - Total Domain Event Count Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history`| eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime|dedup domain|table domain|stats count AS TotalDomainEventCount | collect index=`summary_index`


### DomainTools Threat Hunting - Newly Observed Domains Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` | eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime|dedup domain|table domain|stats count as NewlyObservedDomainCount | collect index=`summary_index`


### DomainTools Threat Hunting - Registrant Country Codes from High Risk Domains
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` |eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime and risk_score>=70|dedup domain|search registrant_contact_country=*|eval iso2=upper(registrant_contact_country)|lookup geo_attr_countries iso2 OUTPUT country|stats count by country |collect index=`summary_index`


### DomainTools Threat Hunting - Risk Classification Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` | eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime and (risk_score >= 50) |dedup domain| eval created=if(match(coalesce(created,create_date),"^\\d{4}-\\d{2}-\\d{2}$"),strptime(coalesce(created,create_date),"%Y-%m-%d"),coalesce(created,create_date)) | search (created=* NOT created="unknown") | eval expires=coalesce(expires,expiration_date)|eval age=ceil(((now() - created) / 86400)) | eval orig_domain=domain | sort - "Malware"=8-30000265 "Spam"=30000265-480 | stats count by range | eval RiskClassification=range | collect index=`summary_index`

### DomainTools Threat Hunting - Risk Level Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history`|eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime|dedup domain| eval RiskLevel=case(risk_score<50,"Very Low",risk_score>=50 and risk_score<70,"Low",risk_score>=70 and risk_score<90,"Moderate",risk_score>=90 and risk_score<95,"High",risk_score>=95 and risk_score<100,"Very High",risk_score=100,"Extreme") |stats count by RiskLevel| collect index=`summary_index`


### DomainTools Threat Hunting - Risky Registrant Emails Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` | eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime and risk_score>`min_tp_risk` |dedup domain|eval registrant_email=coalesce(registrant_email,registrant_contact_email_1)|stats count(registrant_email) by registrant_email|collect index=`summary_index`


### DomainTools Threat Hunting - Risky Registrants Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` | eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime and risk_score>`min_tp_risk` |dedup domain|eval registrant=coalesce(registrant,registrant_contact_name)|stats count(registrant) by registrant|collect index=`summary_index`


### DomainTools Threat Hunting - Risky Registrars Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history` | eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime and risk_score>`min_tp_risk` |dedup domain|table registrar|stats count(registrar) by registrar|collect index=`summary_index`


### DomainTools APIUsageCount Summary
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history`|eval sinceTime=now()-`summary_search_run_interval`*60|where retrieved>=sinceTime|dedup domain|table domain|stats count as APIUsageCount|collect index=`summary_index`


### DomainTools Threat Hunting - Diagnostics - API Overage Analysis Summary Index
Enabled: **True**
Schedule: **Every 15 Minutes**
Search:

	|from inputlookup:`dt_lookup_history`|eval sinceTime=(now()-(`summary_search_run_interval`*60))|where queued>=sinceTime AND retrieved=0|dedup domain|table domain|stats count as APIOverageCount|eval APIOverageCount = max(0,APIOverageCount-(`per_minute_limit`*15))|collect index=`summary_index`

### DomainTools for Enterprise Security - High Risk Score Correlation Search
Enabled: **True**
Schedule: **Every 5 Minutes**
Search:

	|`dt_base_search` |tldextract domain_field=domain|eval domain=lower(domain)|dedup domain|table domain|eval _key=domain|lookup `dt_lookup_history` _key OUTPUT domain AS dtdomain, risk_score| where risk_score >= `min_tp_risk` |dedup domain| rename domain AS dest | table _time dest risk_score

### DomainTools Maintenance - Remove Failed Domains From Queue KV Store
Enabled: **True**
Schedule: **Every Day at 12:01 AM**
Search:

	|from inputlookup:`dt_lookup_queue` |eval sinceTime=(now()-`data_queue_length`)|where queued>sinceTime|lookup whois_lookup_queue domain|outputlookup `dt_lookup_queue`


### DomainTools Maintenance - Expire Stale Cache Entries in KV Store
Schedule: **Every Day at 12:01 AM**
Search:

	|from inputlookup:`dt_lookup_history` |eval sinceTime=(now()-`data_cache_length`)|where retrieved>sinceTime|eval _key=domain|lookup `dt_lookup_history` _key|outputlookup `dt_lookup_history`


## Lookup tables

### KeyValue
	whois_lookup_history
		Used to cache DomainTools whois data.

	whois_lookup_queue
		Used to queue domains for enrichment with the whois APIs.

	iris_lookup_history
		Used to cache DomainTools Iris data.

	iris_lookup_queue
		Used to queue domains for enrichment with the Iris APIs.

### CSV
	dtools_watchlist
		Used for alerting on matching components of a domain.

	public_suffix_list
		Used by tldextract.

## Macros

    You can see the details of the macros below by viewing them in the advanced search section of the splunk UI or by viewing the contents to the macros.conf file.

### dt_base_search
This is the source of the data to enrich. The output of these events must include a field (re)named domain which contains a URL, FQDN, or domain. The tldextract library will successfully extract many URLs and subdomains to the base domain root.

	definition = search url=*| rename url AS domain

### min_tp_risk
This is the value returned by the risk or reputation API that will generate an alert in SplunkES.

	definition = 90

### min_prox_risk
Minimum proximity score.

	definition = 70

### dt_api_enrich_cmd
This is the enrichment command used to retrieve data from the APIs.

	definition = domaintools domain mode=iris_enrich field=domain silent=t

### data_cache_length
This is the amount of time, in seconds, to keep data in the whois_lookup_history table.

	definition = 2592000

### data_queue_length
This is the amount of time, in seconds, to keep data in the whois_lookup_queue table.

	definition = 86400

### per_minute_limit
This is the per minute query rate limit for the APIs.

	definition = 60

### populating_search_run_interval
This is the interval, in minutes, that the populating search is run.

	definition = 5

### cron_limit
This is the multiplier used by the populating search to limit the number of rows returned on each run.

	definition = 270
IMPORTANT: runs are assumed to run every five minutes with a 60/minute rate, and then are backed off 10% to allow for ad-hoc invesigative queries. IF the populating search is run at a longer interval, such as 15 minutes, then this value should be manually adjusted using this formula:

==cron_limit = ((per_minute_limit) * populating_search_run_interval) * 0.9==

### score_type
This is the "mode" to use for risk score API queries to the command "domaintools." Must be one of 'risk' or 'reputation'.

	definition = risk

### summary_index
This is the index to use for the summary data. The default is "summary."

	definition = summary

### dt_lookup_queue
This is the queue to use based on configured APIs. The default is "iris_lookup_queue."

	definition = iris_lookup_queue

### dt_lookup_history
This is the history KV table to use based on configured APIs. The default is "iris_lookup_history."

	definition = iris_lookup_history

### young_domain_age
This is the age, in days, to use for determining if a domain registration is "young."

	definition = 7

### young_domains
This will find "young" domains (based on the young_domain_age macro) present in the lookup cache

	definition = from inputlookup:`dt_lookup_history`|eval domain_created=if(match(created,"^\\d{4}-\\d{2}-\\d{2}"),strptime(created,"%Y-%m-%d"),created) | eval age=ceil((now()-domain_created)/86400)|where age<=`young_domain_age`|dedup domain

### young_domain_age_drilldown

	definition = eval cd=strptime(create_date, "%Y-%m-%d")|eval age=ceil((now()-coalesce(cd,created,create_date))/86400)|search age&lt;=`young_domain_age`


## Workflow Actions

### dts_es_whois_domainprofile_dashboard
  This action allows notable events to be opened in the Domain Profile dashboard.

### dts_es_iris
	This action allows notable events to be opened in IRIS.
