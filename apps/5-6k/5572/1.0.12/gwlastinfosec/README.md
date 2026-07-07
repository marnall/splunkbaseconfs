# Splunk Gatewatcher Lastinfosec Apps

## Overview

The Gatewatcher LastInfoSec App for Splunk (gwlastinfosec) helps you download, parse and use

LastInfoSec Threat intelligence IOC data feed directly from your Splunk searches.

It helps to visualize the downloaded data with the 3 dashboards:

- GW LastInfoSec - IoC Explore: last IoC table with search field (first 50 rows)
- GW LastInfoSec - IoC Analysis: get more detail on the IoC and related
- GW LastInfoSec - IoC Stat: statistics about the downloaded data

The Gatewatcher LastInfoSec App for Splunk (gwlastinfosec) helps you download, parse and use
LastInfoSec Threat intelligence IOC data feed directly from your Splunk searches.
It helps to visualize the downloaded data with the 3 dashboards:

### What do The Gatewatcher LastInfoSec App for Splunk can do

This app is able to connect, download, parse and record the Gatewatcher LastInfoSec Threat Feed in multiple regular splunk kv store lookup, one for each threat type, thus allowing you to enrich your own queries and searches with accurate threat informations. 

Regular download of the Gatewatcher LastInfoSec Threat Feed is scheduled by default to every 20 minutes. You can also trigger manual update. 

The `Gatewatcher LastInfoSec App for Splunk` also comes with 3 dashboards allowing you to navigate / search the Gatewatcher LastInfoSec Threat Feed, and get accurate insights about the Threat feed updates events. 
 
### How does it work ?

The `Gatewatcher LastInfoSec App for Splunk` relies on the `CURL command` apps to download for you in an automatic fashion the Gatewatcher LastInfoSec Threat Feed. 

This App directly run from your search head thru a scheduled search which connects directly to Gatewatcher LastInfoSec API, authenticate with your token, donwload the JSON Threat Feed, parse it, format it and record in an specific multiple kv store lookup named « Filename_lastinfosecioc_kv, Host_lastinfosecioc_kv, URL_lastinfosec_kv, SHA1_lastinfosecioc_kv, SHA256_lastinfosecioc_kv, MD5_lastinfosecioc_kv »

The kv store lookup are regular Splunk kv store lookup, exported to all other apps with read permission to every one, write permission limited to admin. 

### Platform, operating system and hardware requirements:

The `Gatewatcher LastInfoSec App for Splunk` is compatible with recent version of Splunk, starting from Splunk Entreprise 7.1.1 to later version (including 8.2.0, 8.2.1 and 9.0.1). 

Only supported versions of Splunk have been fully tested, older version may work fine.

The `Gatewatcher LastInfoSec App for Splunk` include configuration parameters by size or date ( or both ) permitting to limit the impact on the storage of feeding the kv store. 

## Get started

### System requirements

This topic defines the computing requirements for running the `Gatewatcher LastInfoSec App for Splunk` in the Splunk `Search Head`

- CPU: at least for 4 Core.
- RAM: minimiun of 12GB, recommand 16GB.
- Disk: at least 10GB free of space for the kv store lookup.

### How to install

In 3 easy steps:

- install on your search head the `CURL command` apps -> `curl_command_v1.0.1.spl` package. Set the `Sharing` to `Global` in `http://<your_search_head>:8000/en-US/manager/launcher/apps/local`
- install the `Gatewatcher LastInfoSec App for Splunk` package on your search head 
- configure `Gatewatcher LastInfoSec App for Splunk` with the `api_key` in the `Set up` panel `http://<your_search_head>:8000/en-US/manager/gwlastinfosec/apps/local/gwlastinfosec/setup?action=edit`

### Before you deploy

- Make sure that the `CURL command` apps is installed and exported to "Global" to allow the `Gatewatcher LastInfoSec App for Splunk` to use it. 

To verify that `CURL command` apps is correctly installed and configured, you can try this in the default splunk `search` app

Without proxies

```
| curl url=http://www.google.com output=text
```

With proxies:

```
| curl url=http://www.google.fr proxies="http://proxy.example.com:3128/,http://proxy.example.com:3128/" output=text
```

- obtain thru your Gatewatcher's LastInfoSec Technical or Sales representative an `api_key` token to access Gatewatcher LastInfoSec API


### Recommendation
Once installed, splunk may complains/not working correctly because of limits reached by some commands used in the application.
To avoid any problems, please create a limits.conf file containing the following :

[subsearch]

maxout = 3000000

[searchresults]

maxresultrows = 3000000

[mvexpand]

max_mem_usage_mb = 8000



### Distributed deployment compatibility

The `Gatewatcher LastInfoSec App for Splunk` is run on your search head, so it's fully compatible with distributed deployment.

### User permissions

By default, the Gatewatcher LastInfoSec App for Splunk scheduled search is run as admin, and the kv store lookup are owned by admin, shared and allows anyone to read.

## Release Notes

Version 1.0.0: initial release of The `Gatewatcher LastInfoSec App for Splunk`.
Version 1.0.8: bugfix ssl for splunk < 8
Version 1.0.9: support new fields Vulnerabilities,TargetedOrganizations,TargetedPlatforms,TargetedSectors and update dashboard
Version 1.1.11: now support splunk cloud, by changing setup method from XML to Javascript
## Troubleshooting

The Gatewatcher LastInfoSec App for Splunk includes several debug features, all disabled by default. Please see with a Gatewatcher LastInfoSec Technical representative before activating them. 

## License

See [License](LICENSE) file.

## FAQs

### How do I Install it ?

The `Gatewatcher LastInfoSec App for Splunk` can be deployed as a regular Splunk Entreprise app, from Splunk Web interface or Splunk Cli.

See https://docs.splunk.com/Documentation/Splunk/latest/Admin/Deployappsandadd-ons and choose your version of Splunk Entreprise. 
 

## How do I upgrade from a previous versions ?

The `Gatewatcher LastInfoSec App for Splunk` needs to be upgraded using the regular procedure of Splunk Entreprise, depending on your version, deployment type. 
 
### How do I use it ?

Depending on your threat hunting needs, use the Gatewatcher LastInfoSec `Filename_lastinfosecioc_kv` kv store lookup for example to enhance your own logs, as any regular lookup.

To have a look at the "Filename_lastinfosecioc_kv:

```sh
| inputlookup Filename_lastinfosecioc_kv
```

To have a list of all entries of the "lastinfosecioc" present on your system in a more comprehensive way use

```sh
| `get_ioc` 
```

Note: Be sure to be in the context of the `Gatewatcher LastInfoSec App for Splunk`. 

To search all the kv store lookup in a visual way, use the 2 dashboards present in the `Gatewatcher LastInfoSec App for Splunk` context.

To add the "lastinfosecioc" lookup fields "TLP","Risk","Categories","Tags" to your logs, assuming your logs are in `index=proxy` and you have a field named "url":  `index=proxy | lookup URL_lastinfosecioc_kv Value as url OUTPUT TLP Risk Categories Tags`.
 
Please contact your Gatewatcher LastInfoSec Technical or Sales representative to get more insights on how the `Gatewatcher LastInfoSec App for Splunk` may enhance your security posture. 

### How to use with a proxy

Go on `Configuration` panel and add `proxies` var as follow in `Command` section.

proxies="<http_traffic_proxy>,<https_traffic_proxy>" or if only a https proxy, set proxies=",<https_traffic_proxy>" 

```
curl url=`gwlis_setup_api_url`?api_key=`gwlis_setup_api_token` timeout=`gwlis_setup_api_timeout` proxies="http://proxy.example.com:3128/,http://proxy.example.com:3128/"
```

### If Splunk version inferior to 8.x

As the python SSL store isn't updated anymore due to end of life, the program will not be able to download the LIS Threat Feed

In order to work, you need to have `CURL command` apps >= 1.0.1

Go on `Configuration` panel and add `verifySSL=false` var as follow in `Command` section.

```
curl url=`gwlis_setup_api_url`?api_key=`gwlis_setup_api_token` timeout=`gwlis_setup_api_timeout` verifySSL=false"
```

### What browsers does the The Gatewatcher LastInfoSec App for Splunk ?

The `Gatewatcher LastInfoSec App for Splunk` is using regular Splunk Entreprise Dashboards features (XML). 

Any browser supported by the Splunk Web Framework / XML dashboards is compatible. 
