## SA-openVulnQuery

This supporting add-on provides one command -- `ovquery`. It is built on Cisco's PSIRT openVuln API and the Splunk SDK (note that this is not an offical product of Cisco).

Version: 1.1

Command reference:

# ovquery

## Description

The `ovquery` queries Cisco's PSIRT openVuln API and generates Splunk events from the results returned. Credentials must be generated and setup before command will work.

The command requires that the specific API filter (`get_by`) to query is specified (found at https://github.com/CiscoPSIRT/openVulnAPI/tree/master/openVulnQuery#api-filters-required) as well an appropriate `query` is specified for the filter. Returned by default is all fields of 'advisory\_id', 'sir', 'first\_published', 'last\_updated', 'cves', 'bug\_ids', 'cvss\_base\_score', 'advisory\_title', 'publication\_url', 'cwe', 'product\_names', and 'summary', though you can list only specific fields by providing a comma separated list to the command. The command expects by default a `get_by` and `query` option. The `query` value will depend on what the `get_by` value is set to.

## Syntax

ovquery get\_by=\<string> query="\<string>" \[adv\_type="\<string>"] \[fields="\<comma-seperated-field-list>"]

### Required arguments

 **get\_by**  
   	**Syntax:** get\_by=\<string> </br>
   	**Description:** Specify an API filter to query</br>
   	**Usage:** get\_by="all" | get\_by="advisory" | get\_by="cve" | get\_by="latest" | get\_by="serverity" | get\_by="year" | get\_by="product" | get\_by="ios" | get\_by="ios_xe"

 **query**  
   	**Syntax:** query="\<string>" </br>
   	**Description:** Specify an openVulnQuery API query based upon which get\_by filter is used </br>
   	**Usage:** i.e. query="3.7.2E" | query="10" | query="CVE-2018-0229"

### Optional arguments

 **adv_type**  
   	**Syntax:** adv\_type="\<string>" </br>
   	**Description:** Specify an advisory type format. </br>
   	**Usage:** i.e. adv\_type=cvrf | adv\_type=oval </br>
   	**Default:** cvrf

  **fields**  
   	**Syntax:** fields="\<comma-seperated-field-list\>"  </br>
   	**Description:** Name of the fields to limit the query to (note limiting the fields can decrease the query response time) </br>
   	**Usage:** i.e. fields="advisory\_id,sir" </br>
   	**Default:** all fields returned if not specified

## Examples

### **1: IOS XE version 3.7.2E** ###

`| ovquery get_by="ios_xe" query="3.7.2E"`

### **2: 10 most recent advisories** ###

`| ovquery get_by="latest" query="10"`

### **3: Search by specific CVE: 2018-0229** ###

`| ovquery get_by="cve" query="CVE-2018-0229"`

### Release Notes
Updated for Python 2 and 3 compatability. Updated to latest packages of splunklib and openVulnQuery.
