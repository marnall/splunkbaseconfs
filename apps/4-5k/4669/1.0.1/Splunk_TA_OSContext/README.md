# Splunk App for Open Source Context pDNS

## Getting Started
In order to use this app, you will need the following:

* A working installation of Splunk 6.3 or later
* An API key for Open Source Context
	* Available at http://oscontext.com
* An application capable of extracting tar,gzip(tgz) compressed archives

###Installing the App
___
To install the app:

* Extract the contents of Splunk_SA_OSContext.tgz into your $SPLUNK_HOME/etc/apps folder.
* Create a the file ```$SPLUNK_HOME/etc/apps/Splunk_SA_OSContext/local/token.txt``` and enter your API key into this file.
* Restart Splunk ($SPLUNK_HOME/bin/splunk restart)

## Searching
### Basics
___
There are three primary types of searches that can be executed with the app.

* A domain search is used to get the passive dns data associated with any given domain. Search results for the domain myexample.com would return records that contain the hosts and host/subdomains observed with the public suffix of myexample.com. 
* An IP search is used to return all records where the IP address searched is contained in the "value_ip" field. This type of search whould reveal any other domains contained withing the data set that have been seen to resolve to the searched IP address.
* A Network search is similar to the IP search. Using the network search the user can enter a network in CIDR notation (i.e. 192.168.1.1/24) and the search results will contain records in which any IP address in that network appears in the "value_ip" field.

### Limiting Results
___
There are several ways you can limit searches

* Time - You must use the datetime range timepicker in Splunk. The relative values and real-time time panels are currently not functioning in the app as of version 1.0.4
* Number - you can use the "Limit Results" drop down to select the increment of search results to return (10,25,50,100,250,500,1000,Max). The maximum size of results returned but the API at this time is 100,000. The maximum number of returned results is also limited but how many results are in the dataset. If there are only 4 results, only 4 results will be returned in any case where the number of results to return is specified as greater than or equal to 4.
* Record Type - The "Select Record Type" drop down allows the user to specify a specific type of record to be returned in the results set. If no limiting is selected, all resource record types will be returned in the results. If the user specifies a tye of resource record, only results in which the resource record tupe matched the type indicated will be returned.
* Fields - The "Fields" multi-select dropdown allows the user to specify which fields to return with the search results. Currently the user can select one or more of following fields:
	*  Date First Seen - The date the qname was first seen. ("date")
	*  Date Last Seen - The date the qname was last seen. ("last_seen")
	*  Detected Data Value if IP - The detected data value if an IP address. ("value_ip")
	*  Detected Data Value as String - The detected data value as a string. ("value")
	*  Domain Associated with Record - The domain name associated with the record. ("domain")
	*  DNS Query Type - The type of query that was performed when the value was detected. ("qtype")
	*  Type of DNS Record - The type of data value that was detected. ("type")

### Advanced Searching using oscquery custom search command
___
This functionality has been implemented as a custom search command within Splunk named oscquery. This allows for the user to use this command outside of the OSContext App UI. The oscquery command can be used in the SPL toolbar as well as custome lookup scripts. There are 5 arguments that must be supplied to the oscqsuery command.

``` |oscquery search_type search_value number_results record_type fields start_date end_date sort_order```

Table 1 Basic Command Syntax

| search_option  | type  | values  |
|---|---|---|
| search_type  | string  | domain OR ip OR net  |
| search_value  | string  | domainname OR IP OR CIDR  |
| number_results  | int  | any integer >=1 AND <=100000  |
| record_type  | string  | a DNS record type or ANY (ref Table 1.2) |
| fields  | srting  | comma separated list of fields or ALL (ref Table 1.3)  |
| start_date  | int  | Zulu UNIX Epoch of when you want search to start  |
| end_date  | int  | Zulu UNIX Epoch of when you want search to end  |
| sort_order. | string  | Field and order you want to sort upon (ref Table 1.4) |

Table 2 Values for record_type

| DNS Record Type  | record_type value  |
|---|---|
| Any  | ANY  |
| A  | name  |
| AAAA  | aaaa  |
| CNAME  | CNAME  |
| DOMAIN | domain  |
| IP  | ip |
| MX  | mx |
| NS  | ns |
| PTR | ptr |
| SOA_EMAIL | soa_email |
| SOA_SERVER | soa_server|
| TXT | txt |

Table 3 Values for fields

| Field Name  | field value  |
|---|---|
| All Fields | ALL |
| Date First Seen  | date  |
| Date Last Seen  | last_seen  |
| Detected Value if IP  | value_ip  |
| Detected Value as String  | value  |
| Domain Associated with Record  | domain  |
| DNS Query Type | qtype |
| DNS Record Type | type |
| Value of Originating Query | qname |

Table 4 Values for fields

| Field Name  | field value  | Options |
|---|---|---|
| Date First Seen  | date  |  asc OR desc  |
| Date Last Seen  | last_seen  |  asc OR desc  |
| Detected Value if IP  | value_ip  |  asc OR desc  |
| Detected Value as String  | value  |  asc OR desc  |
| Domain Associated with Record  | domain  |  asc OR desc  |
| DNS Query Type | qtype |  asc OR desc  |
| DNS Record Type | type |  asc OR desc  |
| Value of Originating Query | qname |  asc OR desc  |

Examples
___

```| oscquery domain example.com 100 ANY ALL 1420070400 1577836800 "sort:last_seen:desc"```

Would return up to 100 records for example.com with anyrecord type and all fields between the times of 2015-01-01T00:00:00Z and 2020-01-01T00:00:00Z in decending order of when last seen.

```| oscquery ip 173.194.76.27 25 mx ALL 1420070400 1577836800 "sort:last_seen:desc"```

Would return up to 25 MX records where value_ip == 173.194.76.27 and all fields within the record between the times of 2015-01-01T00:00:00Z and 2020-01-01T00:00:00Z in decending order of when last seen.

```|oscquery net 173.194.76.27/24 1000 ANY "value,type,last_seen" 1420070400 1577836800 "sort:value_ip:asc"```

Would return the detected value as string, DNS record type, and date last seen fields of up to 1000 records where value_ip == [173.194.76.0 TO 173.294.76.255] between the times of 2015-01-01T00:00:00Z and 2020-01-01T00:00:00Z sorted by IP in ascending order.

### Caution
___
When trying to return only a specific type of DNS resource record, the values from Table 2 should be used as a guide. You may only specify one value per query. If more than one record type is desired, please use the value of ANY.

When using any value other than ALL from Table 3, the fields should be comma separated without spaces and the whole string encased in quotes i.e. "value,type,date,last_seen"
___
### Advanced Searching using oscsplq custom search command

There is a command included within this app designed to make query from the query line easier and more efficient. The usage for this command is different than that of oscquery, the fields are flag delimited and not in a specific order.

This command take a minimal input of a domain, IP address, or network. You may only use one of these options simultaneously.

Table 5 oscsplq Default Values:

| Field Name  | Default Value  |
|---|---|
| Start Date  | 2010-01-01T00:00:00Z  |
| End Date  | Current Time  |
| Date Range Type  | last_seen  |
| Number of Results  | 100  |
| Sort Order  | last_seen:desc  |
| Fields to Return  | ALL  |
| DNS Record Type | ANY |

Table 6 Search Options for oscsplq:

| Field Name  | Flag  | Example
|---|---|---|
| Domain  | -d  | example.com  |
| IP  | -i  | 192.168.1.1  |
| Network  | -w  | 192.168.1.1/24  |
| Number of Results  | -n  | 500  |
| DNS Record Type  | -t  | mx  |
| Sort Order  | -o  | last_seen:desc  |
| Start Date  | -s  | 2010-01-01T:04:00:00Z |
| End Date  | -e  | 2018-03016T:16:00:00Z  |
| Date Range Type | -r  | date OR last_seen  |

Table 5 describes the default values used if not otherwise specified for oscsplq. These values were used as defaults to aid the user in not having to enter a value for each field.

Table 6 describes the flags that can be used for oscsplq search command. Please note that only one of the -d,-i, or -w flags may be used simultaneously.

Examples
___

```|oscsplq -d example.com```

This search would retuen 100 records wherer the domain field contains example.com, last seen between 2010-01-01T00:00:00Z and the current time when the search was executed. All DNS record types and fields would be returned and sorted in decending order of the last_seen date.

```|oscsplq -d example.com -s 2018-01-01T:04:00:00Z -e 2018-01-01T16:00:00Z -t mx -n 25 -o value_ip:asc -r date```

This search would return 25 MX type records belonging to example.com, first seen between 4AM and 4PM Zulu time on January 1st, 2018, sorted in ascending order of the value_ip field.

The -l Flag
___

There is an ability to issue lucene syntax commands to the API in lieu of the domain, ip, or network. This command is invoked with the -l flag and will not work with the -d, -i, or -w flags. All other flags such as start time, end time, sort order, etc... can still be added to the search and will work to properly filter the results.

```|oscsplq -l "qname.right:net" -s 2018-12-31T:00:00:00Z -e 2018-12-31T01:00:00Z```

This query would return all records where the domain ends in "net" between the hours of midnight and 1AM UTC on December 31st, 2018. This would include att.net , charter.net, and other .net domains, however it would not include sonicnet.com, as the right side of the domain value is not net.

There are a wide range of query commands available via the lucene syntax. Please ask OSC staff for additional documentation for the complete list of lucene searchable fields.

### Workflow Actions ###
___
By default there are workflow actions are enabled. This provides the analyst, when researching events, a quick and convenient way to research an ip or domain properly mapped to the CIM against OSC passive DNS.

For events that contain the fields ```src_ip```, ```dest_ip```, or both, there is an option in the event menu to search OSC passive DNS for the IP.

For events that contain the field ```dest```, there is an option to search OSC passive DNS for the domain contained in dest.

If you would like to disable these workflow actions, please copy the ```$SPLUNK_HOME/etc/apps/Splunk_TA_OSContext/default/workflow_actions.conf``` to your ```$SPLUNK_HOME/etc/apps/Splunk_TA_OSContext/local``` directory and add enabled=0 to the workflow action(s) you wish to disable.

If you would like to modify these workflow actions or create additional workflow actions, please copy the ```$SPLUNK_HOME/etc/apps/Splunk_TA_OSContext/default/workflow_actions.conf``` to your ```$SPLUNK_HOME/etc/apps/Splunk_TA_OSContext/local``` directory and make any modifications necessary for your environment.
