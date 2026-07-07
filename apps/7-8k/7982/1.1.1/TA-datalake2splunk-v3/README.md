# Datalake2Splunk V3

# Decription

This is an add-on powered by the Splunk Add-on Builder.
This app provides the ability to ingest Orange Datalake threat intel given an api token

# Release Notes
## 1.0.0
### Features:
New fields available: threat_entities, sighting_sources and last_positive_sighting
### Configuration and Input:
- The Account page now displays Long Term Token as intended
- It is now possible to configure a cron schedule instead of just seconds for interval
- The API URL is customisable in the input (used to request preproduction environment)

### Script:
- Automatically constructed Lookups now contain atom_type and atom_value columns
-nBetter logging to ensure troubleshooting for each input

### Parsing:
- When ingested, data now have a new sourcetype datalake:indicators that includes new parsing for multivalue version of all attributes such as threat_source, threat_entity and sighting_source
- Macro datalake_parser updated to do the same parsing as the props does
- Updated savedsearches for lookup creation when data is indexed to reflect updated atom_types and new attributes

## 1.0.1
Fixed missing nav and views.

## 1.0.3
- Added Legacy lookup definitions for easier migration from V2
- Changed name of input_type to avoid conflicts between V2 and v3

## 1.0.5
- More internal logs
- Added data fetch report (IOC Collection)
- Added empty csv file to avoid errors in Dashboard
- Improved Dashboard and new collection dashboard
- Added IOC Collection Report
- Removed datalake_cve definition from macro datalake_parser
- Added conf_replication_include.account and conf_replication_include.settings in default/server.conf

## 1.0.6
- AppInspect check for Python 3.13 (Splunk 10.2)
- Dashboard IOC Viewer
- Updated Roadmap

## 1.0.7
changed [shclustering] stanza in server.conf to force replication of
ta_datalake2splunk_v3_account instead of juste account.

## 1.0.8
- added ta_datalake2splunk_v3_settings as well for shclustering replication (to replicate proxy configuration)
- New issue noticed : lookup csv file not replicated on all members on splunk cloud using sh cluster.
Workaround would be to use index mode and use the lookup gen search as the ouputlookup command triggers a replication to all members.

## 1.0.9
- Changed Lookup Gen searches so they match exactly lookup mode + description at the end for ES
- removed Build Datalake credit card lookup
- changed 'email' for 'src_user' in "Build Datalake email lookup" as 'email' is not a value accepted by email_intel kvstore
- Build Datalake file lookup outputs a 'file_hash' column instead of just file
- Build Datalake ip_range lookup outputs an 'ip' column for ES ip_intel
- Build Datalake certificate lookup outputs a 'certificate_file_hash' column instead of juste file because datalake gives hashes and it's ES supported field name
- No field values in ES for phone, asn and crypto

## 1.1.0
Some backslash missing for Datalake certificate and Datalake URL generating lookup searches.
Error at line 53,135,177,218,259,343,385,426 after by corrected
Updated known issues in README.md

## 1.1.1
Correction line 429 of savedsearches.conf | outputlookup datalake_url
Changed restmap.conf and inputs.conf to use python.required = 3.9  instead of python.version = python3 (compliance for Splunk Cloud 10.2)
Updated splunk_sdk, splunklib, splunktaucclib,ucc_restbuilder, splunk_add_on_ucc_framework
TRUNCATE=20000 on datalake:indicators sourcetype

## Roadmap : 
- P1 : Known issue :_csv.Error: line contains NUL --- need modifications in the script to remove null values usually inside datalake_url.
- P2 : Required Feature : add properties hashes.sha1, hashes.sha256 hashes.sha512 for file_hash atom_type
- P2 : python3.13 will be required soon for splunk 10.4 - need further testing
- P2 : Threat Match searches to create events in a summary index
- P3 : Convert dashboards to dashboard studio
- P3 : Custom Alert action to create sightings in Datalake

# Installation

## Migration instructions
It is not possible to collect indicators on Datalake API V2 with this addon. When migration occures, create new inputs on this addon and update hashes if there are some changes in atom_types requested.
## Splunk Cloud

If on Splunk Cloud classic, app must be installed on both Search Head and Input Data Manager. API / Input configuration is done on IDM and you have to enable indexing.

## Splunk Cloud Victoria Experience

Install app using Splunkbase directly from Splunk GUI

## On-prem single or distributed

If on an on-prem environnement, install the app on the Search Head. Indexing is optional. If your search Head doesn't have Internet Access, you can install it on another instance (Heavy Forwarder dedicated to API pulling and enable indexing). In that case you also need Datalake2SplunkV3 app on the Search Head to parse data into lookups.

If you use indexing, fill macro datalake-index with the index This index must be created first.

# Troubleshooting

All logs regarding the app are located in $SPLUNK_HOME/var/log/splunk/ta_datalake2splunk_v3_datalake2splunk.log Search :

 index=_internal sourcetype="tadatalake2splunk:log" 

# Known Issues
Splunk cloud shcluster might not replicate csv lookups to all members. The only workaround is to use the index mode and the savedsearch to fill the lookups and splunk to interpret them as new knowledge objetcs to be replicated.
Account not replicating on all members despite conf_replication_include.ta_datalake2splunk_v3_account = true : Only workarund is to manually logon to each search head of the cluster and add the account with same name.

# Support
cybersoc-splunkapps.ocd@orange.com

# Contributing
No Public contribution at the moment
