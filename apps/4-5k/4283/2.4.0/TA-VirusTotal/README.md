
App:                VirusTotal TA  
Current Version:    2.4.0  
Splunk Version:     7.0.x, 7.1.x, 7.2.x, 7.3.x, 8.0.x, 8.1.x, 8.2.x
Author:             Adarma ( tomasz.dziwok@adamra.com )  


# Virus Total TA

This app is used to supplement your data with information from VirusTotal.
The custom command ` | virustotal ` (bundled with this app) uses the `https://www.virustotal.com/vtapi/v2/file/report`
endpoint to communicate with the VirusTotal API.

This TA can be installed on the search head. No additional manual steps are required in distributed environments,
as the app only interacts with search-time functionality ( lookups and scheduled searches ).

## Getting Started

This app requires set-up. App set-up can be accessed from Splunk's "Manage Apps" menu.
The following options should be configured in the set-up menu.

> Note: The setup should be ran by an admin user.

For minimum functionality (ad-hoc searches only), the following should be configured:
 - VirusTotal API Key
 - VirusTotal Max Batch Size

> Note that without configuring these values, neither the custom command nor the scheduled searches will work.

For full functionality (lookup table caching VT data), the following can also be configured:
 - Enable "Cache Auto Update"
 - Configure "Cache Auto Update : Index Filter" : Provide index and/or other filters indicating where events with hashes can found
 - (optional) Review and customise the cron schedule (directing the frequency of when the internal VT cache is to be refreshed)
 - (optional) Review and customise the "Earliest time" for the scheduled search to work with your cron schedule.

For extended cleanup functionality
 - Enable "Cache Auto Clean"
 - (optional) Review and customise the cron schedule for the search and the retention period for the cache
 - It is recommended that the cleanup search run after (not before) the update search.

## Security and Data Exposure

This TA will only ever connect to the VirusTotal REST API endpoint. These connections will only ever be performed over https connections. These connections will only ever be triggered by the explicit invocation of the `| virustotal` command (either by users or by scheduled searches).

This TA will share certain information with the VirusTotal API. This information is strictly limited to:
 - The VirusTotal API key : Required to authenticate against the VirusTotal API
 - The contents of the field specified when running the `| virustotal <hash|url|ip>=FIELD` command. (e.g. hash field, url field, or ip field). Note that care should be taken when using the `url` field. Depending on your data, this field might contain HTTP parameters (e.g. `?very_secret_data=my_secret_password`). This TA **will not** anonymise, remove, nor mutate your data in any way. This could lead to information disclosure. Ensure you understand this risk, or speak to the data owner before using the command. Additionally care should be taken when invoking the VirusTotal command. A careless invocation could result in information disclosure: e.g. `| virustotal hash=very_secret_pii_field` . This invocation would result in the contents of `very_secret_pii_field` being sent across the network to the VirusTotal API.

 No other information will be sent over the network. No other fields from the event will be sent. No file contents or file names will be uploaded for scanning.

## App functionality

### Basic Functionality

The `virustotal` command can be used in SPL. The command accepts two arguments - usage of `hash=<field>` will be described now, and usage of `rescan=<bool>` will be described later in this document.
This argument should be set to the field name of the field that contains hashes in your search.

Example:

```
index=email_attachments attachment_hash=*
| fields attachment_hash, from
| virustotal hash=attachment_hash

```

This will force a real-time query to the VirusTotal API and retrieve the most recent data for each hash.
This use of the app is recommended strictly on an ad-hoc basis, as it can be slow and use many API queries.

 > Should output of the above command not look as expected, check for any warnings/errors in the "Job" dropdown and in the search log. This sometimes happens as a result of data quality issues, VT license issues, and other problems.

Proof of Concept: 

```spl
| makeresults 
| eval eicar="131f95c51cc819465fa1797f6ccacf9d494aaaff46fa3eac73ae63ffbdfd8267"
| virustotal hash=eicar
```

> This PoC is fully self-contained (i.e. does not depend on any external data). 

Similar syntax can be used to query other VirusTotal intelligence endpoints like "url", "domain", and "ip" information.

Example:

```
index=email_attachments source_domain=* target_domain=myorg.com
| fields source_domain, from
| virustotal domain=source_domain

```

Note that the `virustotal` command syntax changed slightly from the first to the second example. It now contains `domain=source_domain`. By using `domain=` instead of `hash=`, we are instructing the command to query VT for different information. One of `url=`, `ip=`, `domain=`, or `hash=` must be used whenever invoking the command. Failure to do this will result in an error. Similarly, if more than one of these options is specified ina  single invocation; this too will result in an error condition.

### Caching Support

This TA also comes bundled with the ability to cache VT data into lookup tables. This function requires configuration in app setup.
Once configured, a set of scheduled searches will periodically update several KVStore collections with VT data.
This lookups will contain historical hashes/urls/ips/domains (up to a configured age), and will also have all the most recent relevant hashes.
This method of correlating VT data is much faster than the ad-hoc method described above.
The following lookups are available, and can be configured for automatic population and updating via App Setup:

 - `virustotal_hash_cache` : This lookup can/should be queried by referencing the `vt_hashes` key. e.g. `| lookup virustotal_hash_cache vt_hashes AS <name_of_your_hash_field>`
 - `virustotal_url_cache` : This lookup can/should be queried by referencing the `vt_urls` key. e.g. `| lookup virustotal_url_cache vt_urls AS <name_of_your_url_field>`
 - `virustotal_ip_cache` : This lookup can/should be queried by referencing the `vt_resource` key. e.g. `| lookup virustotal_ip_cache vt_resource AS <name_of_your_ip_field>`
 - `virustotal_domain_cache` : This lookup can/should be queried by referencing the `vt_domain` key. e.g. `| lookup virustotal_domain_cache vt_resource AS <name_of_your_domain_field>`

Example:

```
index=email_attachments attachment_hash=*
| fields attachment_hash, from
| lookup virustotal_hash_cache vt_hashes AS attachment_hash OUTPUT vt_classification, vt_query_time
```

The drawback of this method is that data within the lookup can potentially be outdated,
as known hashes are only updated at the interval specified in the setup.
Additionally, care should be taken that the scheduled search that populates this lookup is scheduled to run shortly
before any correlations or rules that make use of the lookup. This way, the probability is high that the lookup will have a
chance to pull any required (new) information from VT about previously unseen hashes.

To achieve the best of both approaches, you may use the following SPL snippet:

```spl
index=email_attachments attachment_hash=*
| fields attachment_hash, from
| lookup virustotal_hash_cache vt_hashes AS attachment_hash OUTPUT vt_classification, vt_query_time
| virustotal hash=attachment_hash rescan=false
```

Note the `rescan=false` flag. This instructs the command not to query VT API for hashes which already have metadata attached.
As such, a majority of hashes will retrieved from lookup, and any hashes that weren't found in the lookup will be supplied real-time.

> If the lookup is empty, or some other logical error occurs resulting in failure to supply information from the lookup,
the virustotal command will query VT API for all hashes. This could take a long time and potentially use a very large amount
of API calls. Be sure you understand the risk when using this method.

### Detailed command documentation

The `| virustotal` command supports the following options:

 - `hash=` : specify the name of the field which contains file hashes to be scanned against the VT API
 - `url=` : specify the name of the field which contains URLs to be scanned against the VT API
 - `ip=` : specify the name of the field which contains IP addresses to be scanned against the VT API
 - `domain=` : specify the name of the field which contains domains to be scanned against the VT API

Exactly one of these options must be specified when invoking the command. In addition to these options, there are several flags that can be used to further modify the functionality of command.

 - `mode=` : can be either `json` or `v1` . If mode json is used, the command will return the full json results returned from VT. This can be used to extract any information using spath and work manually with the highest possible level of verbosity. In `v1` mode, the command will return several fields (those deemed to be most valuable but not too verbose by the developers of this TA). `v1` is currently the default mode and the only one that works with caching.
 - `rescan` : can be `true` or `false`. If set to false, any rows that already contain a `vt_resource` field will not be rescanned against the VirusTotal API.

# Advanced functionality

In the 2.0 release of this addon, support was added for an additional output format. By using the `mode=json` option, the command can be used to retrieve and display raw VirusTotal output in json form. This can be used to retrieve additional information, which is not displayed in the command's standard output. By using the `| spath` command, the json format can be extracted and further analysed in Splunk. Note that the TA's out-of-the-box caching support does not use the json output, and still relies on the standard fields typically returned by the command.


## Manually triggering data onboarding

When running the TA for the first time, there is no need to wait for the scheduled search to execute.
After completing App Setup, simply go into the app, click on the reports tab, and click "Open in Search" for the  "VirusTotal Update Hash Lookup" row. (or any of the other "VirusTotal Update * Lookup" searches)
This search will work its way through your events and build a cache ( KVStore-backed lookup ) of all the hashes, ip addresses, urls, or domain names it has seen.

> Depending on the amount of data you have ( in the time-period specified in setup ), and on the VT license/key you are using,
 this could take a significant amount of time to go through all your hashes.


## Lookup: `virustotal_hash_cache`

Fields:
 - `vt_resource` : Synonymous to the _key of the underlying KVStore collection. Usually the hash.
 - `vt_hashes` : A MV list of hashes. At this time, typically, has one of each: md5, sha1, sha256. This field is accelerated. All values in this field are lowercase (to support case-insensitive matching). This is the best field to lookup against (e.g. `| lookup virustotal_hash_cache vt_hashes AS attachment_hash`).
 - `vt_query_time` : Unix timestamp representing the last time the VT API has been queried for information relating to this hash.
 - `vt_classification` : This field is the percentage of AVs that detected a threat. This field is typically synonymous to the following arithmetic expression: `vt_positives/vt_total*100`. Note that this field can also hold a string value of `unknown_hash`. This means that VT has no information about any files with this hash.
 - `vt_scan_date` : This is the datetime that VT reports having last scanned this file on their servers.
 - `vt_permalink` : An HTTPs URL to a human-friendly HTML site about this hash/file. May contain more information about the findings.
 - `vt_positives` : The number of AntiVirus utilities that identified the file with the given hash as a threat.
 - `vt_total` : The number of AntiVirus utilities that were used by VT to scan a file with the given hash.
 - `vt_threat_av` : An MV field of the names of all the AntiVirus utilities that identified the file with this hash as a threat.
 - `vt_threat_id` : An MV field of the classification names assigned to the perceived threat by AntiVirus utilities listed in `vt_threat_av`

## Lookup: `virustotal_url_cache`

 - `vt_query_time` : Unix timestamp representing the last time the VT API has been queried for information relating to this hash.
 - `vt_classification` : This field is the percentage of AVs that detected a threat. This field is typically synonymous to the following arithmetic expression: `vt_positives/vt_total*100`. Note that this field can also hold a string value of `unknown_hash`. This means that VT has no information about any files with this hash.
 - `vt_scan_date` : This is the datetime that VT reports having last scanned this file on their servers.
 - `vt_permalink` : An HTTPs URL to a human-friendly HTML site about this hash/file. May contain more information about the findings.
 - `vt_positives` : The number of AntiVirus utilities that identified the file with the given hash as a threat.
 - `vt_total` : The number of AntiVirus utilities that were used by VT to scan a file with the given hash.
 - `vt_threat_av` : An MV field of the names of all the AntiVirus utilities that identified the file with this url as a threat.
 - `vt_threat_id` : An MV field of the classification names assigned to the perceived threat by AntiVirus utilities listed in `vt_threat_av`

## Lookup: `virustotal_ip_cache`

 - `vt_resource` : The IP address that this entry pertains to
 - `vt_classification` : This does not yield useful threat information like hash/url. Basically can be "known" or "unknown"; referring to whether this was found in VT database or not; but not indicating whether this is a threat.
 - `vt_query_time` : the time when this Ip was last checked against VT.
 - `vt_whois` : whois information associated with this IP.
 - `vt_asn` : Autonomous System Number that owns this IP or its range.
 - `vt_network` : The CIDR range that this IP belongs to in IANA records.
 - `vt_country` : The country that this IP is registered to.
 - `vt_as_owner` : The name of the Autonomous System that owns this IP or IP range
 - `vt_scan_date` : The date that VirusTotal last updated this record.

## Lookup: `virustotal_domain_cache`

 - `vt_resource` : The domain name that this record refers to. (lower case / case insensitive)
 - `vt_classification` : This does not yield useful threat information like hash/url. Basically can be "known" or "unknown"; referring to whether this was found in VT database or not; but not indicating whether this is a threat.
 - `vt_categories` : The categories that this site has been identified as containing. e.g. 'search engine', 'adult content', 'gambling', etc.
 - `vt_query_time` : the time when this domain was last checked against VT.
 - `vt_detected_communicating_samples` : number of samples (executables) that were observed communicating with this domain. (capped at 100)
 - `vt_detected_downloaded_samples` : number of samples (executables) that were observed to be downloadable from this domain
 - `vt_detected_referrer_samples` : ???
 - `vt_detected_urls` : number of URLs under this domain that were reported as malicious by at least one VT engine.

## Saved Searches

The description of each scheduled search can be found in the app setup. Please ensure you read and understand it before
enabling the saved search

## Support

Support will be provided by the developers (ADARMA) on a best-effort basis. The developers make no commitment to continued development. The software is provided as is, and the developer accepts no responsibility for any issues with the software, or which may result as a consequence of using the software.

## Known Issues

 - 1 : While running the search, multiple errors occur, each from a different indexer, claiming that "Application does not exist: TA-VirusTotal"
   - This issue can happen on several older versions of Splunk. It means that, despite the TA's objections, the command is being run in streaming mode across all indexers. The quick-fix is to use a non-streaming command (e.g `| table *`) right before the `| virustotal` command. This will force the remainder of the search to happen on the search head; fixing the issue.

## Changelog

### 2.4.0

 - Role changes for Splunk Cloud compatibility
 - Fixing errors in Splunk AppInspect
 
### 2.2.0

> thanks to: @edro15 

 - removed setup.xml & fixed compatibility with Spunk Cloud

### 2.1.0

 - Added support for python 3.x
   - Updated splunklib to latest version
   - Moved splunklib out of "bin" and into "lib" as per best-practice

### 2.0.0

Added support for URL, domain, and IP intelligence (with full support for caching working almost identically to how hash caches have worked since the beginning)  
Added support for using a proxy to connect to VirusTotal  
Made the `| virustotal` command available in other apps. (permissions are still restricted to admin users; see metadata/default.meta for more info)  

### 1.2.3

Added a data-quality warning to warn users that data in their hash field may have issues.  

### 1.2.0

Added cmd_timeout option to virustotal.conf and the app setup page. This option allows the user to provide a timeout  
value. This is a patch intended to provide support for Splunk versions lower than 7.1.0. On those versions,  
the search job lifecycle reaches the "Finalising" state prematurely, causing the command to terminate before it is  
done processing all events. The consequence of correcting for this behaviour, is that the user is unable to manually  
"Stop" the job. The timeout was added to provide the user with the means to specify the maximum running time for the command,  
intended to be especially useful in environments where manual stopping is impossible.  
