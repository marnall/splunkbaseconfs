# DNSTwist Add-on for Splunk

---

<br>
### Description

The DNSTwist Add-on for Splunk provides the | dnstwist search command to generate a large list of permutations based on a list of provided domain names.  This command was removed from ESCU v.3.40.0 and is referenced in the Brand Monitoring Analytical Story (https://research.splunk.com/stories/brand_monitoring/).

## Platform and hardware requirements

This topic discusses the underlying requirements for running the DNSTwist Add-on for Splunk.


## What versions of Splunk Enterprise does the app support?

DNSTwist Add-on for Splunk supports Splunk Enterprise versions 8.2.x and 9.0.x.

<br>

---

<br>

## Distributed Installation

This table provides a quick reference for installing this app onto a distributed deployment of Splunk Enterprise.

#### DNSTwist Add-on for Splunk
| Splunk Instance Type | Supported | Required | Comments |
|--|--|--|--|
| Search Heads | Yes | Yes | |
| Indexers | No | No |  |
| Heavy Forwarders | Yes | No | Supports Heavy Forwarder for enrichment creation |
| Universal Forwarders | No | No |  |



## Setup and Initial Configuration


### Configure Splunk Company Domains List
 1. Update lookup (domains.csv) with the list of company-owned domains to use.  Refer to the Lookup Definition for field names and values.


<br>

---

<br>

## Usage

<br>

**| dnstwist domainlist=domains.csv**

#### Performs word premutation on a list of domains provided under DA-ESS-ContentUpdate/lookup/domains.csv

<br>

**| dnstwist domain=www.splunk.com**

#### Performs word premutation on a single domain

<br>

**| dnstwist populate_from_cim=true**

#### Performs word premutation on cim_corporate_email_domains.csv and cim_corporate_web_domains.csv from Splunk_SA_CIM

<br>

---

<br>

## Lookup Definitions

<br>

### **domains.csv**  OR **cim_corporate_web_domains.csv**

| Field | Type | Possible Value(s) | Description |
|--|--|--|--|
domain | String | company.com | Domain name to reference to create list of look-alike domains. |