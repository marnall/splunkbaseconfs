Need support? splunkcompek.net

## Splunk App for McAfee/SkyHigh Web Gateway

Version: 6.0.0

Date: 27 Mar 2026

  * About
  * Where to install this App
  * Quick Start / Get Data In
  * Overview of Sourcetypes and Log Formats
  * Configure a custom log format (mcafee:webgateway:custom) on MWG
  * **Upgrade from 5.x to 6.x**
  * Upgrade from 4.x to 5.x
  * **Interactive Deployment Wizard**
  * Security considerations
  * Onboarding checklist
  * Detailed description of the mcafee:webgateway:custom Log Format
  * Other logs
    * Audit log
    * /var/log/messages
    * /var/log/secure
    * /opt/mwg/log/mwg-errors
  * Self-Monitoring
  * Next Steps / Action Plan
  * FAQ
  * Dashboard Customization
  * Troubleshooting
  * Summary of changes
  * Contributors, Attributions
  * Copyright
  * Disclaimer
  * Contact, Support and Feedback
  * Additional information
    * mwg_xml2txt script
    * dump_logging_fields
    * List of Counters

About

This Splunk App for McAfee Web Gateway allows rapid insights and operational visibility into McAfee Web Gateway (MWG)
and McAfee Web Gateway Cloud Service (WGCS) deployments. It provides field extraction and CIM field mapping using all
available types of access logs (default and custom McAfee Web Gateway log, McAfee Web Gateway Cloud Service), and
facilitates fast incident response and troubleshooting. This app is designed for security administrators, CISOs, and
security personnel responsible for web security operations.

In 2022, McAfee Web Gateway (MWG) rebranded as SkyHigh Secure Web Gateway (SWG). The App and sourcetype will maintain
the McAfee name for some time to preserve the old App ID.

List of abbreviations used in this document:  Abbreviation| Meaning  
---|---  
MWG| McAfee Web Gateway  
SWG| SkyHigh/Secure Web Gateway  
WGCS| McAfee/SkyHigh Web Gateway Cloud Service  
UF| Splunk Universal Forwarder  
  
Product Compatibility:  Product| Version(s)  
---|---  
Splunk Enterprise| 8.x, 9.x, 10.x  
Splunk Cloud| all versions, both Classic and Victoria  
Splunk CIM| 4.x, 5.x, 6.x  
MWG/SWG| 7.6+, 8.x, 9.x, 10.x, 11.x, 12.x  
WGCS| API version 5-12  
  
Currently there are 186 different charts, tables and panels grouped into 41 views:

  * **Summary** (default) — Requests / Block Ratio, Traffic Overview

  * **Search**
    * Easy Search — Status Code Overview, Web Usage by URL Category, Top User-Agents, Users + IPs, Top Hosts, Top Blocked Domains, Top Rules, Events
    * Fast Search
    * Raw Search (link)

  * **Traffic & Content**
    * Traffic — Top Inbound/Outbound Traffic by Source/Destination
    * URL Filter — URL Categories, Blocked by URL Filter or Web Reputation, Top Categories by Volume/Hits, Geolocation, High Risk Destinations, Not categorized Domains
    * Media Types — Top Media Types by Volume/Hits, EXE/Macro Uploads/Downloads, Magic Bytes Mismatch, Encrypted Files
    * Applications — Applications by Hits/Volume, Top Applications
    * Uploads
    * User-Agents — User-Agent Statistics

  * **Network & Protocol**
    * Protocols — by Hits, by Volume (absolute and percent)
    * Connections — Long running transactions
    * Network — Top unreachable Servers
    * HTTP — HTTP Method Timechart/Statistics, Request/Response Headers Statistics
    * Headers — Request Headers Statistics/Avg Length/Variations, Mismatched dest and Host Header
    * DNS — DNS resolution time distributions
    * DoH — DNS-over-HTTPS Statistics by Destinations/Client
    * SSL — SSL Versions/Ciphers/KeyExchangeBits by Hits (Server/Client)
    * Certificates — Certificate blocks, Expired Certs, Issuers, Client Certificate Requested
    * Authentication — Failed Auth by SRC IP/User-Agent/Destination, Multiple Logins, Auth Method Statistics

  * **Security & Threats**
    * Malware — Malware, Top Users by blocked Malware
    * Potential Risks — High Risk Requests, Unusual Ports, Requests to IPs, Very long URLs, Large Headers, DGA, Content-Disposition
    * Security Posture — HTTPS Scanner / Media Type Filter / Opener enabled?
    * Unfiltered Threats
    * Rules — Top Rules, Block Rules, Rule Complexity/Performance, Time in Rule Engine

  * **System & Infrastructure**
    * Performance — Connect to Server / Total Transaction / Client-Side / DNS / Externals Latency
    * Errors — Error Analysis
    * MWG-Errors — Errors by Host, MWG Core/Coordinator, Events with KBxxxxx
    * Monitoring — CPULoad, HTTP/HTTPS/HTTP2 Requests, Memory, Filesystem, Swap
    * Audit — Failed Logins, Activity by Action/Source_Type/User/Appliance
    * Audit - Timeline (requires Splunk 9.1+ with Dashboard Studio)
    * Linux Syslog — Event Timeline, Events by Host, Category Breakdown, Top Repeated Messages
    * Linux Secure — Authentication Events, Failed Logins, Successful Logins, Sudo Commands
    * Troubleshooting & Log Analyzer — Sourcetype Detection, Field Extraction Health, Timestamp Validation, Syslog Prefix Issues
    * Troubleshooting (legacy)

  * **Accelerated (+)** — Summary+, Search+, Traffic+, URL Filter+, Protocols+, User-Agents+

  * Help/Contact

Where to install this App Instance| [App for McAfee Web Gateway](<https://splunkbase.splunk.com/app/1654/>)| [Add-on for McAfee Web Gateway](<https://splunkbase.splunk.com/app/5452/>)  
---|---|---  
Standalone (all-in-one) Splunk| +| -  
Splunk Cloud| +| -  
On-prem Search Head| +| -  
On-prem Indexer| -| +  
Syslog/Log Server with Universal Forwarder| -| +  
SkyHigh Logging Client| -| +  
Quick Start / Get Data In

Upgrading from an older version? Read **Upgrade from 5.x to 6.x** or Upgrade from 4.x to 5.x.

  1. Configure a custom log format (mcafee:webgateway:custom) on SWG
  2. Choose your deployment method and configure using the wizard below
  3. Install the Splunk App for McAfee Web Gateway on the Search Head
  4. Configure the index_and_sourcetype macro (Settings > Advanced search > Search macros)

#### Interactive Deployment Wizard

#### Step 1: Deployment Mode

| Mode| Description  
---|---|---  
Select| **Universal Forwarder on SWG**|  Install UF directly on SWG, monitor log folder, forward to Splunk indexer.
**Recommended.**  
Select| **Splunk Enterprise on SWG**|  Install Splunk Enterprise directly on SWG, monitor local log folder. For testing
or small environments.  
Select| **SWG → Syslog → UF**| SWG sends syslog to a log server where UF forwards to Splunk. Not recommended.  
Select| **Syslog directly to Splunk**|  SWG sends syslog directly to Splunk indexer. Not recommended.  
  
#### Step 2: Parameters

Parameter| Value| Comment  
---|---|---  
Index name| | Splunk index for SWG logs  
Sourcetype| mcafee:webgateway:custom (recommended)mcafee:webgateway:defaultmcafee:webgateway:minimal|  
Additional log sources|  Audit log  
/var/log/messages  
/var/log/secure  
mwg-errors | Additional inputs for the same index  
Splunk indexer (host:port)| | For UF outputs.conf  
Syslog destination (hostname/IP)| | Where SWG sends syslog  
Syslog port| |   
Syslog transport|  UDP TCP (selected: tcp) |   
Strip syslog header|  Yes (recommended) No (selected: yes) | Strip syslog header to send message only.  
File permissions method|  UF 9.x+ with CAP_DAC_READ_SEARCH (default) UF without CAP_DAC_READ_SEARCH (setfacl for splunkfwd) Splunk Enterprise (setfacl for splunk) |   
  
#### Step 3: Generated Configuration

#### inputs.conf

#### outputs.conf

#### Permissions

#### rsyslog.conf (on SWG)

#### rsyslog input configuration (on syslog server)

#### syslog-ng input configuration (on syslog server)

#### Syslog considerations

  * Syslog UDP is typically not recommended because of the potential packet loss.
  * Install the syslog collector on the same VLAN/network as SWG. Avoid unreliable links (WiFi/WAN), firewalls with DPI/IDS.
  * For large environments, use an intermediate syslog server rather than sending directly to Splunk.

References: [Splunk validated architectures](<https://www.splunk.com/pdfs/technical-briefs/splunk-validated-architectures.pdf>) | Video walkthroughs: [Local file monitor](<https://youtu.be/96oRco3MTu0>) | [Syslog to Splunk](<https://youtu.be/vYy6ddpGkNw>) | [Syslog TLS](<https://youtu.be/-nSkYdDQA00>)

Overview of Sourcetypes and Log Formats There are several possible log formats that can be used. Compare your logs with
the examples below to identify your current format.  

#### On-premise Web Gateway

Log Format| Sourcetype| # of MWG fields| # of CIM fields| Average log line length (HTTPS Scanner enabled)|
Comment/Example  
---|---|---|---|---|---  
**Custom Log (recommended)**|  mcafee:webgateway:custom| 50-100| 50-100| ~600-1800 Bytes| This custom modular log format
allows for flexible addition or removal of logging fields as needed. It provides comprehensive Common Information Model
(CIM) coverage and deep insights for analytics and rapid troubleshooting. Despite providing significantly more
information, the log size remains largely unchanged. In fact, this new format achieves up to 3 times higher information
density compared to the default log format.  
  
Starting from version 5.0.0 of the app, an updated log format was introduced that provides significantly improved search
(**up to 30 times**) and reporting (**up to 100 times**) performance by leveraging TERM and PREFIX directives:  
  
2021-02-26 14:36:46 -0600 s=200 ac=allowed src=192.168.2.1 p=https m=GET d=safebrowsing.googleapis.com dp=443 bi=563
bo=4156 dur=38 rt=17 up="/v4/threatListUpdates" ua="FF86-10.0" c=it dip=142.250.185.n ckex=112 skex=112 cntx scc=1302
ssc=1302 sslcp=1.3 sslsp=1.3 sslicn="GTS CA 1O1,GlobalSign" sslcn="upload.video.google.com" crtdays=-52 mbmismatch ctmt0
rul="L" rnf=41 rne=104 srcp=62407 conrt=0 bfc=524 btc=4418 tunnel psrcip=192.168.2.1n psrcp=42550 rqv=2.0 rsv=2.0 r=0
tdns=0 tcon=0 tre=34 text=34 t=18.18.22.11.15  
  
Old versions of the app (3.x and 4.x) provided a slightly different format, that doesn't allow TERM/PREFIX benefits:  
_2021-02-26 14:40:23 +0100 204 allowed 192.168.2.1 https GET example.com 443 775/58 88/1 up="/test" ua="FF86-10.0"
a="Google" c="wa" dip=142.250.185.nn kex=112/112 cntx sccc=1302/1302 sslp=1.3/1.3 sslicn="GTS CA 1O1,GlobalSign"
sslcn="example.com" crtdays=-66 ctmt0 rul="L" rn=13/44 srcp=63298 conrt=0 b=744/239 psrcip=192.168.2.1 psrcp=20010
piv=2.0/2.0 r=0 t=0/0/86/87/56/56/3/4/28_  
Minimal Log| mcafee:webgateway:minimal| 6| 8| ~45-55 Bytes| Minimal log format, contains only 6 most important fields:
status, src, dest, bytes_in, category, reputation. There is no timestamp, DATETIME_CONFIG = CURRENT is used instead.
This format allows you to get the most important statistics using the shortest possible event length and is intended for
use with the Splunk Free license (500 MB/day, ~10.000.000 events/day).  
  
302 192.168.1.10 maps.google.com 667 cm -38  
Default Access Log| mcafee:webgateway:default| 14| 17| ~700 Bytes| The default log format, which has a fixed structure,
provides only a minimal subset of fields. Use it only if no MWG modification is possible.  
  
[26/Feb/2021:14:40:23 +0100] "" 192.168.2.1 200 "GET https://example.com/test&adk;=1473563476 HTTP/2.0" "Web Ads"
"Minimal Risk" "image/gif" 286 538 "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0" ""
"0" "Google"  
Legacy log format for the Splunk App v.3.0.7| MWGaccess3| 26| 27| ~650 Bytes| **DEPRECATED** — No longer supported for
new deployments. Existing users should migrate to mcafee:webgateway:custom. Customized log format with a fixed
structure, provides more fields than the default log, including some timings and transferred bytes. Verbose fields like
the User-Agent string are shortened.  
  
[26/Feb/2021:14:40:23 +0100] status="200/0" srcip="192.168.2.1" user="" profile="-" dstip="-" dhost="example.com"
urlp="443" proto="HTTPS/https" mtd="GET" urlc="Web Ads" rep="0" mt="image/gif" mlwr="-" app="Google"
bytes="538/539/289/286" ua="FF86.0-10.0" lat="0/0/59/434" rule="Last Rule"
url="https://example.com/test&adk;=1473563476"  
Modified legacy log derived from MWGaccess3| mcafee:wg:kv| 26| 27| 650-850 Bytes| **Not supported by this app.** This sourcetype belongs to the [Splunk Add-on for McAfee Web Gateway](<https://classic.splunkbase.splunk.com/app/3009/>) and is listed here for reference only. Modified MWGaccess3 log format with a fixed structure, provides more fields than the default log, including some timings and transferred bytes. Verbose fields like the User-Agent string are shortened. Added sha2 hash and a CN name of the SSL certificate, a Cache-Control header, file name, a reputation level.  
  
[10/Mar/2024:15:16:52 +0100] status="200/0" srcip="192.168.2.1" dhost="web.de" destip="82.165.229.83" urlp="443"
proto="HTTPS/https" mtd="GET" urlc="Portal Sites" rep="0" mt="text/html" bytes="69/189/345936/345564" ua="curl/8.4.0"
lat="0/0/397/397" rule="Last Rule" url="https://web.de/" rep_level="Minimal Risk" cache_control="no-cache, no-store,
must-revalidate" ssl_cert_sha2="12695b9b9d0c190b01674492fcf898f91ba85d996dbafe8651e1ac41482f5907"
ssl_cert_name="*.web.de"  
  
#### SSE / Web Gateway Cloud Service (WGCS)

WGCS log format provides a [subset of required fields](<https://success.myshn.net/Skyhigh_Secure_Web_Gateway_\(Cloud\)/Reporting/Using_a_REST_API_for_Reporting/Reporting_Fields>), there are several API versions:  
  
Log Format| Sourcetype| # of MWG fields| # of CIM fields| Average log line length (HTTPS Scanner enabled)|
Comment/Example  
---|---|---|---|---|---  
WGCS API version 5| skyhigh:webgateway:csv  
or  
mcafee:webgateway:wgcs_v5| 28| 28| ~300-400 Bytes|
"user_id","username","source_ip","http_action","server_to_client_bytes","client_to_server_bytes","requested_host","requested_path","result","virus","request_timestamp_epoch","request_timestamp","uri_scheme","category","media_type","application_type","reputation","last_rule","http_status_code","client_ip","location","block_reason","user_agent_product","user_agent_version","user_agent_comment","process_name","destination_ip","destination_port"
"-1","142.250.185.nn","142.250.185.nn","GET","206","1040","example.com","/test","OBSERVED","","1626329868","2021-07-15
06:17:48","https","Business, Software/Hardware","application/x-empty","","Minimal Risk","Internal Request
handled","200","8.65.16.n","","","Other","","","","78.47.250.n","443"  
WGCS API version 6| skyhigh:webgateway:csv| 28| 28| ~300-400 Bytes| No new fields are introduced. All fields from
versions 1 – 5 are downloaded. Starting with API version 6, an error message is sent with the response to a download
request that has timed out.  
WGCS API version 7| skyhigh:webgateway:csv| 34| 28| ~400-450 Bytes| All fields from versions 1 – 6 are downloaded, plus
these fields:

    
    
    pop_country_code
    referer
    ssl_scanned
    av_scanned_up
    av_scanned_down
    rbi
      
  
WGCS API version 8| skyhigh:webgateway:csv| 40| 30| ~400-500 Bytes|  All fields from versions 1 – 7 are downloaded, plus
these fields:

    
    
    dlp
    client_system_name
    filename
    pop_egress_ip
    pop_ingress_ip 
    proxy_port
      
  
WGCS API version 9| skyhigh:webgateway:csv| 40| 30| ~450-600 Bytes|  With this header, no new fields are added. All
fields from versions 1 – 8 are downloaded.  
WGCS API version 10| skyhigh:webgateway:csv| 40| 30| ~450-600 Bytes|  With this header, all fields from versions 1 – 9
are downloaded, plus these fields:

    
    
    mw_probability
    discarded_host
    ssl_client_prot
    ssl_server_prot
      
  
WGCS API version 11| skyhigh:webgateway:csv| 41| 30| ~450-600 Bytes|  With this header, fields from versions 1 – 10 are
downloaded, plus this field:

    
    
    domain_fronting_url
      
  
WGCS API version 12| skyhigh:webgateway:csv| 41| 30| ~450-600 Bytes|  With this header, fields from versions 1 – 11 are
downloaded, plus these fields:  
Downloaded for firewall traffic:

    
    
    domain_name
    client_host_name
    host_os_name
    scp_policy_name
    process_exe_path
    

Downloaded for Private Access traffic:

    
    
    virus
      
  
Configure a custom log format (mcafee:webgateway:custom) on MWG

  1. Extract the file Splunk_Log_XXXXXX.xml (where XXXXXX is the version) from the MWG folder of the application package.

  2. Import Splunk_Log_XXXXXX.xml file in MWG into the Default Log Handler: Policies > Rule Sets > Log Handler, right click on "Default" and select Add > Rule Set from Library

  

  3. In the new window that appears, click on the "Import from file" button, then choose the xml file and click OK.

  

  4. click "Auto-Solve Conflicts..." > select "Solve by referring to existing objects" and click OK to import the RuleSet.

  

  5. If MWG cannot resolve external hostnames then disable DNS RuleSet.
  6. If MWG cannot query Online URL Database then disable URL Categorization and Geolocation Rules.
  7. If any of the imported RuleSets/Rules are marked red - this indicates that some properties like Header.Request.GetAll (available on MWG 10.x+) are not available in the current MWG version. Just delete these rules or upgrade MWG to the latest 10.x+ version. If a TLS RuleSet is shown in red, it needs to be modified as described below in the Troubleshooting section.  
  

  8. The Log configuration has a modular structure, you can choose to send just a preconfigured minimal set of fields or select any subset from available fields. The log ruleset contains several parts (see numbering on the next screenshot): 

     1. Required rulesets for [CIM-conforming logging](<https://docs.splunk.com/Documentation/CIM/latest/User/Web>).
     2. Web Data Model ruleset where a log line from the previously prepared fields is built.
     3. Additional rulesets where other fields are added as needed.
     4. The DEBUG ruleset that helps to verify that the log lines are built correctly.
     5. Write Splunk.log - final log line modifications, performance monitoring of the Splunk ruleset itself and writing the Splunk log to the hard disk.
     6. Send via Syslog.
     7. RuleSet Library - optional templates that can be copied into appropriate Policy Rule Sets (Opener, Media Type Filter etc.) to obtain information that is usually not available in the logging cycle.
  

Here are the most important modifications that you can do in additional Rulesets (block of RuleSets #3 on the previous
screenshot).

Ruleset| Possible modifications  
---|---  
Splunk| Domains not to log - some domains can be excluded from logging completely.  
Set Timestamp| choose the right timestamp. The ISO format with a time zone is selected by default. Other options are
ToGMT, ISO8601, unix epoch and ToWebReporter formats. If you change the timestamp format on MWG then you have to adjust
the TIME_FORMAT setting in local/props.conf on Splunk Indexer.  
Client IP| Connection.IP property is used by default. Deselect it and select Client.IP if you have downstream proxies or
loadbalancer between the client and MWG.  
URL Categories| add internal domains to "internal Domains" list to avoid them being shown as "uncategorized"  
Headers| on MWG older than version 10.x some rules will be marked in red if they are not compatible - delete them or
upgrade MWG to the newest 10.x version or later.  
TLS| disable this ruleset if HTTPS Scanner is not enabled  
-| To get the correct Rule statistics you must create one last ruleset with a rule named "Last Rule" which is applied to all cycles (Request, Response, Embedded).  
RuleSet Library| Opener, Hashes/Body, Malware, Media Type, Uploads - to get some of the required information, additional
rules need to be placed in the corresponding Policy Rule Sets. If you skip this step, some tables and graphs will be
empty.  
  
  
Create a "Last Rule Set" with an empty "Last Rule" as a most bottom rule in the Rule Sets Tree:  
  
Copy Rules to Certification Verification Rule Set to be able to log information about certification parameters:  
  

Upgrade from 5.x to 6.x

  * Version 6.x is fully compatible with 5.x log formats. No changes to your SWG log configuration are required.
  * Just upgrade the app on the Search Head and the Add-on on indexers/forwarders.
  * If you are currently using syslog, consider migrating to Universal Forwarder for improved reliability.
  * See Summary of changes for the full list of changes in 6.0.0.

Upgrade from 4.x to 5.x

  * Version 5.x supports all previous log formats and introduces a new format for faster searches (speedup up to 30 times) and faster reports (speedup up to 100 times).
  * If you choose to keep the old log format on SWG and don't benefit from the speedup, just upgrade the app, no additional steps required.
  * To take advantage of the speedup introduced by the new log format, follow these steps to upgrade the log handler on SWG and the Splunk app: 
    * Review SPL searches in Splunk that use raw extractions and modify them for the new log format.
    * If there are custom parsing and extractions on intermediate heavy forwarders or Cribl, check and modify them as necessary.
    * Upgrade the app on the search head(s)
    * Next, upgrade the log configuration on SWG: 
      * Import the provided log format configuration (e.g., a file named "2023-10-26_13-10_Splunk_new_format.xml") from the app package in the MWG folder.
      * Optional, for highly modified rulesets: use provided scripts mwg_xml2txt script and dump_logging_fields to find differences between old and new versions of logging rulesets.
      * To view all available fields use `index_and_sourcetype`| fieldsummary | fields field count | sort field
      * Modify the new log format configuration as needed, all fields that were used before should be also enabled in the new ruleset.
      * Double check the timestamp in the old and new log configuration.
      * Disable the old log format ruleset, enable the new log ruleset, save changes.
      * Check all your searches, dashboards and reports using a time range with a new log format (e.g. "last 15 minutes") and make sure they work as expected. If not, find which fields are missing and enable them in the log configuration ruleset.
  * Finally, test everything in a test or staging environment. If you need support, send an email to splunkcompek.net

* Security considerations
Least privileges Starting from UF version 9.x a splunk forwarder runs with **AmbientCapabilities=CAP_DAC_READ_SEARCH**
that allows the **service** to read any file on the system (incl. /etc/shadow etc.).
<https://docs.splunk.com/Documentation/Forwarder/latest/Forwarder/Installleastprivileged>.  
  
**Important** : The Linux ACLs are still being applied. However, when running commands directly as the "splunkfwd" user
(outside the service), standard Linux permission checks still apply. The Splunk forwarder service, which runs as
"splunkfwd" but with the "CAP_DAC_READ_SEARCH" capability, can read any file on the system.  
  
If this capability is too permissive, you can disable it in /etc/systemd/system/SplunkForwarder.service and configure UF
read-only permissions using classic linux permissions:  Command| Comment  
---|---  
setfacl -m u:splunkfwd:rx /opt/mwg/log/user-defined-logs| Allow the user splunkfwd to read user-defined logs | usermod -aG adm splunkfwd| Add the user splunkfwd to the adm group to allow reading /var/log/messages and /var/log/secure  
usermod -aG mwg splunkfwd| Add the user splunkfwd to the mwg group to allow reading various proxy logs; this provides
more permissions than the setfacl method.  
Deployment Server In a high-security environment, you can consider avoiding direct connections between the UF and the
deployment server. Instead, opt to push all configurations using alternative methods.

* Onboarding checklist
Check| Expected Result| Conditions/Causes| Comment  
---|---|---|---  
Timestamp and Timezone| Timestamp and timezone are correct, there are no "future" events| |  | eval diff=_indextime - _time   
Index| Index is correct| | Use a separate index for proxy events  
Sourcetype| sourcetype is correct| |   
Host extraction| Host extraction is correct| Syslog| Don't rely on rDNS, it decreases performance and can fail. Hosts
server1, SERVER1, server1.example.com, 10.20.30.nn can be the same host, but are different hosts from Splunk's point of
view.  
Integrity| All events reach Splunk, no events are lost| Syslog, high log rate| useACK, rsyslog: disk queue  
Truncation| Long log lines aren't truncated| rsyslog: MaxMessageSize, syslog-ng: log_msg_size, syslog via UDP, Splunk: TRUNCATE| [test-link](<https://proxy-test.com/_000000010_000000020_000000030_000000040_000000050_000000060_000000070_000000080_000000090_000000100_000000110_000000120_000000130_000000140_000000150_000000160_000000170_000000180_000000190_000000200_000000210_000000220_000000230_000000240_000000250_000000260_000000270_000000280_000000290_000000300_000000310_000000320_000000330_000000340_000000350_000000360_000000370_000000380_000000390_000000400_000000410_000000420_000000430_000000440_000000450_000000460_000000470_000000480_000000490_000000500_000000510_000000520_000000530_000000540_000000550_000000560_000000570_000000580_000000590_000000600_000000610_000000620_000000630_000000640_000000650_000000660_000000670_000000680_000000690_000000700_000000710_000000720_000000730_000000740_000000750_000000760_000000770_000000780_000000790_000000800_000000810_000000820_000000830_000000840_000000850_000000860_000000870_000000880_000000890_000000900_000000910_000000920_000000930_000000940_000000950_000000960_000000970_000000980_000000990_000001000_000001010_000001020_000001030_000001040_000001050_000001060_000001070_000001080_000001090_000001100_000001110_000001120_000001130_000001140_000001150_000001160_000001170_000001180_000001190_000001200_000001210_000001220_000001230_000001240_000001250_000001260_000001270_000001280_000001290_000001300_000001310_000001320_000001330_000001340_000001350_000001360_000001370_000001380_000001390_000001400_000001410_000001420_000001430_000001440_000001450_000001460_000001470_000001480_000001490_000001500_000001510_000001520_000001530_000001540_000001550_000001560_000001570_000001580_000001590_000001600_000001610_000001620_000001630_000001640_000001650_000001660_000001670_000001680_000001690_000001700_000001710_000001720_000001730_000001740_000001750_000001760_000001770_000001780_000001790_000001800_000001810_000001820_000001830_000001840_000001850_000001860_000001870_000001880_000001890_000001900_000001910_000001920_000001930_000001940_000001950_000001960_000001970_000001980_000001990_000002000_000002010_000002020_000002030_000002040_000002050_000002060_000002070_000002080_000002090_000002100_000002110_000002120_000002130_000002140_000002150_000002160_000002170_000002180_000002190_000002200_000002210_000002220_000002230_000002240_000002250_000002260_000002270_000002280_000002290_000002300_000002310_000002320_000002330_000002340_000002350_000002360_000002370_000002380_000002390_000002400_000002410_000002420_000002430_000002440_000002450_000002460_000002470_000002480_000002490_000002500_000002510_000002520_000002530_000002540_000002550_000002560_000002570_000002580_000002590_000002600_000002610_000002620_000002630_000002640_000002650_000002660_000002670_000002680_000002690_000002700_000002710_000002720_000002730_000002740_000002750_000002760_000002770_000002780_000002790_000002800_000002810_000002820_000002830_000002840_000002850_000002860_000002870_000002880_000002890_000002900_000002910_000002920_000002930_000002940_000002950_000002960_000002970_000002980_000002990_000003000_000003010_000003020_000003030_000003040_000003050_000003060_000003070_000003080_000003090_000003100_000003110_000003120_000003130_000003140_000003150_000003160_000003170_000003180_000003190_000003200_000003210_000003220_000003230_000003240_000003250_000003260_000003270_000003280_000003290_000003300_000003310_000003320_000003330_000003340_000003350_000003360_000003370_000003380_000003390_000003400_000003410_000003420_000003430_000003440_000003450_000003460_000003470_000003480_000003490_000003500_000003510_000003520_000003530_000003540_000003550_000003560_000003570_000003580_000003590_000003600_000003610_000003620_000003630_000003640_000003650_000003660_000003670_000003680_000003690_000003700_000003710_000003720_000003730_000003740_000003750_000003760_000003770_000003780_000003790_000003800_000003810_000003820_000003830_000003840_000003850_000003860_000003870_000003880_000003890_000003900_000003910_000003920_000003930_000003940_000003950_000003960_000003970_000003980_000003990_000004000_000004010_000004020_000004030_000004040_000004050_000004060_000004070_000004080_000004090_000004100_000004110_000004120_000004130_000004140_000004150_000004160_000004170_000004180_000004190_000004200_000004210_000004220_000004230_000004240_000004250_000004260_000004270_000004280_000004290_000004300_000004310_000004320_000004330_000004340_000004350_000004360_000004370_000004380_000004390_000004400_000004410_000004420_000004430_000004440_000004450_000004460_000004470_000004480_000004490_000004500_000004510_000004520_000004530_000004540_000004550_000004560_000004570_000004580_000004590_000004600_000004610_000004620_000004630_000004640_000004650_000004660_000004670_000004680_000004690_000004700_000004710_000004720_000004730_000004740_000004750_000004760_000004770_000004780_000004790_000004800_000004810_000004820_000004830_000004840_000004850_000004860_000004870_000004880_000004890_000004900_000004910_000004920_000004930_000004940_000004950_000004960_000004970_000004980_000004990_000005000_000005010_000005020_000005030_000005040_000005050_000005060_000005070_000005080_000005090_000005100_000005110_000005120_000005130_000005140_000005150_000005160_000005170_000005180_000005190_000005200_000005210_000005220_000005230_000005240_000005250_000005260_000005270_000005280_000005290_000005300_000005310_000005320_000005330_000005340_000005350_000005360_000005370_000005380_000005390_000005400_000005410_000005420_000005430_000005440_000005450_000005460_000005470_000005480_000005490_000005500_000005510_000005520_000005530_000005540_000005550_000005560_000005570_000005580_000005590_000005600_000005610_000005620_000005630_000005640_000005650_000005660_000005670_000005680_000005690_000005700_000005710_000005720_000005730_000005740_000005750_000005760_000005770_000005780_000005790_000005800_000005810_000005820_000005830_000005840_000005850_000005860_000005870_000005880_000005890_000005900_000005910_000005920_000005930_000005940_000005950_000005960_000005970_000005980_000005990_000006000_000006010_000006020_000006030_000006040_000006050_000006060_000006070_000006080_000006090_000006100_000006110_000006120_000006130_000006140_000006150_000006160_000006170_000006180_000006190_000006200_000006210_000006220_000006230_000006240_000006250_000006260_000006270_000006280_000006290_000006300_000006310_000006320_000006330_000006340_000006350_000006360_000006370_000006380_000006390_000006400_000006410_000006420_000006430_000006440_000006450_000006460_000006470_000006480_000006490_000006500_000006510_000006520_000006530_000006540_000006550_000006560_000006570_000006580_000006590_000006600_000006610_000006620_000006630_000006640_000006650_000006660_000006670_000006680_000006690_000006700_000006710_000006720_000006730_000006740_000006750_000006760_000006770_000006780_000006790_000006800_000006810_000006820_000006830_000006840_000006850_000006860_000006870_000006880_000006890_000006900_000006910_000006920_000006930_000006940_000006950_000006960_000006970_000006980_000006990_000007000_000007010_000007020_000007030_000007040_000007050_000007060_000007070_000007080_000007090_000007100_000007110_000007120_000007130_000007140_000007150_000007160_000007170_000007180_000007190_000007200_000007210_000007220_000007230_000007240_000007250_000007260_000007270_000007280_000007290_000007300_000007310_000007320_000007330_000007340_000007350_000007360_000007370_000007380_000007390_000007400_000007410_000007420_000007430_000007440_000007450_000007460_000007470_000007480_000007490_000007500_000007510_000007520_000007530_000007540_000007550_000007560_000007570_000007580_000007590_000007600_000007610_000007620_000007630_000007640_000007650_000007660_000007670_000007680_000007690_000007700_000007710_000007720_000007730_000007740_000007750_000007760_000007770_000007780_000007790_000007800_000007810_000007820_000007830_000007840_000007850_000007860_000007870_000007880_000007890_000007900_000007910_000007920_000007930_000007940_000007950_000007960_000007970_000007980_000007990_000008000_000008010_000008020_000008030_000008040_000008050_000008060_000008070_000008080_000008090_000008100_000008110_000008120_000008130_000008140_000008150_000008160_000008170_000008180_000008190_000008200_000008210_000008220_000008230_000008240_000008250_000008260_000008270_000008280_000008290_000008300_000008310_000008320_000008330_000008340_000008350_000008360_000008370_000008380_000008390_000008400_000008410_000008420_000008430_000008440_000008450_000008460_000008470_000008480_000008490_000008500_000008510_000008520_000008530_000008540_000008550_000008560_000008570_000008580_000008590_000008600_000008610_000008620_000008630_000008640_000008650_000008660_000008670_000008680_000008690_000008700_000008710_000008720_000008730_000008740_000008750_000008760_000008770_000008780_000008790_000008800_000008810_000008820_000008830_000008840_000008850_000008860_000008870_000008880_000008890_000008900_000008910_000008920_000008930_000008940_000008950_000008960_000008970_000008980_000008990_000009000_000009010_000009020_000009030_000009040_000009050_000009060_000009070_000009080_000009090_000009100_000009110_000009120_000009130_000009140_000009150_000009160_000009170_000009180_000009190_000009200_000009210_000009220_000009230_000009240_000009250_000009260_000009270_000009280_000009290_000009300_000009310_000009320_000009330_000009340_000009350_000009360_000009370_000009380_000009390_000009400_000009410_000009420_000009430_000009440_000009450_000009460_000009470_000009480_000009490_000009500_000009510_000009520_000009530_000009540_000009550_000009560_000009570_000009580_000009590_000009600_000009610_000009620_000009630_000009640_000009650_000009660_000009670_000009680_000009690_000009700_000009710_000009720_000009730_000009740_000009750_000009760_000009770_000009780_000009790_000009800_000009810_000009820_000009830_000009840_000009850_000009860_000009870_000009880_000009890_000009900_000009910_000009920_000009930_000009940_000009950_000009960_000009970_000009980_000009990_000010000>)  
Logging delay| Low logging delay| | | eval diff=_indextime - _time   
Log integrity in case of network interruption| Short network interruptions shouldn't lead to loss of events| | useACK, rsyslog: disk queue  
Secure transfer| Log transferred via TLS, Certificate validation, mTLS| |   
Multiline| There are no multiline proxy events| |   
Duplicates| There are no duplicate events| |   
Parsing| All events parsed correctly, action/src/dest fields are always present| |   
Settings location| All settings are placed inside of MWG App or TA| Settings can be placed in a wrong app if GUI is
used| Use btool to verify.  
You can access these and additional onboarding tips and checks using the [Data Onboarding Checklist](<https://classic.splunkbase.splunk.com/app/6881/>) Splunk app available on Splunkbase. Detailed description of the mcafee:webgateway:custom Log Format Why the new log format? Neither the default nor the previously used MWGaccess3 log formats provide enough information for effective SIEM analysis. These legacy formats provide very limited information about downloading and uploading risky files. Many SIEM correlation rules will not work properly if a transferred file is embedded as a part of a composite object (zip, iso, docx, etc.) or has different/faked media-type header or extension. The new log format provides the following use cases among many others: 

  * Even if a transaction was allowed, detect all potentially dangerous objects and log their true media-type, hash and size.
  * Even if a transaction was white-listed and not checked for the Web-Reputation and URL-Categorization - these checks are still performed in the Log Cycle after the transaction has been completed and the log event will contain them.
  * It performs a DNS lookup of dest_host, and if there is more than one IP, does a reverse DNS lookup of URL.Destination.IP to detect fast-flux C&C; Servers.

The custom log format (mcafee:webgateway:custom) consists of several parts:

  * Timestamp
  * Fixed set of fields: status, action, client_ip, url_protocol, http_method, dest, dest_port, bytes_out/bytes_in, duration/response_time. These fields have no field prefix - Splunk extracts them based on the log structure.
  * Variable set of fields: they are included in the log only if they are enabled AND exist. For example, a URL path will not be included for this URL: https://www.example.com/. These fields have either a short field prefix (for example up=) or consist of a single string (i.e. "tunnel") and can exist in any part of the log line, their order is not important. Any of the variable fields can be enabled and disabled on the MWG at any time, without the need to modify anything on the Splunk side. You can enable conditional logging for these fields, for example a query string can be logged only for some subset of categories, certificate information (Issuer, Common Name, Subject Alternative Names etc.) - only for suspicious transactions etc.

2021-02-26 14:36:46 -0600 200 allowed 192.168.2.1 https GET safebrowsing.googleapis.com 443 563/4156 38/17 up="/v4/threatListUpdates" ua="FF86-10.0" c="it" dip=142.250.185.n kex=112/112 cntx sccc=1302/1302 sslp=1.3/1.3 sslicn="GTS CA 1O1,GlobalSign" sslcn="upload.video.google.com" crtdays=-52 mbmismatch ctmt0 rul="L" rn=41/104 srcp=62407 conrt=0 b=524/4418 tunnel psrcip=192.168.2.1 psrcp=42550 piv=2.0/2.0 r=0 t=0/0/34/34/18/18/22/11/11 **Starting from version 5.0.0 of the app** , an updated log format was introduced that provides significantly improved search (up to 30 times) and reporting (up to 100 times) performance by leveraging [TERM](<https://docs.splunk.com/Documentation/Splunk/latest/Search/Quicktipsforoptimization#Use_the_TERM_directive_to_match_terms_that_contain_minor_breakers>) and [PREFIX](<https://docs.splunk.com/Documentation/Splunk/latest/SearchReference/Tstats#Performance>) directives: Search/reporting performance using normal search:|   
---|---  
Search/reporting performance using accelerated new log format und TERM/PREFIX:|  
The change between version 4 and version 5 is essentially the addition of a field prefix to every value, enabling the
use of the PREFIX directive. The new version of log is about 10-15% longer - consider that for a license usage:
2021-02-26 14:36:46 -0600 s=200 ac=allowed src=192.168.2.1 p=https m=GET d=safebrowsing.googleapis.com dp=443 bi=563
bo=4156 dur=38 rt=17 up="/v4/threatListUpdates" ua="FF86-10.0" c=it dip=142.250.185.n ckex=112 skex=112 cntx scc=1302
ssc=1302 sslcp=1.3 sslsp=1.3 sslicn="GTS CA 1O1,GlobalSign" sslcn="upload.video.google.com" crtdays=-52 mbmismatch ctmt0
rul="L" rnf=41 rne=104 srcp=62407 conrt=0 bfc=524 btc=4418 tunnel psrcip=192.168.2.1 psrcp=42550 rqv=2.0 rsv=2.0 r=0
tdns=0 tcon=0 tre=34 text=34 t=4.18.18.22.11 You can download a Cheat Sheet new log format with examples of usage:
<https://proxy-test.com/swg_cheatsheet.pdf> The app (version 5.+) supports both old and new format. If you want to
speedup search and reporting and also greatly reduce a load on the search head it is recommended to configure new log
format on the SWG. **Logging of URL fields:** Instead of logging a URL as-is (ex. http://www.example.com/wp/3?id=4), MWG
splits the URL into usable parts (url protocol, domain, url path, url query) which will be used on Splunk's end to
rebuild the url. This saves lot of processing and produces better results, in particular:

  * no need to parse url each time
  * correct domain extraction follows the [Public Suffix List](<https://publicsuffix.org/>), ensuring the domain field is populated with a specific/public top-level domain, rather than just the last two segments of the host name (i.e. for the hostname www.bbc.co.uk, bbc.co.uk is a domain and not just co.uk).
  * accelerated search using TERM/PREFIX has issues/limitations when applied to unparsed URLs

Default settings exclude logging of the URL query string (portion of the url after the question mark "?"). Enable it in the Web Data Model ruleset if required. Note that logging the query string greatly increases the length of log lines, potentially bloating TSIDX and leading to compromised search performance, heightened storage needs, and increased license usage. Conversely, enabling query string logging proves beneficial in numerous scenarios. Choose to enable it for each request or selectively as needed. An excerpt of the 100 most useful fields is provided below. MWG has about [900 properties](<https://success.myshn.net/Skyhigh_Secure_Web_Gateway_\(On_Prem\)/Secure_Web_Gateway_Reference/Web_Policy_Configuration/Properties>) that can be used for logging. Description of logged fields MWG field| CIM field| Comment  
---|---|---  
Timestamp| -|  | Property| Example| TIME_FORMAT / Comment  
---|---|---  
DateTime.ToISOString| 2010-03-22 11:45:12)| %Y-%m-%d %H:%M:%S  
DateTime.ToISOString with Milliseconds| 2010-03-22 11:45:12.123| %Y-%m-%d %H:%M:%S.%3N  
DateTime.ToISOString with Milliseconds and timezone| 2010-03-22 11:45:12.123 -0600| %Y-%m-%d %H:%M:%S.%3N %z  
**DateTime.ToISOString and timezone**| **2010-03-22 11:45:12 -0600**| **%Y-%m-%d %H:%M:%S %z**  
DateTime.ToGMTString| Mon, 22 March 2010 11:45:36 GMT| %a, %d %B %Y %H:%M:%S %Z  
DateTime.ToISO8601String| 2016-01-26T11:45:36.695Z| this time format can produce unexpected output, don't use it  
DateTime.ToNumber| Unix epoch time - 1512915182| %s  
DateTime.ToWebReporterString| [29/Oct/2010:14:28:15 +0000]| \\[%d/%b/%Y:%H:%M:%S %z\\]  
**Connection.IP** / Client.IP| src| Client.IP takes the value of X-Forwarded-For header  
Authentication.UserName| user|  
Message.TemplateName, Block.ID,  
Response.StatusCode, Protocol.FailureDescription,  
BytesFromServer, Command.Name,  
Action.Names| action| The action taken by the proxy: allowed, blocked, error or auth. Various MWG properties are used to
calculate correct action field.  
URL| url| Don't enable it, Splunk build URL based on uri components  
URL.Categories| category| MWG will try to categorize URL retroactively even if URL Filter was skipped in the Policy Rule
Sets. Add your internal domains to "internal Domains" list to avoid them being marked as "uncategorized"  
Header.Response.Get(Content-Type)  
MediaType.FromHeader| http_content_type| The content-type of the requested HTTP resource as reported by the web server
(can be wrong, faked or missing)  
Header.Request.Get(User-Agent)| http_user_agent| A short string (FF68-10.0 for Firefox 68 on Windows 10)  
LastSentLastReceivedServer| response_time| FSFRS-LSFRS+LSLRS is used to calculate response_time that includes sending
time  
Header.Request.Exists(Referer)| http_referrer| The HTTP referrer used in the request. The W3C specification and many
implementations misspell this as http_referer. Use a FIELDALIAS to handle both key names. This field is disabled by
default.  
URL.Domain of Header.Request.Exists(Referer)| http_referer_domain| The domain name contained within the HTTP referrer
used in the request. Disabled by default.  
Response.StatusCode| status| The HTTP response code indicating the status of the proxy request. MWG doesn't distinguish
between status sent by web server and status set by proxy, so this value can be misleading. Use action field to see what
the proxy action was.  
URL.Protocol| -| http/https/ftp etc. Used to re-build url  
Command.Name| http_method| GET/POST/PUT/OPTIONS etc  
URL.Host| dest| The host of the requested resource  
URL.Port| dest_port| The port of the requested resource  
BytesToServer| bytes_out| The number of outbound bytes transferred  
BytesFromServer| bytes_in| The number of inbound bytes transferred  
TimeInTransaction| duration| The time taken by the proxy event, in milliseconds  
URL.Path| uri_path| The path of the resource served by the webserver or proxy  
URL.ParametersString| uri_query| Not enabled by default. You can enable it for all requests or selectively  
Application.Name| app| The application detected or hosted by the server/site such as WordPress, Splunk, or Facebook  
Cache.Status eq TCP_HIT| cached| Indicates whether the event data is cached or not. Not enabled by default.  
Header.Get(Cookie)| cookie| The cookie file recorded in the event. Not enabled by default.  
URL.Destination.IP| dest_ip| It is important to record the destination IP at the moment of the request. A hostname can
be resolved to several IPs (think "moving target" CDN) so a DNS resolution a second later can lead to wrong result. Be
aware that MWG can be unable to do DNS resolution by itself and it can be a different IP after all if MWG is behind
upstream proxies.  
URL.Domain| url_domain| The domain name contained within the URL of the requested HTTP resource. It is extracted from hostname based on [Public Suffix List](<https://publicsuffix.org/>)  
Header.Request.GetAll| -| Returns a concatenated string of all the original request headers (separated by \r\n) as
received from client.  
Header.Response.GetAll| -| Returns a concatenated string of all the original response headers (separated by \r\n) as
received from server.  
Header.Request.Get(Via)| -| Via header in request  
Header.Response.Get(Via)| -| Via header in response  
Header.Response.Get(Location)| -| Location header in response  
Client.KeyExchangeBits| -| Normalized strength (symmetric) of the weakest link during the key exchange. Helps to detect
outdated client software  
Server.KeyExchangeBits| -| Normalized strength (symmetric) of the weakest link during the key exchange. Helps to detect
outdated servers which required special handling  
Server.Handshake.CertificateIsRequested| -| True, if the web server requests a client certificate (during the initial
SSL handshake) [*]  
ClientContext.IsApplied| -| A clue if HTTPS Scanner is enabled for this request  
Server.Cipher| -| Description of cipher/algorithms between proxy and server (e.g. ECDHE-RSA-AES256-GCM-SHA384)  
Client.Cipher| -| Description of cipher/algorithms between client and proxy (e.g. ECDHE-RSA-AES256-GCM-SHA384)  
SSL.Server.Protocol| -| SSL/TLS protocol used between proxy and server (e.g. TLSv1.2 TLSv1.1 TLSv1.0 SSLv3.0 unknown).  
SSL.Client.Protocol| -| SSL/TLS protocol used between client and proxy (e.g. TLSv1.2 TLSv1.1 TLSv1.0 SSLv3.0 unknown)  
SSL.TransparentCNHandling| -| true for ssl connections where the CN is not known until the server handshake is done  
Server.CertificateChain.Issuer.CNs| ssl_issuer_common_name| The issuer common names of the certificate chain (bottom-up
including the self-signed root CA, empty without certificate verification) [*]  
SSL.Server.Certificate.CN| ssl_subject_common_name| The common name of the server certificate [*]  
Server.Certificate.SHA2-256Digest| ssl_hash| The hex-encoded sha2-256 digest of the server certificate [*]  
Server.Certificate.AlternativeCNs| -| This list stores all alternative subject names stored in the server certificate's
extensions section [*]  
Server.Certificate.DaysExpired|  _ssl_end_time_|  Stores how many days the server certificate is expired. Negative
values mean that it is still valid [*]  
DNS.Lookup(URL.Host)| -| List of IP addresses of URL.Host if there are more than one.  
DNS.Lookup.Reverse(URL.Destination.IP)| -| List of hostnames for the destination IP. Very often it does not equal the
requested hostname  
Body.NumberOfChildren| -| Number of embedded objects for archive or document [*]  
Body.NestedArchiveLevel| -| The current archive level, used to calculate the max level of the embedded object [*]  
IsCompositeObject| -| True, if current file is composite (archive or office document) [*]  
Body.IsEncryptedObject| -| True, if current object is encrypted  
Antimalware.Proactive.Probability| -| Malware probability value  
Antimalware.Infected| used for:  
file_name  
file_hash| True, if virus was found, false otherwise  
Antimalware.VirusNames| signature| List of names of found viruses  
Application.Reputation| -|  reputation of the application  
Authentication.Method| authentication_method| authentication method (NTLM, Kerberos, etc.)  
Authentication.Realm| -| authentication realm (i.e. AD directory name)  
Authentication.UserGroups| -| User Groups, can be filtered with "Authentication UserGroups to log" list  
Authentication.FailureReason.Message| signature (?)| Human readable authentication failure reason description  
Authentication.Failed| action (in Authentication DM)| It is true if credentials were provided but the authentication has
failed  
Cache.IsCacheable| -| True, if the response is cacheable and web cache is enabled  
Cache.Status| -| TCP_HIT for a web cache hit, TCP_MISS_RELOAD for a miss, TCP_MISS_VERIFY if the data in the cache was
outdated, TCP_MISS_BYPASS for bypass based on I/O load  
Cache.IsFresh| -| True, if the response is validated or not read from web cache  
MagicBytesMismatch| -| True, if Mime Type from header doesn't match to detected Mime Type [*]  
EnsuredTypes| -| List of Mime Types detected by signatures (with high probability of detection)  
NotEnsuredTypes| -| List of Mime Types detected by signatures (with low probability of detection)  
IsMediaStream| -| Determine if current transaction is media stream  
StreamDetector.Probability| -| Probability value for media stream detection  
StreamDetector.MatchedRule| -| Returns name of matched streaming detection rule  
Rules.CurrentRule.Name| -| The name of the currently evaluated rule  
Rules.EvaluatedRules| -| List of all IDs of rules/rule sets, which have been evaluated  
Rules.FiredRules| -| List of all IDs of rules/rule sets, where the condition was true  
Proxy.IP| -| Stores the Webgateway IP  
Proxy.Port| -| Stores the Webgateway port  
Client.ProcessName| -| Stores the process name that initiated the connection, e.g. provided by MCP  
Client.SystemInfo| -| Client System Information (provided by MCP)  
DNS.Lookup.Reverse(client_ip)| src_ip| Hostname of the client  
Connection.Protocol| -| The protocol that the client uses to communicate with the proxy (HTTP, HTTPS, FTP, IFP, SSL,
ICAP, XMPP, TCP or SOCKS)  
Connection.Port| src_port| Stores the port of the client  
Connection.RunTime| -| Connection run time (current time minus start time) in seconds  
BytesFromClient| -| Number of bytes received from the client for this request  
BytesToClient| -| Number of bytes sent to the client for this request  
Tunnel.Enabled| -| True, if a HTTP or HTTPS tunnel was enabled - the server response bypassed the response cycle  
Proxy.Outbound.IP| -| Stores the IP which is used as the Outbound Source IP by Webgateway when connecting to onward
server  
Proxy.Outbound.Port| -| The port which is used as the source port by Webgateway when connecting to onward server  
ProtocolAndVersion| -| protocol and version of the request/response (HTTP/1.1, HTTP/2.0)  
Error.ID| -| ID of error  
Error.Message| -| Name of error  
URL.Reputation| \- | Returns the web reputation value for the current URL. Range is from -127 to 127, where -127 means 'Minimal Risk' and 127 means 'High Risk'.  
URL.Geolocation| -| Returns the geolocation of the current URL. The geolocation is the code of the country in which the
webserver is located, that hosts the requested resource. The country code is given in ISO 3166 notation. Note: The
setting "Disable local GTI database" must be enabled in the URL Filter settings; otherwise this property is not filled.  
TimeInRuleEngine| -| Milliseconds currently spent in rule engine. If used in log handler, time consumed by the rule
engine from start to the end of a transaction  
FirstSentFirstReceivedServer  
LastSentLastReceivedServer  
FirstReceivedFirstSentClient  
LastReceivedLastSentClient  
LastSentFirstReceivedServer | -| Time between first byte sent to server and first byte returned from server in milliseconds etc...  
HandleConnectToServer| -| Time to connect to a server in milliseconds  
ResolveHostNameViaDNS| -| Time to resolve a host name via DNS  
TimeInExternals| -| Milliseconds currently spent waiting for external responses, e.g. from AV scanner, domain controller
for NTLM authentication or URL cloud categorization  
  
  * [*] - requires a rule(s) from Splunk Log Template > RuleSet Library be placed in the corresponding Policy Rule Set to make these properties available in the logging cycle.

Other logs

  * Audit log Audit logs (/opt/mwg/log/audit/audit.log) contains all changes and activity made by administator(s) using UI or REST interface. Audit events can be sent to Splunk using a UF or custom syslog configuration. Almost 70 actions are mapped to Authentication and Change CIM Data Models: Action| action| change_type| object_category  
---|---|---|---  
ACTIVATE_LICENSE_FILE| modified| | license  
ADDED_ADMINROLE| added| AAA| role  
ADDED_APPLIANCE| added| | appliance  
ADDED_CONTENT| added| filesystem| config  
ADDED_GROUP_ROLE_MAPPING| added| AAA| role  
ADDED_RULES| added| | config  
ADDED_SYSTEM_FILES| added| filesystem| file  
ADDED_TEMPLATE_DIRECTORIES| added| filesystem| directory  
AUTHENTICATE_WITH_EXTERNAL_SERVER| success| |   
BACKUP_TRIGGERED| created| | backup  
CREATED_NEW_LIST| added| | config  
CREATED_NEW_RULE| added| | config  
CREATED_NEW_RULEGROUP| added| | config  
CREATED_NEW_SETTINGS| added| | config  
CREATED_NEW_USER| added| AAA| user  
CREATED_NEW_USER_DEFINED_PROPERTY| added| | config  
DASHBOARD_DATA_RESET| deleted| |   
DATE_CHANGED| modified| | config  
DELETED_ADMINROLE| deleted| AAA| role  
DELETED_APPLIANCE| deleted| | appliance  
DELETED_CONTENT| deleted| | config  
DELETED_LIST| deleted| | config  
DELETED_LOG_HANDLER| deleted| | config  
DELETED_RULE| deleted| | config  
DELETED_RULE_GROUP| deleted| | config  
DELETED_RULES| deleted| | config  
DELETED_SETTINGS| deleted| | config  
DELETED_TEMPLATE_DIRECTORIES| deleted| | directory  
DELETED_TEMPLATE_FILES| deleted| | file  
DELETED_USER| deleted| AAA| user  
DELETED_USER_DEFINED_PROPERTY| deleted| | config  
EXPORT_PRIVATE_KEY| read| | config  
FILE_DOWNLOAD| read| | file  
FILE_UPLOAD| added| filesystem| file  
FILES_DELETE| deleted| filesystem| file  
FORCED_USER_LOGOUT| logout| |   
JOINED_NTLM| modified| | config  
LEFT_NTLM| modified| | config  
MODIFIED_ADMINROLE| modified| | role  
MODIFIED_APPLIANCE_SETTINGS| modified| | config  
MODIFIED_CLUSTER_CONFIGURATION| modified| | config  
MODIFIED_CONTENT| modified| | config  
MODIFIED_CATALOG| modified| | config  
MODIFIED_GROUP_ROLE_MAPPING| modified| | role  
MODIFIED_LIST| modified| | config  
MODIFIED_NTLM| modified| | config  
MODIFIED_RULE| modified| | config  
MODIFIED_RULE_GROUP| modified| | config  
MODIFIED_SETTINGS| modified| | config  
MODIFIED_SYSTEM_FILES| modified| filesystem| file  
MODIFIED_TEMPLATE_FILES| modified| filesystem| file  
MODIFIED_USER| modified| AAA| user  
MODIFIED_USER_DEFINED_PROPERTY| modified| | config  
MOVED_RULE_GROUPS| modified| | config  
MOVED_RULES| modified| | config  
REORDERED_CONTENT| modified| | config  
RESTORE_FAILED| modified| | config  
RESTORE_STARTED| pending| | config  
RESTORE_SUCCEDED| modified| | config  
SAVING_FAILED| read| | config  
SYSTEM_LIST_UPDATE| modified| | config  
TRIGGER_ACTION| pending| | config  
USER_LOGIN| success| |   
USER_LOGIN_FAILED| failure| |   
USER_LOGOUT| logout| |   
USER_TIMED_OUT| timeout| |   
Audit.log can be sent to Splunk using either the UF or Syslog.

    * using UF This method sends audit events "as is" - multiline, with all details. inputs.conf:
          
          [monitor:///opt/mwg/log/audit/audit*]
          #index=proxy_audit
          sourcetype=mcafee:webgateway:audit
          

    * using syslog (2 methods):
      * using rsyslog file monitor: This method sends audit events "as is" - multiline, with all details.
        * create a new file /etc/rsyslog.d/swg_audit_log.conf with following content:
              
              module(load="imfile")
              
              # exclude this facility.severity in rsyslog.conf: local5.!=info
              input(type="imfile"
                    File="/opt/mwg/log/audit/audit.log"
                    Tag="swg_audit_log"
                    Facility="local5"
                    Severity="info")
              
              template(name="msg_only_udp" type="string" string="%msg%")
              # template(name="msg_only_tcp" type="string" string="%msg:2:$%")
              
              if $programname == "swg_audit_log" then {
                  action(type="omfwd"
                         Target="splunk.server"
                         Port="10514"
                         Protocol="udp"
                         Template="msg_only_udp")
              }
              

        * modify rsyslog.conf via UI to exclude local5.info: add local5.!=info to the line with /var/log/messages
        * restart rsyslog: systemctl restart rsyslog
      * Write Audit log to syslog: This method produces one-line events (easier to read, but less details)
        * Configuration > Log File Manager > Settings for the Audit Log: enable "Write audit log to syslog" checkbox.
        * Add to rsyslog.conf using UI (modify syslog-server and port): 
              
              $template msg_only_udp,"%msg%" # An alternative format, without a syslog header, for UDP
              if $programname == 'mwg' and $syslogfacility-text == 'auth' and $syslogseverity-text == 'info' then @splunk-server:10514;msg_only_udp
              

        * modify rsyslog.conf via UI to exclude auth.info: add auth.!=info to the line with /var/log/messages
        * restart rsyslog: systemctl restart rsyslog
  * /var/log/messages log /var/log/messages is a system log file that records various system messages and events To send it using UF (recommended): 
    * add a user splunk (for Splunk) or splunkfwd (for Splunk Forwarder) to the adm group (using vigr or by modifying /etc/group): `adm:x:4:mwgc,tomcat,splunk`
    * create a monitor stanza in local/inputs.conf:
          
          [monitor:///var/log/messages*]
          # host = your_host
          # index = proxy
          sourcetype = linux_messages_syslog

    * systemctl restart SplunkForwarder
To send it using syslog:

    * create a new file /etc/rsyslog.d/swg_var_log_messages_log.conf with following content (take the log string from the rsyslog.conf (UI), modify splunk host and port): 
          
          $template msg_only_udp,"%msg%" # An alternative format, without a syslog header, for UDP
          *.info;daemon.!=info;daemon.!=debug;daemon.!=notice;mail.none;authpriv.none;cron.none @splunk:10614;msg_only_udp
          

The previous setup sends a mix of various syslog severities and facilities to the receiver, making it more difficult to
filter and separate the syslog stream. An alternative setup will read from /var/log/messages and send the logs using a
custom severity/facility combination:

          
          ###############################################
          # var_log_messages.conf – dedicated rule set  #
          ###############################################
          
          module(load="imfile")                       # <- load only once globally
          
          # very small template: send the raw line only
          template(name="mwgOnlyMsg" type="string" string="%msg%")
          
          # ---------- ruleset that talks to the log-collector -----------------
          ruleset(name="var_log_messages"){
              action( type="omfwd"
                      target="syslog.example.com"
                      port="514"
                      protocol="udp"
                      template="mwgOnlyMsg"
                      # Action.SendingQueue.Size="10000"
                      Action.ResumeRetryCount="-1"
              )
              stop                                     # absolutely nothing else
          }
          
          # ---------- file monitor ------------------------------------------------
          input(
              type="imfile"
              File="/var/log/messages" 
              Tag="var_log_messages"        # colon will be auto-appended
              Facility="local7"
              Severity="info"
              addMetadata="on"                         # if you need %$!metadata!filename%
              ruleset="var_log_messages"                  # every line -> out
          )
          
          

    * restart rsyslog: systemctl restart rsyslog
    * assign it to default sourcetype linux_messages_syslog
  * /var/log/secure log /var/log/secure is a system log file that contains security-related events and authentication information, for example: 
        
        pam_unix(sshd:session): session opened for user root by (uid=0)
        pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=10.1.2.3  user=root

To send it using UF (recommended):

    * add a user splunk (for Splunk) or splunkfwd (for Splunk Forwarder) to the adm group (using vigr or by modifying /etc/group): `adm:x:4:mwgc,tomcat,splunk`
    * create a monitor stanza in local/inputs.conf:
          
          [monitor:///var/log/secure*]
          # host = your_host
          # index = proxy_audit
          sourcetype = linux_secure
          # sourcetype = mcafee:webgateway:secure

    * systemctl restart SplunkForwarder
To send it using syslog:

    * create a new file /etc/rsyslog.d/swg_var_log_secure_log.conf with following content (modify splunk host and port): 
          
          $template msg_only_udp,"%msg%" # An alternative format, without a syslog header, for UDP
          authpriv.* @splunk:10714;msg_only_udp 
          

    * restart rsyslog: systemctl restart rsyslog
    * assign it to default sourcetype linux_secure
An example of usage:

    
    source="/var/log/secure" host="prx*" index="proxy" sourcetype="linux_secure" authentication fail* | rex "(?\d+) more authentication failures" | eval failure_count=if(isnotnull(failure_count),failure_count,1)| stats sum(failure_count) AS count values(host) AS host by process rhost user

  * /opt/mwg/log/mwg-errors The folder /opt/mwg/log/mwg-errors contains various types of logs:  Log name| Log type| Comment  
---|---|---  
mwg-core| text, single line| mwg-core logging | mwg-coordinator| text, single line| mwg-coordinator logging | mwg-ui| text, multi line| mwg-ui Tomcat logging | mwg-logmanager| text, single line| mwg-logmanager logging | mwg-uideserialization| text, single line| mwg-ui deserialization logging | mwg-sysconfd| text, single line| mwg-sysconfd logging | mwg-monitor| text, single line| mwg-monitor logging | mwg-saas-connector| text, single line| mwg-saas connector logging | *.bin| binary| cannot be parsed. Can be excluded, but the presence of such logs is also a good hint about potential issues. To send it using UF (recommended): 
    * add a user splunk (for Splunk) or splunkfwd (for Splunk Forwarder) to the mwg group (using vigr or by modifying /etc/group): `mwg:x:199:tomcat,splunk`
    * create a monitor stanza in local/inputs.conf:
          
          [monitor:///opt/mwg/log/mwg-errors/mwg*log]
          sourcetype = mcafee:webgateway:mwg-errors
          # index = proxy_audit

    * systemctl restart SplunkForwarder
To send it using syslog:

    * Create a file /etc/rsyslog.d/swg_opt_mwg_log_mwg_errors.conf with following content:
          
          #############################################
          # swg_opt_mwg_log_mwg_errors.conf – dedicated rule set  #
          #############################################
          
          module(load="imfile")                       # <- load only once globally
          
          # very small template: send the raw line only
          template(name="mwgOnlyMsg" type="string" string="%msg%")
          
          # ---------- ruleset that talks to the log-collector -----------------
          ruleset(name="mwgErrors_out"){
              action( type="omfwd"
                      target="syslog.example.com"
                      port="514"
                      protocol="udp"
                      template="mwgOnlyMsg"
                      Action.SendingQueue.Size="10000"
                      Action.ResumeRetryCount="-1"
              )
              stop                                     # absolutely nothing else
          }
          
          # ---------- file monitor ------------------------------------------------
          input(
              type="imfile"
              File="/opt/mwg/log/mwg-errors/mwg-co*.errors.log" # monitor both mwg-core and mwg-coordinator
              Tag="swg_mwg-errors_mwg-core_log"        # colon will be auto-appended
              Facility="local6"
              Severity="info"
              addMetadata="on"                         # if you need %$!metadata!filename%
              ruleset="mwgErrors_out"                  # every line -> out
          )
          
          

    * systemctl restart rsyslog
Self-Monitoring SSWG offers approximately 300 system properties and counters that can be collected from all appliances
and analyzed. These include:

    * System Details: Information about CPU load, memory usage, disk usage, and more.
    * Performance Statistics: Metrics such as the number of requests.
    * Network Statistics: Data on bytes sent/received, close waits, etc.
    * SWG version and Antivirus modules version
    * Proxy Statistics: Details like the current number of connections and client count.
    * and many others
This statistic can be collected and sent along with an access log to Splunk. A scheduled rule engine trigger or a cron
job can be used to perform a request to a non-existent domain called ‘reporting.test’. The monitoring data is sent to
Splunk as part of the URL path, for example:  
2024-03-09 16:21:04 +0100 s=403 ac=blocked src=255.255.255.255 p=http m=- d=reporting.test dp=80 bi=0 bo=0 dur=0 rt=0
up="/hostname_proxy24_ProxyIP_10.20.30.40_MWGVersion_12.2.5_MWGBuildNumber_47878___Lic336_CPULoad4_CPUIdle94_MemFree13645803520_MemUsed7259697152_...."  
In an example above the proxy hostname is proxy24, the IP 10.20.30.40, the software version 12.2.5 and the build 47878,
the remaining license 336 days and so on.  
  
A pre-configured rule set is provided with the app package (located in the MWG folder). Consider it as a lightweight
alternative for full-fledged monitoring with SNMP but without installing and configuring any software besides Splunk.
This self-monitoring is especially useful for a PoC and quick troubleshooting.  
  
A full list of all available counters can be viewed here: List of Counters. The statistic counters can be sent from Web
Gateway to Splunk every 60 seconds via the already configured mcafee:webgateway:custom sourcetype - no need to configure
SNMP or firewall rules. The counters are sent along with other events in the same mcafee:webgateway:custom sourcetype.
Following 3 steps are all that is needed to enable it:

    1. Import a self-monitoring RuleSet from the MWG folder of the app: Policy > RuleSets (under Policy RuleSets, **not** in Log Handler) > Add > Top Level RuleSet > Import Rule Set from Rule Set Library > Import from file
    2. Place the Monitoring RuleSet as a first top-level rule set
    3. Configure a periodic rule engine trigger (Configuration > Appliances > [each appliance] > Proxies (HTTP..) > Advanced Settings > Periodic Rule Engine Trigger > "http://reporting.test", Trigger Interval: 60 seconds). Alternatively you can create a cronjob on each appliance: * * * * * curl -x proxyip:proxyport http://reporting.test/ 2>&1 >/dev/null  
  
  

The ruleset can be modified to include other counters as needed. The self-monitoring will be extended in future versions, so check for updates if you find this feature useful. Next steps / Action Plan | You want to:| Action  
---|---  
complete setup|

    * Double-check the Onboarding checklist
    * If the timestamp format was modified, adjust validation regex in the Splunk RuleSet > DEBUG > Verify Log Structure and report if it is not correct
    * Search for logging errors: LOGERR1 OR LOGERR2 OR LOGERR3  
use non-default index| Modify "index_and_sourcetype" macro to include an index (i.e. 'index=proxy AND
sourcetype="mcafee:webgateway:custom"')  
improve search speed and speedup reporting| Upgrade to version 5.x and upgrade to the new log format, the app version
5.x supports all previous log formats and introduces a new format for faster searches (speedup up to 30 times) and
faster reports (speedup up to 100 times).  
implement Common Information Model (CIM)| Install [Splunk Common Information Model (CIM)](<https://splunkbase.splunk.com/app/1621/>) App  
import new version of the Splunk Logging Ruleset but keep all modifications| Use a mwg_xml2txt and dump_logging_fields
scripts to see differences between versions.  
build accelerated DM| Don't put highly variable strings like uri_path, uri_query, url in accelerated DM unless you
really need them  
improve proxy performance, find causes of high latency| Check errors, web cache (should be disabled!), timers (esp. DNS)  
configure data retention| Configure frozenTimePeriodInSecs TBD  
implement some GDPR requirements| Check if personally identifiable information (PII) should be removed, encrypted,
obfuscated or masked. TBD  
investigate a breach/incident| Create a copy of all relevant events (also from other sources) to avoid aging it out. TBD  
implement a 4-eyes principle| It can be implemented either on the proxy side or using splunk. TBD  
mask/obfuscate some fields| It can be implemented either on the proxy side or using splunk. TBD  
send events to other destination besides splunk| Modify rsyslog.conf or use "Route and filter data". TBD  
customize or create own views and reports| Dashboard Customization  
add new fields| At first, check if a required field is already available. Send me an email, so I can include it in the
log template. If the field is too specific, consider creating a new ruleset in the Splunk ruleset and put all new fields
there - this step will greatly simplify an update/migration. To benefit from the PREFIX/TERM acceleration, if the value
can't contain any major breakers, use key=value format.  
exclude some events from search| Create a macro to exclude some sources, destinations or user-agents and add it to a
query  
exclude some events from logging| On MWG: Modify existing list "Domains not to log" or create own excluding rules  
improve search performance|

    * rewrite queries to use base search (be aware of base search restrictions)
    * rewrite queries to use accelerated data model
    * use TERM/PREFIX (implemented in the version 5.x) [[1]](<https://conf.splunk.com/files/2020/slides/PLA1089C.pdf>)
    * add to index_and_sourcetype macro: DIRECTIVES(REQUIRED_EVENTTYPES(eventtypes=""),REQUIRED_TAGS(tags="")) \- helps on busy SH with many installed TAs [[1]](<https://conf.splunk.com/files/2017/slides/splunk-search-and-performance-improvements.pdf>)  
correctly log FTP/FTPoverHTTP connections| Due to the nature of FTP requests, the MWG events don't correctly reflect
connection type. This requires more work, both on MWG and on Splunk side. TBD  
use TERM/PREFIX for fields with major breakers like User-Agent| Build a ua field on SWG without major breakers using
String.ReplaceAllMatches( field, regex([^\w\\-]+),"_")  
work with IPv6 addresses| TBD  
you have an idea how to improve this app or need support| Write an email to splunkcompek.net  
FAQ

    * **Q** : The default dashboard filter (user, src, destination and user-agent) is not sufficient, how to add other filter conditions? **A** : You can use any of the default input fields to add your own SPL, for example in a "User" input field enter * block_id=80 to show all matching events with block_id equals 80. Also read Dashboard Customization
    * **Q** : MWG or SWG? **A** : MWG underwent several acquisitions: 
      * initially named Webwasher (-2004)
      * Cyber Guard Webwasher (2004-2006)
      * Secure Computing Webwasher (2006-2008)
      * McAfee Web Gateway (2008-2013)
      * Intel Security Web Gateway (SWG) (2013-2017)
      * then again as McAfee Web Gateway (2017-2022)
      * now SkyHigh Security Web Gateway (SWG) (2022-).
    * **Q** : You want to extend/modify/improve the app/documentation or get a beta build. **A** : Send your requests to splunkcompek.net
Dashboard Customization

Sometimes it is required to add own inputs elements, for example a dropdown list of indexes or group of hosts. This can
be easily be done using sed. Each view (starting from the version 5.0.6) contains a placeholder line that can be used to
insert your input element. In a following example we add an input element and modify search queries in SPL code to use a
new token.

    * Prepare a text file (for example /tmp/textblock.txt) with an input element:
          
          <input type="dropdown" token="index_and_sourcetype_macro" searchWhenChanged="true">
                <label>Index</label>
                <choice value="`index_and_sourcetype_prod`">Prod</choice>
                <choice value="`index_and_sourcetype_nonprod`">Non-Prod</choice>
                <default>`index_and_sourcetype_prod`</default>
              </input>

    * Perform following commands line by line:  

          
          su - splunk # change to splunk user
          mkdir -p $SPLUNK_HOME/etc/apps/McAfeeWebGateway/local/data/ui/views # create a local folder
          cp $SPLUNK_HOME/etc/apps/McAfeeWebGateway/default/data/ui/views/*xml $SPLUNK_HOME/etc/apps/McAfeeWebGateway/local/data/ui/views # copy views from default to the local folder
          cd $SPLUNK_HOME/etc/apps/McAfeeWebGateway/local/data/ui/views # cd to the local folder
          

    * Some views, like "audit", "audit_timeline" and "mwg_errors" (and maybe other views in the future) use different macros, you can skip them when adding a snippet: 
          
          for file in *xml; do
            if [ "$file" != "mwg_errors.xml" ] && [ "$file" != "audit.xml" ] && [ "$file" != "audit_timeline.xml" ]; then
              sed -i '/<!-- Placeholder for additional inputs -->/r /tmp/textblock.txt' "$file"
              sed -i '/`index_and_sourcetype`/$index_and_sourcetype_macro$/g' $file
            fi
          done

    * Do debug/refresh

If you just need to add the same text block for all views use this sed command instead:

    
    for file in *xml; do sed -i '/<!-- Placeholder for additional inputs -->/r /tmp/textblock.txt' $file; done # add a textblock to each view

Troubleshooting

    * Use the built-in **Troubleshooting & Log Analyzer** view for automated diagnostics, sourcetype detection, field extraction health check, and syslog header validation.
    * Has the corresponding MWG Logging RuleSet been imported?
    * Are some charts and tables empty? - Check that the required fields and values are collected by the Splunk Rule Set in the Logging Cycle, activate them as needed.
    * Does a "Last Rule" exist on MWG?
    * Were the supplement rules copied in the Policy Rule Sets?
    * Is Splunk getting any input?
    * Does a search for index=* (sourcetype=mcafee:* OR sourcetype=MWGaccess3) output raw events?
    * Does Splunk recognize timestamps correctly?
    * If sent via Syslog - was the Syslog header part correctly removed?
    * Are there any errors in $SPLUNK_HOME/var/log/splunk/splunkd.log?
    * Problem: Events are not parsed correctly because an extra space character before the timestamp. Solution: modify the log template in MWG to $template msg_only,"%msg:2:$%"
    * Problem: Events are not parsed correctly because first character(s) of the timestamp is cut off. Solution: modify the log template in MWG to $template msg_only,"%msg:1:$%" or even $template msg_only,"%msg:$%"
    * Problem: Imported Splunk RuleSet has some RuleSets marked red - some properties like Header.Request.GetAll are available only on new MWG versions (10+) and rules containing such "unknown" properties will be marked red if imported on older MWG versions. Just delete these rules or upgrade the MWG to the newest 10+ version.  
  
  
  
If a TLS Ruleset is shown red, modify it as follows (delete a second condition "SSL.Server.Certificate.SignatureMethod
is not in list **null** " and replace it with "SSL.Server.Certificate.SignatureMethod is not in list **Safe Signature
Algorithms** ". Safe Signature Algorithms is a McAfee supplied list that should already be present in recent MWG
versions:  
  
  
  
  
  
  
If the list "Safe Signature Algorithms" is not present, create it as following:  

    * Problem: Rule value is empty therefore Rule Statistics doesn't work on MWG 11.0-11.0.2. Answer: this is a bug in Map.GetStringValue function that was fixed in MWG 11.1, please update your MWG or temporarily disable Log Handler > Splunk > Rules > "Rules.CurrentRule.Name (short if exists in Rule Map)" rule.
    * Problem: Some fields are not extracted correctly or missing. Answer: The configuration from another app can override or suppress the intended field extraction. The **btool** doesn't work well in such situations, use this SPL on Search Head (replace searchtype as needed): 
          
          | rest splunk_server=local /servicesNS/-/-/configs/conf-props search="eai:acl.app=*" 
          | search title="mcafee:webgateway:custom" (title!=null) (eai:acl.app!=null)
          | rename eai:acl.app as app, eai:acl.perms.read as read, eai:acl.sharing as sharing, eai:acl.perms.write as write
          | fields - updated published id eai* null*
          | fields title author splunk_server app read write sharing **
          | eval title="[".title."]"
          | foreach * [eval title=if("<<FIELD>>"="author" OR "<<FIELD>>"="splunk_server" OR "<<FIELD>>"="app" 
          OR "<<FIELD>>"="read" OR "<<FIELD>>"="write"  OR "<<FIELD>>"="sharing" 
          OR "<<FIELD>>"="title" OR '<<FIELD>>'="",title,mvappend(title,"<<FIELD>>"." = ".'<<FIELD>>'." "))]
          | fields title author splunk_server app read write sharing
          | search title=**
          

Summary of changes

    * **6.0.0** \- Major documentation overhaul. New Interactive Deployment Wizard for guided configuration. Updated product compatibility: Splunk Enterprise 8.x/9.x/10.x, CIM 4.x/5.x/6.x. New views: Troubleshooting & Log Analyzer, Linux Syslog, Linux Secure, Certificates, Fast Search. Audit Timeline no longer requires 3rd party app (uses Dashboard Studio, Splunk 9.1+). MWGaccess3 formally deprecated. Added Malware Data Model mapping
    * 5.0.10 - improved views: mwg_errors, traffic, unfiltered_threats. New (hidden) view "troubleshooting for initial setup and debugging (contains following tables: Sourcetype presence, Sourcetype presence + related Apps, Sourcetype detection). The eventtype "Web" renamed to "mcafee_webgateway_Web". New version of Log Template - v0.14 - fixed extraction of Referer.Domain, prepared NextHopProxy.Address field, prepared Authentication.Method from RawCredentials to detect insecure Basic-over-NTLM Authentication.
    * 5.0.9 - fixed a typo in the sourcetype name "mcafee:webgateway:mwg_errors" (mwg-errors -> mwg_errors)
    * 5.0.8 - added searchWhenChanged=true to all inputs, visual improvements in Errors and MWG_Errors views, fixed a search error in Errors view, fixed macro "index_and_sourcetype_mwg_errors", added a sourcetype definition for "mcafee:webgateway:mwg-errors".
    * 5.0.7 - added mwg_errors and unfiltered threats views, added new columns to Traffic and Traffic5 views, new macro "index_and_sourcetype_mwg_errors".
    * 5.0.6 - new version of the log template: improved creation of ua2 field (for accelerated search). Added accelerated view User-Agents+. Each view has a placeholder to simplify custom modifications. Improved Errors-view. Improved Traffic and Traffic+ statistics. Minor fixes.
    * 5.0.5 - added search macro for Audit_Timeline, clarified configuration options for the least-privileged splunkfwd user on the UF and other security options.
    * 5.0.4 - added new views: Search+ (accelerated) Audit-Timeline and Bad_Reputation. Minor fixes in Monitoring and Authentication views. Added Sparklines to Monitoring view. Added an option to switch between Bytes/MB/GB to Overview page. Added drilldowns to URL (accelerated) view. props.conf - fixed extraction of the AuthMethod field. Added documentation about handling of punycode domains using custom segmenters.conf. Search renamed to Raw_Search to avoid overlapping with other savedsearches. transforms.conf: in the rewrite_host_from_host_field extraction - the field name called now swg and not host to avoid accidental overwriting of the host field. Improved documentation. Added a new improved version of the logging template.
    * 5.0.3 - added parsing of SSE/WGCS logs up to API version 12.
    * 5.0.2 - added documentation about logging of /var/log/messages and /var/log/audit, fixed missing tokens in protocols view.
    * 5.0.1 - minor fixes.
    * 5.0.0 - New major release, backwards compatible with old 4.x versions and old versions of log. This version provides major speedup (up to 100-fold) of reports using PREFIX (requires Splunk 8 and above). To use this new mode a slight log format modification required, read README for details.
    * 4.0.14 - added interactive online configuration builder and new views: monitoring, DoH and certificates. Added experimental support for DoH (DNS over HTTPS) and Client-Hints. Improved documentation.
    * 4.0.13 - added HTTP headers analysis view, new MWG Logging template, a supplemental script to compare MWG Logging templates to facilitate logging template upgrades. Improved documentation to include more best practices.
    * 4.0.12 - an internal release
    * 4.0.11 - added a lookup of executables that can be used for download and exfiltration (https://lolbas-project.github.io/). Fixed a TIME_PREFIX for wgcs_v5
    * 4.0.10 - fixed extraction of authentication_method, authentication_realm, auth_failure_message and auth_failure_id fields (Thank you ML!)
    * 4.0.9 - improved WGCS regexes, now URL, rule name and User-Agent fields that contain quote character(s) are parsed correctly. Improved a TIME_PREFIX to fix parsing errors. New CIM fields added. Added distsearch.conf to enable replication of macros.
    * 4.0.8 - added sc_admin role to default.meta
    * 4.0.7 - support for MWG audit log, feedback form, and a new auth method statistics view
    * 4.0.6 - better README with more examples, global export in default.meta, MWG Log has autorotation/autodeletion enabled in case it is not enabled globally
    * 4.0.5 - added parsing of McAfee Web Gateway Cloud Service (WGCS) Logs
    * 4.0.4 - applied required changes to maintain compatibility with Splunk Cloud (use jQuery 3.5), improved documentation, minor fixes
    * 4.0.3 - added Security Posture view, minor fixes
    * 4.0.2 - improved Error Analysis view, minor fixes
    * 4.0.1 - new major release, new log format, better documentation, new views: SSL, Errors, Uploads
    * 3.0.7 - committed changes in props.conf and transform.conf by Myron Davis, added a contributors section in README, clarifications for the installation process in README
    * 3.0.6 - enabled Splunk CIM (Common Information Model) version 4, by Myron Davis, compatibility with Splunk App for Enterprise Security, by Myron Davis, renamed App folder from AppForMcAfeeWebGateway to McAfeeWebGateway to match it with the app ID
    * 3.0.5 - The App package now includes a step-by-step installation instruction with screenshots, the log structure has been reordered to avoid overwriting of parameters
    * 3.0.4 - Introduced new short log format, many redundant fields removed, cleanup, faster search, and some panels were merged. This new major version isn't compatible with the version 2.xx
Contributors/Attributions

    * Thanks to Myron Davis for a lot of suggestions, enabling CIM, compatibility for Enterprise Security App
    * Thanks to Simon B.
    * Thanks to the [McAfee/SkyHigh Community Forum](<https://communitym.trellix.com/t5/Web-Gateway/bd-p/web-gateway>)
Copyright

This App, documentation and MWG logging ruleset are licensed under Creative Commons BY-ND 3.0

Disclaimer

    * Test anything before using in production.
    * Everything you do with this app is at your own risk.
Contact, Support and Feedback

    * E-Mail: splunkcompek.net
    * [Splunk Answers](<https://community.splunk.com/>)
Additional information mwg_xml2txt script The MWG Splunk Logging RuleSet is quite complex. Most customers modify it to
accommodate their own needs. Use this script to find all modifications when importing a new version of the RuleSet.
Usage:  
Step 1: convert XML to TXT and compare them  
perl mwg_xml2txt.pl old_ruleset.xml > old_ruleset.txt  
perl mwg_xml2txt.pl new_ruleset.xml > new_ruleset.txt  
vimdiff old_ruleset.txt new_ruleset.txt  
  
VIMDIFF will compare TXT files and highlight differences in lists and rules using color output. It can be a simple
change, like a rule being enabled/disabled, but can also be a more complex modification - in this case use a Step 2 to
do a direct XML comparison.  
Tip: press **zR** inside of vimdiff to unfold all sections. Step 2: Identify differences and optionally extract the
corresponding XML section for comparison  
export a single rule from xml ruleset (replace RuleName with an actual Rule Name that you want to extract)  
perl -0777 -e '$a=<>; ($rule)=$a=~m/(\Q**RuleName** \E.*?<\/rule>)/ms; print "$rule"' ruleset_old.xml > rule_old.txt  
perl -0777 -e '$a=<>; ($rule)=$a=~m/(\Q**RuleName** \E.*?<\/rule>)/ms; print "$rule"' ruleset_new.xml > rule_new.txt  
vimdiff rule_old.xml rule_new.xml  
After Step 1 you'll see similar output (see below). The [true] or [false] indicates if the rule is enabled or disabled.
The short 6-char string after each line are first 6 chars of the md5 for the entire rule block, so even a small
modification will be highlighted.

    
    Rules.CurrentRule.Name (short if exists in Rule Map) [true] 250e76
    Rules.CurrentRule.Name (if doesnt exist in Rule Map) [true] a1b8cf
    ------------------------------------------------------------------
    Rules.CurrentRule.Name (Last Rule) [false] 5a7005
    Rules.CurrentRule.Name [false] a568cc
    Number of FiredRules / EvaluatedRules (based on Last Rule presence) [false] 7b4f37
    Number of FiredRules / EvaluatedRules (based on loghandler position) [true] ebfaf3
    

|

    
    Rules.CurrentRule.Name (short if exists in Rule Map) [true] 250e76
    Rules.CurrentRule.Name (short if exists in Rule Map) [false] f3a8a4
    Rules.CurrentRule.Name (if doesnt exist in Rule Map) [false] 181bd9
    Rules.CurrentRule.Name (Last Rule) [false] 5a7005
    Rules.CurrentRule.Name [false] a568cc
    Number of FiredRules / EvaluatedRules (based on Last Rule presence) [false] 7b4f37
    Number of FiredRules / EvaluatedRules (based on loghandler position) [true] ebfaf3
      
  
---|---  
      
    
    
    #!/usr/bin/perl
    use strict;
    use warnings;
    my $version = "0.3 17.Oct.2022 by PP";
    use Digest::MD5 qw(md5_hex);
    # <list version="1.0.3.464" mwg-version="11.2.4-42436" name="Authentication UserGroups to log" id="com.scur.type.string.483"
    #    <listEntry>
    #       <entry>application/vnd.ms-excel.addin.macroEnabled.12</entry>
    #       <description>MS Office 2007 Excel addin (macro-enabled)</description>
    #    </listEntry>
    #
    #<list version="1.0" mwg-version="11.1.4-40769" name="Map" id="com.scur.type.complex.maptype.321" typeId="com.scur.type.complex.maptype" classifier="Other" systemList="false" structuralList="false" defaultRights="2">
    #        <description></description>
    #        <content>
    #          <listEntry>
    #            <complexEntry defaultRights="2">
    #              <configurationProperties>
    #                <configurationProperty key="key" type="com.scur.type.string" encrypted="false" value="test"/>
    #                <configurationProperty key="value" type="com.scur.type.string" encrypted="false" value="OK"/>
    #              </configurationProperties>
    #
    #   <ruleGroup id="4122" defaultRights="2" name="Splunk" enabled="true" cycleRequest="true" cycleResponse="true" cycleEmbeddedObject="true" cloudSynced="false">
    #      <rule id="5820" enabled="true" name="Domains not to log">
    # usage: 
    # Step 1: convert XML to TXT and compare them
    # perl mwg_xml2txt.pl old_ruleset.xml > old_ruleset.txt
    # perl mwg_xml2txt.pl new_ruleset.xml > new_ruleset.txt
    # vimdiff old_ruleset.txt new_ruleset.txt
    # 
    # VIMDIFF will compare TXT files and highlight differences in lists and rules using color output. It can be a simple enabled vs disabled, 
    # but can be also a more complex modification - in this case use a Step 2 to do a direct XML comparison.
    #
    # Step 2: identify differences and optionally extract corresponding XML section for comparison
    # export a single rule from xml ruleset:
    # perl -0777 -e '$a=<>; ($rule)=$a=~m/(\QRuleName\E.*?<\/rule>)/ms; print "$rule"' ruleset_old.xml > rule_old.txt
    # perl -0777 -e '$a=<>; ($rule)=$a=~m/(\QRuleName\E.*?<\/rule>)/ms; print "$rule"' ruleset_new.xml > rule_new.txt
    # vimdiff rule_old.xml rule_new.xml
    
    my $line=1;
    my $xml = undef;
    
    open (my$fh, '<', $ARGV[0]) or die "cannot open file: $!";
    { 
      local $/=undef;
      $xml = <$fh>;
    }
    close $fh;
    
    my @lists=$xml=~m/<list [^<]+ name="([^"]+)"/g;
    foreach my $list_name (sort @lists){
      my $list = undef;
      if($xml =~/(<list [^\n]+ name="$list_name" [^\n]+com\.scur\.type\.complex\.maptype.+?<\/list>)/ms){ # map has other structure
        $list = $1;
        #print "$list_name\n$list\n\n"; 
        my @entries = $list =~ m/ key="key"[^\n]+value="([^\n]+\n[^\n]+value="[^"]+)"/msg;
        s/([^"]+)".*\n.*"([^"]*)/$1 - $2/msg for @entries; # remove anything except key-value
        print "$list_name\n  ".(join "\n  ",sort @entries)."\n\n";
      }elsif($xml =~/(<list [^\n]+ name="$list_name".+?<\/list>)/ms){ 
        $list = $1;
        #print "$list_name\n$list\n\n"; 
        my @entries = $list =~ m/<entry>([^<]+)<\/entry>/msg;
        print "$list_name\n  ".(join "\n  ",sort @entries)."\n\n";
      }else{ 
        die "cannot find list" 
      };
    }
    
    while(<>){
      #print "$line: $_";
      $line++;
      next if /<ruleGroups\/?>/;
      my($ruleid,$string,$offset,$name,$enabled,$rule_block)=(undef,undef,undef,undef,undef,undef);
      if(/^(\s*)<ruleGroup/){
        $offset=$1;
        if(/ name="([^"]+)"/){$name=$1};
        if(/ rule="([^"]+)"/){$ruleid=$1};
        if(/ enabled="([^"]+)"/){$enabled=$1};
        if(/^(.*)$/){$string=$1};
        #print "$offset $name [$enabled]\n"
        ($rule_block) = $xml =~ /(\Q$string\E.*?<rule )/ms;
        $rule_block =~ s/(id=")\d+"/$1XXX"/msg;
        $rule_block =~ s/(propertyId=")\d+"/$1XXX"/msg;
        $rule_block =~ s/(id="com\.scur\.type\.\w+\.)\d+"/$1XXX"/msg;
        $rule_block =~ s/(id="com\.scur\.type\.complex\.\w+\.)\d+"/$1XXX"/msg;
        $rule_block =~ s/(com\.scur\.engine\.\w+\.)\d+/$1XXX/msg;
        if(not defined $rule_block){die "Rule block not defined for $string"};
        print "$offset $name [$enabled] ".substr((md5_hex($rule_block)),0,6)."\n"
    
      }elsif(/^(\s*)<rule id=/){
        $offset=$1;
        if(/ name="([^"]+)"/){$name=$1};
        if(/ rule="([^"]+)"/){$ruleid=$1};
        if(/ enabled="([^"]+)"/){$enabled=$1};
        if(/^(.*)$/){$string=$1};
        ($rule_block) = $xml =~ /(\Q$string\E.*?<\/rule>)/ms;
        $rule_block =~ s/(id=")\d+"/$1XXX"/msg;
        $rule_block =~ s/(propertyId=")\d+"/$1XXX"/msg;
        $rule_block =~ s/(id="com\.scur\.type\.\w+\.)\d+"/$1XXX"/msg;
        $rule_block =~ s/(id="com\.scur\.type\.complex\.\w+\.)\d+"/$1XXX"/msg;
        $rule_block =~ s/(com\.scur\.engine\.\w+\.)\d+/$1XXX/msg;
        if(not defined $rule_block){die "Rule block not defined for $string"};
        print "$offset $name [$enabled] ".substr((md5_hex($rule_block)),0,6)."\n"
      }    
    }
    
    
    

dump_logging_fields script Use the following script to output configured fields in the Splunk log handler. This is
useful if you migrate to a new Logging ruleset and want to compare which fields are enabled in old and new ruleset.
Example of usage: ./dump_logging.pl 2023-10-26_13-10_Splunk.xml com.scur.engine.datetimefilter.datetime.toisostring s=
ac= src= p= m= d= dp= bi= bo= dur= rt= up="" ua="" a="" c= ct="" u= ud= exe= macro= mbmismatch ctmt0 ctemt mte= mtne=""
cl= contentdisp='' ckex= skex= ccert cntx scc= ssc= sslcp= sslsp= tcn sslsm= DoH="" emb= embl= rqcompst rscompst
encrypt= file_watchlist="" mlwrp= malware="" malware_file_name="" malware_file_hash="" stream rul="" rul="" rnf= rne=
crt= bfc= btc= tunnel rqv= rsv= uploads="" pfail="" tmplt="" errid= bid= r= geo= tdns= tcon= tre= text= t=.... LOGERR1
LOGERR2 LOGERR3com.scur.engine.stringfilter.string.replaceallmatches tl=

    
    #!/usr/bin/perl
    use 5.010;
    use strict;
    use warnings;
    my $version = "0.3 26.Oct.2023 by PP";
    # This script reads a single Logging RuleSet (exported from the SWG UI) and output a line with logging fields
    # USAGE: ./dump_logging_ruleset.pl LoggingRuleset.xml
    use XML::LibXML;
    use JSON;
    use Data::Dumper;
    use utf8;
    #use open ":std", ":encoding(UTF-8)";
    binmode(STDIN, ":utf8");
    binmode(STDOUT, ":utf8");
    
    my $array_counter = -1; # -1 because it get incremented at start of the loop
    my $array_counter_list = -1;
    
    my $filename = $ARGV[0];
    my %hash = ();
    my $result = undef;
    my $logline_id = undef;
    
    my $dom = XML::LibXML->load_xml(location => $filename);
    
    # get an IP of User-Defined.logLine
    foreach my $property( $dom->findnodes('/libraryContent/userDefinedPropertys/userDefinedProperty')){
     if($property->findvalue('@name') eq "User-Defined.logLine"){
       $logline_id = $property->findvalue('@id');
     }
    }
    
    $result = walk_rules("/libraryContent/ruleGroup/rules/rule", 0, "top_rules");
    $result = walk_rulesets("/libraryContent/ruleGroup/ruleGroups/ruleGroup");
    
    sub walk_rules{
      my $path = shift;
      my $ruleset_counter = shift;
      my $level = shift;
      $array_counter_list = -1;
      foreach my $rule ($dom->findnodes($path)) {
        if( $rule->findvalue('@enabled') eq "true" ){
          $array_counter_list++;
          $hash{$level}[$ruleset_counter]{rules}[$array_counter_list]{"name"}= $rule->findvalue('@name');
    
          # print all direct assigments of logline=xxx
          foreach my $p5 ($rule->findnodes('immediateActionContainers/setActionContainer[@propertyId='.$logline_id."]")){
            my @nodes = $p5->findnodes('expressions/setExpression');
            if( scalar @nodes eq 1 ){
              print $p5->findvalue('expressions/setExpression/parameter/value/propertyInstance/@propertyId');
            }
          }
    
          # print all fields (logline=logline+field=
          foreach my $p ($rule->findnodes('immediateActionContainers/setActionContainer[@propertyId='.$logline_id."]")){
            foreach my $p2 ($p->findnodes('expressions/setExpression/parameter/value/propertyInstance[@propertyId='.$logline_id."]")){
              foreach my $p3 ( $p2->findnodes('../../../../setExpression/parameter/value/stringValue')){
                print $p3->findvalue('@value');
              }
            }
          }
        }
      }
    }
    
    sub walk_rulesets{
      my $path = shift;
      $array_counter = -1;
      foreach my $ruleGroup ($dom->findnodes($path)) {
        if( $ruleGroup->findvalue('@enabled') eq "true" ){
          $array_counter++;
          my $ruleGroup_name = $ruleGroup->findvalue('@name');
          my $ruleGroup_id    = $ruleGroup->findvalue('@id');
          $hash{rulesets}[$array_counter]{name}= $ruleGroup->findvalue('@name');
          my $nested_path = $path.'[@id="'.$ruleGroup_id.'"]/rules/rule';
          walk_rules($nested_path, $array_counter, "rulesets");
        }
      }
    }
    #print Dumper %hash;
    #use utf8;
    #my $json = encode_json(\%hash);
    #my $json = JSON->new->utf8->pretty->encode(\%hash);
    

List of SWG Counters

    
    AMJobQueueLength
    AMLoad
    AMPrivateMemory
    AMUsed
    AMUsedPhys
    ApplHighRisk
    ApplicationMemoryUsage
    ApplMediumRisk
    ApplMinimalRisk
    ApplUnverified
    AuthNTLMCacheRequests
    AuthUserCacheRequests
    BlockedByAntiMalware
    BlockedByApplControl
    BlockedByDCC
    BlockedByDLPMatch
    BlockedByMATD
    BlockedByMediaFilter
    BlockedByURLFilter
    Categories
    CertExpired
    CertNameMismatch
    CertRevoked
    CertSelfSigned
    CertUnresolvable
    CertWildCardMatch
    ClientCount
    CloseWaits
    CloudEnc.DecryptionBytesAll
    CloudEnc.DecryptionErrorsAll
    CloudEnc.DecryptionHitsAll
    CloudEnc.EncryptionBytesAll
    CloudEnc.EncryptionErrorsAll
    CloudEnc.EncryptionHitsAll
    ConnectedSockets
    ConnectionsBlocked
    ConnectionsLegitimate
    CoordLoad
    CoordPrivateMemory
    CoordUsed
    CoordUsedPhys
    CoreLoad
    CorePrivateMemory
    CoreThreads
    CoreUsed
    CoreUsedPhys
    CPUIdle
    CPUIOWait
    CPULoad
    CPULoadRaw
    CPUSystem
    CPUUser
    DCCCalled
    DCCUncategorized
    DXLEventsReceived
    DXLEventsSent
    DXLRequestErrors
    DXLRequestsSent
    DXLServiceCalls
    DXLTraffic
    eDirectoryRequestProcTime
    eDirectoryRequests
    FilesystemUsage
    FirstSentFirstReceivedClient
    FirstSentFirstReceivedServer
    FtpBytesFromServer
    FtpBytesToServer
    FtpRequests
    FtpTraffic
    GTIFileRepCloudLookupDone
    GTIRequestSentToCloud
    HandleConnectToServer
    HarddiskUsage
    Http2BytesFromClient
    Http2BytesFromServer
    Http2BytesToClient
    Http2BytesToServer
    Http2Requests
    Http2Traffic
    HttpBytesFromClient
    HttpBytesFromServer
    HttpBytesToClient
    HttpBytesToServer
    HttpConnectionsFromClientPerCustomer
    HttpRequests
    HttpsBytesFromClient
    HttpsBytesFromServer
    HttpsBytesToClient
    HttpsBytesToServer
    HttpsRequests
    HttpsTraffic
    HttpTraffic
    ICAPClientActiveConnections
    ICAPReqmodRequests
    ICAPReqmodTraffic
    ICAPRespmodRequests
    ICAPRespmodTraffic
    IfpRequests
    KerberosRequests
    LastSentFirstReceivedServer
    LastSentLastReceivedClient
    LastSentLastReceivedServer
    LDAPRequestProcTime
    LDAPRequests
    LoadPerCPU
    MalwareDetected
    MATDInfected
    MATDRequests
    MATDScanTime
    MemConsumed
    MemFree
    MemMallocChunks
    MemMallocKBytesUsed
    MemMMBlocks
    MemMMBytesUsed
    MemoryUsage
    MemUsed
    MT.Archive
    MT.Audio
    MT.Database
    MT.Document
    MT.Executable
    MT.Image
    MT.Text
    MT.Video
    NetworkBytesReceived
    NetworkBytesSent
    NTLMAgentRequestProcTime
    NTLMAgentRequests
    NTLMRequestProcTime
    NTLMRequests
    OTPSendProcTime
    OTPSendRequests
    OTPVerifyProcTime
    OTPVerifyRequests
    PrivDecryptOK
    PrivEncryptOK
    PrivKeyOpDuration
    RADIUSRequestProcTime
    RADIUSRequests
    RawTCPTraffic
    RepHighRisk
    RepMediumRisk
    RepMinimalRisk
    RepUnverified
    ReputationNeutral
    ReputationSuspicious
    ReputationTrusted
    ReputationUnverified
    ResolveHostViaDNS
    SMCached
    SOCKSHTTPRequests
    SOCKSHTTPSRequests
    SOCKSHTTPSTraffic
    SOCKSHTTPTraffic
    SOCKSUDPConnections
    SOCKSUDPTraffic
    SOCKSUnFilteredRequests
    SOCKSUnFilteredTraffic
    SOCKSv4Requests
    SOCKSv4Traffic
    SOCKSv5Requests
    SOCKSv5Traffic
    SSLIssuedCertificate
    SSLSessionClientHit
    SSLSessionClientMiss
    SSLSessionServerHit
    SSLSessionServerMiss
    SSO.AllLogins
    SSO.IncorrectTokens
    StatDBSize
    SwapFree
    SwapUsed
    TCPProxyConnections
    TimeConsumedByGTIFileRepCloudLookup
    TimeConsumedByGTIFileRepCloudLookup_0000_25
    TimeConsumedByGTIURLCloudLookup
    TimeConsumedByGTIURLCloudLookup_0000_25
    TimeConsumedByGTIURLCloudLookup_0026_50
    TimeConsumedByGTIURLCloudLookup_0051_75
    TimeConsumedByGTIURLCloudLookup_0076_100
    TimeConsumedByGTIURLCloudLookup_0101_150
    TimeConsumedByGTIURLCloudLookup_0151_200
    TimeConsumedByGTIURLCloudLookup_0201_250
    TimeConsumedByGTIURLCloudLookup_2001_2500
    TimeConsumedByGTIURLRating
    TimeConsumedByGTIURLRating_0000_25
    TimeConsumedByGTIURLRating_0026_50
    TimeConsumedByGTIURLRating_0051_75
    TimeConsumedByGTIURLRating_0076_100
    TimeConsumedByGTIURLRating_0101_150
    TimeConsumedByGTIURLRating_0151_200
    TimeConsumedByGTIURLRating_0201_250
    TimeConsumedByGTIURLRating_2001_2500
    TimeConsumedByGTIURLRatingSync
    TimeConsumedByGTIURLRatingSync_0000_25
    TimeConsumedByRuleEngine
    TimeForRegex
    TimeForTransaction
    UserDBRequests
    WebCacheDiskUsage
    WebCacheHits
    WebCacheMisses
    WebCacheObjectsCount
    WebCacheReadNotCacheable
    WorkingQueueLength
    XmppClients
    XmppRequests
    XmppTraffic
    

