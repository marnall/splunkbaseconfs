# Overview
Infoblox DDI is a popular DNS, DHCP and IPAM (DDI) system. OOTB there are integrations (via add-ons) with Splunk which provide information about DHCP and DNS services, but there are no IPAM data flows. Luckily, Infoblox (actual product name is NIOS) provides a good REST API that can be used to overcome this gap.

# TA for Infoblox IPAM
This custom technical add-on for Infoblox APIs was built using the Splunk Add-on Builder app (https://splunkbase.splunk.com/app/2962/). The add-on should be installed on your Heavy Forwarders/Indexers and your Search Head instances.

There are three main inputs that can be configured in the TA on your Heavy Forwarder/Indexer:
- /record:host - this lists all host records (from DNS)
- /record:host_ipv4addr - this lists all IPv4 addresses
- /network - this lists all network segments available in IPAM + extended attributes (e.g. location)

REST API URL is usually found at: https://<your_infoblox_instance>:443/wapi/v2.7

For authentication the add-on uses Basic Auth mechanism. Read the API docs here: https://docs.infoblox.com/download/attachments/8945695/Infoblox_RESTful_API_Documentation_2.9.pdf for further details.

# Configuration
## Setup parameters for the TA

|Field|Value|
|--|--|
| Account name | Infoblox |
| Username | <your username> |
| Password | <your password> |
| Log level | WARNING |
| REST API home | https://<your_infoblox_instance>:443/wapi/v2.7 |
| HTTP request timeout | 180 |

## Setup parameters for the inputs
### Hosts
|Field|Value|
|--|--|
|Input name|Hosts|
|Interval|86400|
|Index|<desired index>|
|Requested fields|zone,ipv4addrs,name,view,disable,dns_name,extattrs|
|Item limit|1000|	
|Global account|Infoblox|

### IPv4 addresses
|Field|Value|
|--|--|
|Input name|IPv4|
|Interval|86400|
|Index|<desired index>|
|Requested fields|configure_for_dhcp,host,ipv4addr,mac|
|Item limit|1000|
|Global account|Infoblox|

### Networks
|Field|Value|
|--|--|
|Input name|Networks|
|Interval|86400|
|Index|<desired index>
|Requested fields|dynamic_hosts,comment,disable,network,network_view,extattrs,ipv4addr,netmask,members,static_hosts,total_hosts,unmanaged,utilization|
|Item limit|1000|
|Global account|Infoblox|

# Troubleshooting

The TA logs are sent into the "_internal" index by default. You should perform a search like the following:
`index=_internal source="/opt/splunk/var/log/splunk/ta_infoblox_api*"`

This search will return the contents of the TA logs for the time range you select.

Note that if you see some errors mentioning "next page id" this will be normal, because this means that the input has reached the end of the list of items returned by the API. Anything else deserves to be investigated.
