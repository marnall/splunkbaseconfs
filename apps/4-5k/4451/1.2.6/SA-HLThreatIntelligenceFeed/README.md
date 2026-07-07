# Hurricane Labs Threat Intelligence Feed

## Support
- Splunk ^8.0

## How This App Works
This app pulls down lookups from the Hurricane Labs getThreats API. Corresponding threatlist inputs then ingest
the lookup data into the appropriate threatlist.

## Purchasing an API Key
- Go here https://www.hurricanelabs.com/threat-intelligence-feed to request an API key.

## Setup Process
1. Go to 'Apps' < 'Manage Apps'

2. Find the 'Hurricane Labs Threat Intelligence Feed' app, and then click 'Launch App'

3. Once taken to the app, click on the 'Setup' link in the navigation

2. Enable the threatlist inputs. By default these are set to `disabled = true`. You can enable these one of two ways:
- Directly in `inputs.conf`
- Go to Configure < Data Enrichment < Intelligence Downloads and enable the following Intelligence Downloads:
    - `misp_IPDST`, `misp_MD5SUMs`, `misp_SHA1SUMs`, `misp_SHA256SUMs`, `misp_URL`, `misp_Domains`

(Non-Cloud Only)
3. Enable the scripted input in `inputs.conf`.
- By default the scripted input runs every hour. If it is decided to change this interval, and your environment is
clustered, then it is not recommended to use CRON scheduling for the scripted input.
- Confirm the scripted input has run by searching `index=_internal "ExecProcessor" "threatlist_handler.py"`. If it
successfully ran you will get results back. Ensure log_level is `INFO`. 
- If you see no results, you can force the scripted input to run by running `debug/refresh`.

(Cloud Only or Non-Cloud)
3. Enable the Saved Search `HLThreatIntelligence Populator` to start populating your Threat Lists as 
Scripted Inputs will be removed on Splunk Cloud. 
- It is recommended to schedule the saved search to run hourly as the default retention on the Threat Intelligence Downloads
is set to 1 hour by default. 
- Once the Saved Search has run, you can confirm it is running successfully by running the following search:
`index=_internal sourcetype=scheduler savedsearch_name="HLThreatIntelligence Populator" | table _time status`
- You can also manually run `| hlthreatintel` to make sure everything works as expected. Errors from running this
search should appear in both the messages window as well as the results output. If no results are returned then
everything should be working as expected.

## Upgrading (IMPORTANT)

### Upgrading From `1.0.6` or Earlier
- Starting in version `1.0.7` the setup process has changed slightly as the `setup.xml` file has been removed in the `default` 
folder to meet Splunk Cloud approval. See the `Setup Process` section in this README.
- This app no longer supports anything less than Splunk version 8 as it is required to set the app's Python version to 3 for 
meet AppInspect requirements.

### Upgrading From Version `1.0.3` or Earlier
If you are upgrading from `1.0.3` or earlier version you will need to either do one of 
two things as the setup page functionality has changed:
1. Re-enter the API key on the setup page.
- OR -
2. Change the stanza name in the `passwords.conf` file to be `[credential::api_key:]`. After a `debug/refresh`
the new API key should be seen. 

The reason for the above is the app up to version 1.0.3 utilized the standard Splunk setup page which made it
impossible to update an API key while also overwriting the old API key in `passwords.conf`. This update fixes
this issue, but because of this change one of the above changes needs to be made.

## Configure Threat Intelligence Downloads Retention 
By default, the retention for the Threat Intelligence Downloads provided in this app are set to -1h. If you adjust
this, consider adjusting the schedule for the scripted input `threatlist_handler.py`(non-cloud) or saved search 
`HLThreatIntelligence Populator` (cloud).

You can modify the Threat Intelligence Download settings by going to Configure < Data Enrichment < Intelligence Downloads
in Enterprise Security, and then finding the threat downloads (`misp_IPDST`, `misp_MD5SUMs`, `misp_SHA1SUMs`, 
`misp_SHA256SUMs`, `misp_URL`, `misp_Domains`).

Further information regarding Threat Intelligence Download retention is provided via the Splunk Documentation here: 
`https://docs.splunk.com/Documentation/ES/5.3.1/Admin/Changethreatintel`

The above link contains the following information:
```
Remove threat intelligence from the KV Store collections in Splunk Enterprise Security based on the date that the 
threat intelligence was added to Enterprise Security.

The default maximum age is -30d for 30 days of retention in the KV Store. To remove the data more often, use a 
smaller number such as -7d for one week of retention. To keep the data indefinitely, use a blank field. However, 
if the KV Store collection is stored indefinitely, the .csv files that result from lookup-generating searches can 
grow large enough to impact search head cluster replication performance. If you manually delete the data from the 
.csv file, the maximum age timer does not reset based on the edit date, and the data is still removed from the 
KV Store after the maximum age expires.

If the threat intelligence source is not a TAXII feed, define the maximum age of the threat intelligence. This 
field is not used for TAXII feeds.

- From the Enterprise Security menu bar, select Configure > Data Enrichment > Intelligence Downloads.
- Select an intelligence source.
- Change the Maximum age setting using a relative time specifier.
- Enable the retention search for the collection.
- From the Splunk platform menu bar, select Settings and click Searches, reports, and alerts.
- Search for "retention" using the search filter.
- Enable the retention search for the collection that hosts the threat source. All retention searches 
are disabled by default.
```
- Additionally, the Sinkhole option is set to false by default. If you wish to delete the lookups after
they have been added to the Threat Intelligence you will need to enable the Sinkhole for both the Threat Intel Input
as well as the Threat Intelligence Modular Input. 
See corresponding Splunk documentation (`Configure threat intelligence file retention`):
https://docs.splunk.com/Documentation/ES/6.1.0/Admin/Changethreatintel#Configure_threat_source_retention\

## Proxy Support
As of v. 1.0.4 you can set up a proxy specifically for these feeds. Just modify `feed_proxy.conf`

## Debugging
For detailed logging you can search `index=_internal source="*sa_hlthreatintelligencefeed.log"` which will
tell you if anything goes wrong with either the Scripted Input or Custom Command.

If you use the above search, but see the following: 
`[{'type': 'ERROR', 'text': 'Could not find object id=:api_key:', 'code': None}]` or a `403 forbidden`, and
are upgrading from version `1.0.3` or earlier, then you need to re-enter your API key. 

See the `Upgrading` section in this README for more information.

### Help, I don't see my threatlist!
Once you've configured everything, you should first check to see that your threatlist shows up on the 
"Threat Artifacts" dashboard in Enterpise Security (Security Intelligence <  Threat Intelligence < Threat Artifacts).

If you do not see your threatlist on the "Threat Artifacts" dashboard then it is possible it being omitted as the top
panel specifically (Threat Overview) appends multiple threat intel lists together (file_intel, ip_intel etc.) and
limits the output of those lookups to 10,000 results each. This does not mean your threatlist has not been added.

You can confirm everything is populating as expected by running the following searches:
`| inputlookup http_intel | stats count by threat_key`
- `http_intel` will have `misp_URLs`

`| inputlookup ip_intel | stats count by threat_key`
- `ip_intel` will have `misp_Domains`, and `misp_IPDST`

`| inputlookup file_intel | stats count by threat_key`
- `file_intel `will have `misp_MD5SUMs`, `misp_SHA1SUMs`, and `misp_SHA256SUMs`

If you still do not see results confirm that the necessary threatintel inputs are enabled in ES:
- Configure < Data Enrichment < Intelligence Downloads


## Support:
- This app is developer supported by Hurricane Labs. 
- You can send any inquiries / comments / bugs to splunk-app@hurricanelabs.com
- Response should be relatively fast if emails are sent between 9am-5pm (Eastern)

## Updates
1.2.6
- Updated this README so the app isn't archived

1.2.5
- Added 'Threat Intel' dashboard

1.2.3
- Removed legacy code for setup page to pass Splunk Cloud vetting

1.2.2
- XML on setup marked as 1.1 for jQuery 3.5 support

1.2.0
- Adds a new feed that contains indicators for new and high-profile vulnerabilities. These will be removed once the vulnerabilities are no longer brand-new as they tend to be false positive prone over time. 

1.0.9
- Request errors no longer generate GUI messages. These errors can be found in the _internal logs.

1.0.7
- Empty `<label></label>` in `default/data/ui/views/setup.xml` caused Python to throw an error. This has been fixed.
- Removed `default/setup.xml` as Splunk Cloud no longer supports it.
- Must be installed on Splunk 8 or greater

1.0.6
- Fix of potential bug in JavaScript preventing the Setup page from loading correctly

1.0.5
- Custom command `hlthreatintel` and saved search `HLThreatIntelligence Populator` added for Splunk Cloud usage.
- Updated Setup Page

1.0.4
- Added proxy support

1.0.3
- Simplified installation process. No longer uses a KVStore for managing API endpoints

1.0.2 
- Breaking change fixed, installation process updated to reflect necessary changes
