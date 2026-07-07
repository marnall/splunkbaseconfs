# Introduction

The ET Splunk Technical Add-On (ET-TA) allows ET customers with Splunk
implementations to greatly enhance their ability to enrich and search any log
with ET Intelligence data. The ET-TA provides three primary functions:

* Automatically Downloads, Installs, and Updates the ET Intelligence reputation list into Splunk. 
* Provides several Splunk Macros which allow organizations to build their own complex queries using not just ET, but virtually any data, including with other Splunk features and TAs. 
* Enables integration with the Splunk Adaptive Response framework and dynamically uses the ET Intelligence API to enrich Notable Events with rich context from Proofpoint ET Intelligence. 

## Prerequisites

The app requires the [Splunk Common Information Model App](https://splunkbase.splunk.com/app/1621/) to be installed.

Configuring this app requires that you have two secrets on hand for the for Emerging Threats:

- API Key
- Authorization Code


## Installing the ET Splunk TA 

This app needs to be installed on the search tier of the Splunk deployment. Please refer to the [Splunk Documentation](https://docs.splunk.com/Documentation/AddOns/released/Overview/Wheretoinstall) for additional information.

The Splunk TA can be installed in under from Splunk Web UI. You can
easily install the application from the [Splunkbase](https://splunkbase.splunk.com/app/2915). Please follow the
procedure below:

1.  Log into your Splunk instance at `https://<SplunkIP>:8000`
2.  Click the Apps button 
3.  Click “Browse for Apps” 
4.  Enter “Proofpoint” into the browser bar and you should see Proofpoint – ET Splunk TA. 
5.  If this is the first time you have installed the ET-TA, then you will be given the “Install” button. If you have already installed the ET-TA then you will be given the “Update” button. Click the Install/Update button to install the current TA version. 
8.  Once again, click the (*) Managed Apps button 
9.  You should now see the ET Splunk TA in the table.  
10. Click “Launch App” in in the row for ET Splunk TA

### Configuration

- Navigate to the **Configuration** page of the TA
- Under Add-on Settings, enter API Key and Authorization Code. If you have only one of the Authorization Code or API key, please enter it in their respective field. Please note that not all functionality is available unless both are entered. For the reputation data, the Authorization Code is required. For the adaptive response capability, the API Key is required.
- Press Save
- Navigate to the **Inputs** page of the TA
- Enable the `update_repdata` input to periodically download reputation lists

### Validate Configuration

To verify, the reputation lists have been downloaded, run the following SPL 1 minute after enabling the input:
```
| inputlookup et_domain_repdata
```
```
| inputlookup et_ip_repdata
```

In case you're not seeing these lookups populated after a couple of minutes, please review 
`$SPLUNK_HOME/var/log/splunk/ta_etintel_update_repdata.log` for any log entries.

```
index=_internal  source="*ta_etintel_update_repdata.log"
```

## Usage
This section describes some ad-hoc SPL you can use to work with the TA.

### ET Splunk TA Macros 

Once the ET-TA is installed, you can immediately begin to leverage the power
of the ET-TA. The macros provided will allow you to enrich your logs with ET
data at search time, which improves performance and is not reliant on when the
logs are received. Additionally, the macros allow you to specify which fields
to search for matches, so effectively any field in any log that Splunk can
parse can be used to create queries.

### Reputation Lists

There are two types of Macros provided by the ET-TA.

**IP Lookup Macro:** `et_ip_lookup(IP=<IPfieldname>)`

This macro takes a single argument which is the IP field name and uses it to
search against the ET Intelligence reputation list. If a match is found, that
log will be enriched with the ET data for that entry. Typically this will be a
field from a Firewall, IPS, Proxy or other log that contains an IPv4 Address.
For instance, if your firewall has a field called `srcip=192.168.1.1` for
Source Address, the macro would be `et_ip_lookup(IP=srcip)`. Again this is
only for the field name.

```
|makeresults n=1 
| eval dest_ip = "88.80.3.5"
|`et_ip_lookup(dest_ip)`
```

**DNSLookupMacro:** `et_domain_lookup(DOMAIN=<DNSFieldName>)`

The DNS macro takes a single argument which is a field in a log containing a
DNS FQDN and searches against the ET Intelligence reputation list to see if
there is a match. If there is a match found, the log will be enriched with the
ET data for that entry.  For instance, if you have a log that has a DNS
request field “dns-request=time.nist.gov” then the macro would be
“et_domain_lookup(DOMAIN=dns-request).

```
|makeresults n=1 
| eval dest_domain = "malicious.domain"
|`et_domain_lookup(dest_domain)`
```


### Enriching data

With the TA installed and an understanding of the Macro syntax, it’s time for
us to start using it live. Typically you would follow the following format for
running the macros:

    select_data | `et_macro()` | additional_filtering  | optional_queries_or_macros

Where `<select_data>` is an optional Splunk query string, but is used to
define what data you would like to pass to the ET macro, since you typically
want to narrow down your selection in some way (such as by log source or
matching some logs ahead of passing it to the macro.) Next we pipe the logs to
the Macro.

The Macro is simply finding matches of the IP or Domain field which you pass
to it vs. the ET data set, and if there is a match on that log we will enrich
it with the additional information we know about that object.

After the macro runs, you may define additional match critiera. Most often,
this would be some sort of filter based upon the enriched data. The
information that is outputted from that point is then passed to any additional
queries or macros that might run and ultimately to the Splunk Search window.

**Note**: While the `<select data>` field is optional it is highly recommended for
two reasons. First, it allows you to ensure that only logs of a certain
datatype are sent to the ET-TA macro. This is important because the TA cannot
enrich logs which don’t have a matching field. No error will occur, but they
won’t be enriched. Second, the search time in Splunk is proportional to the
number of logs that are passed to it, so by filtering out unnecessary logs, we
can improve the search time performance.

#### Selecting Predefined Fields 

The ET-TA enriches each entry with the several fields. By default these fields
will be enriched in the logs, but will not display, so you will need to select
which fields you want to display in the UI if you want them to appear. Also
please see the Appendix for the list of categories.

**IP Address Objects:**

* Category: This is the category that the ET Research Team has determined the IP has exhibited. 
* Score: This is a score from 0-127 (worst rep) which is the same as what is used in Suricata. The score is a magnitude, but also decays back to 0 if additional events do not occur. 
* First Seen: This is the date that the object was first seen as creating interesting activity in the global ET sensornet for that given category. 
* Last Seen: This is the date that the object was last seen to be exhibiting interesting activity for that given category. 
* Ports: This field is the list of any TCP/UDP ports that we saw the activity on. 
* Threat Level: This is defined per category. See appendix. 

**DNS Objects**

* Category: This is the category that the ET Research Team has determined the domain has exhibited. 
* Score: This is a score from 0-127 (worst rep) which is the same as what is used in Suricata. The score is a magnitude, but also decays back to 0 if additional events do not occur. 
* First Seen: This is the date that the object was first seen as creating interesting activity in the global ET sensornet for that given category. 
* Last Seen: This is the date that the object was last seen to be exhibiting interesting activity for that given category. 
* Ports: This field is the list of any TCP/UDP ports that we saw the activity on. 
* Threat Level: This is defined per category. See appendix. 

### Adaptive Response Support 

Proofpoint ET Intelligence support for Splunk Adaptive Response further
enhances the capabilities of the ET Technical Add-On by not only identifying
interesting activity, but also allowing to take action on it.  Splunk Adaptive
Response actions typically allow the user to gather information or take other
action in response to the results of a correlation search or the details of a
notable event. Proofpoint ET Intelligence Adaptive Response support falls in
the information gathering category where the Technical Add-On acts to get rich
Threat Intelligence data on actions specified by the user.

#### AR support via Correlation Search

This section describes how to leverage Proofpoint ET Adaptive Response actions via Splunk Correlation Search. Below are the typical steps to create a Correlation Search:

Part 1: Plan the use case for the correlation search.
Part 2: Create a new correlation search.
Part 3: Create the correlation search in guided mode.
Part 4: Schedule the correlation search.
Part 5: Choose available adaptive response actions for the correlation search.

Because Proofpoint ET’s AR action is to collect Threat Intelligence tied to
the object, the recommended objects are source or destination IP Addresses. In
this e.g. the field name is `dest_ip`.

#### AR support via Notable Events

Adaptive Response actions can also be taken manually in the Incident Review
tab on Splunk ES. The Incident Review tab displays the Notable Events that are
generated in response to Correlation Searches. The ‘Run Adaptive Response enables the selection of ‘Proofpoint Check ET’ AR action.

The Proofpoint Check ET AR further requires an object as described earlier. In
the example below, we again associate the AR action with the destination IP
Address. As mentioned earlier, the recommended objects for associating
Proofpoint Check ET actions are source or destination IP Addresses.

#### Reviewing the AR Response

The result of the AR action (triggered either via a correlation search, or
manually) is displayed under the details of each notable event. Clicking on ‘Proofpoint Check ET’ would display more details tied to this action. 

## Appendix

### Categories

|Category|
|---|
|1                       CnC                    Malware Command and Control Server|
|2                       Bot                    Known Infected Bot|
|3                       Spam                   Known Spam Source|
|4                       Drop                   Drop site for logs or stolen credentials|
|5                       SpywareCnC             Spyware Reporting Server|
|6                       OnlineGaming           Questionable Gaming Site|
|7                       DriveBySrc             Driveby Source|
|9                       ChatServer             POLICY Chat Server|
|10                      TorNode                POLICY Tor Node|
|13                      Compromised            Known compromised or Hostile|
|15                      P2P                    P2P Node|
|16                      Proxy                  Proxy Host|
|17                      IPCheck                IP Check Services|
|19                      Utility                Known Good Public Utility|
|20                      DDoSTarget             Target of a DDoS|
|21                      Scanner                Host Performing Scanning|
|23                      Brute\_Forcer          SSH or other brute forcer|
|24                      FakeAV                 Fake AV and AS Products|
|25                      DynDNS                 Domain or IP Related to a Dynamic DNS Entry or Request|
|26                      Undesirable            Undesirable but not illegal|
|27                      AbusedTLD              Abused or free TLD Related|
|28                      SelfSignedSSL          Self Signed SSL or other suspicious encryption|
|29                      Blackhole              Blackhole or Sinkhole systems|
|30                      RemoteAccessService    GoToMyPC and similar remote access services|
|31                      P2PCnC                 Distributed CnC Nodes|
|33                      Parking                Domain or SEO Parked|
|34                      VPN                    VPN Server|
|35                      EXE\_Source            Observed serving executables|
|37                      Mobile\_CnC            Known CnC for Mobile specific Family|
|38                      Mobile\_Spyware\_CnC   Spyware CnC specific to mobile devices|
|39                      Skype\_SuperNode       Observed Skype Bootstrap or Supernode|
|40                      Bitcoin\_Related       Bitcoin Mining and related|
|41                      DDoSAttacker           DDoS Source|


### Category to Threat Level Mapping 

Each category defined in the Categories appendix has an associated Threat
Level Mapping. The threat levels are provided by Emerging Threats and are
understood by Suricata and Snort. You can map the index of the category to the
associated threat level below.


|Category ID|Threat Level|
|---|----------|
|0  |Unknown   |
|1  |Malicious |
|2  |Malicious |
|3  |Malicious |
|4  |Malicious |
|5  |Suspicious|
|6  |Suspicious|
|7  |Malicious |
|8  |Other     |
|9  |Suspicious|
|10 |Suspicious|
|11 |Other     |
|12 |Other     |
|13 |Malicious |
|14 |Other     |
|15 |Suspicious|
|16 |Suspicious|
|17 |Suspicious|
|18 |Other     |
|19 |Good      |
|20 |Suspicious|
|21 |Malicious |
|22 |Malicious |
|23 |Malicious |
|24 |Malicious |
|25 |Other     |
|26 |Suspicious|
|27 |Suspicious|
|28 |Suspicious|
|29 |Malicious |
|30 |Suspicious|
|31 |Malicious |
|32 |Other     |
|33 |Suspicious|
|34 |Suspicious|
|35 |Suspicious|
|36 |Other     |
|37 |Malicious |
|38 |Suspicious|
|39 |Suspicious|
|40 |Suspicious|
|41 |Malicious |


##### binary file declaration
cli.exe
cli-32.exe
cli-64.exe
gui.exe
gui-32.exe
gui-64.exe
