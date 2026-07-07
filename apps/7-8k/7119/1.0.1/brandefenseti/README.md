# Splunk - App

# Brandefense Threat Intelligence Feed

## Support

* Splunk > 7.0

## How This App Works

This app pulls down lookups from Brandefense API. Corresponding threatlist inputs then ingest the lookup data into the appropriate threatlist.

## Purchasing an Product

* Go here <https://brandefense.io/> to request Discover Platform.

## Setup Process


 1. Go to 'Apps' > 'Manage Apps' menu item in the left navigation panel.
 2. On the Apps page, you will see a list of installed apps. To install a new app from a file, click on the "Install app from file" button, usually located at the top right corner of the page
 3. In the "Upload an App" section, click on the "Choose File" or "Browse" button to locate and select the app package file from your local computer or network.
 4. Once you've selected the app package file, click the "Upload" or "Install" button to begin the installation process.
 5. Some apps may require you to restart Splunk for changes to take effect. If prompted, follow the on-screen instructions to restart Splunk.
 6. Once the app is installed, you can access it by returning to the Splunk Web Interface. Click on the "Apps" menu item, and you should see the Brandefense app among your installed apps.
 7. Click on the app's name to create input, Go to Inputs in Brandefense App
 8. Click on Create New Input and filled the form according table below

     ![](/api/attachments.redirect?id=fc21d813-a15e-447e-ab67-dd53bf06983a)

| Name | Enter a unique name for the data input |
|----|----|
| Interval | 3600 |
| Index | Brandefense |
| Server | api.brandefense.io |
| API Key | API Token |
| Initial data collection\n | Initial data collection will start with the data in the selected time period. |

    \
 9. In first run, lookup files will be created in 30 minutes. Otherwise trigger searches below after data is collected. `Brandefense - Domain Lookup Update`, `Brandefense - Hash Lookup Update`, `Brandefense - IP Lookup Update`
10. The following lookup files will be created, you can call lookup files like “|inputlookup brandefense_threat_domain“

    
    1. brandefense_threat_domain
    2. brandefense_threat_hash
    3. brandefense_threat_ip
    4. brandefense_threat_url

## Configure Threat Intelligence Downloads Retention

By default, the retention for the Threat Intelligence Downloads provided in this app are set to -1d.

You can modify the Threat Intelligence Download settings by going to Configure < Data Enrichment < Intelligence Downloads in Enterprise Security, and then finding the threat downloads (`brandefense_threat_domain`, `brandefense_threat_hash`, `brandefense_threat_ip`,`brandefense_threat_url`).

Further information regarding Threat Intelligence Download retention is provided via the Splunk Documentation here: `https://docs.splunk.com/Documentation/ES/5.3.1/Admin/Changethreatintel`

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

* Additionally, the Sinkhole option is set to false by default. If you wish to delete the lookups after they have been added to the Threat Intelligence you will need to enable the Sinkhole for both the Threat Intel Input as well as the Threat Intelligence Modular Input. See corresponding Splunk documentation (`Configure threat intelligence file retention`): [https://docs.splunk.com/Documentation/ES/6.1.0/Admin/Changethreatintel#Configure_threat_source_retention\](https://docs.splunk.com/Documentation/ES/6.1.0/Admin/Changethreatintel#Configure_threat_source_retention%5C)

## Proxy Support

you can set up a proxy specifically for these feeds. Just modify `Threats` in Inputs page.

## Debugging

For detailed logging you can search `index=_internal source="C:\Program Files\Splunk\var\log\splunk\brandefense_threats.log" ERROR` which will tell you if anything goes wrong with either the Scripted Input or Custom Command.

If you use the above search, but see the following: `Connection to threateye.bdef.io timed out`, then you need to check your connection or whitelist your IP Address.

### Help, I don't see my Threats!

Once you've configured everything, you should first check to see that your `Threats` shows up on the "Threat Artifacts" dashboard in Enterpise Security (Security Intelligence <  Threat Intelligence < Threat Artifacts).

If you do not see your `Threats` on the "Threat Artifacts" dashboard then it is possible it being omitted as the top panel specifically (Threat Overview) appends multiple threat intel lists together (file_intel, ip_intel etc.) and limits the output of those lookups to 10,000 results each. This does not mean your `Threats` has not been added.

You can confirm everything is populating as expected by running the following searches:

`| inputlookup http_intel | stats count by threat_key`

* `http_intel` will have `brandefense_threat_url`

`| inputlookup ip_intel | stats count by threat_key`

* `ip_intel` will have `brandefense_threat_domain`, and `brandefense_threat_ip`

`| inputlookup file_intel | stats count by threat_key`

* `file_intel `will have `brandefense_threat_hash`

If you still do not see results confirm that the necessary Threats inputs are enabled in ES:

* Configure < Data Enrichment < Intelligence Downloads

## Support:

* This app is developer supported by Brandefense.
* You can send any inquiries / comments / bugs to [support@brandefense.io](mailto:support@brandefense.io)
* Response should be relatively fast if emails are sent between 9am-5pm (Eastern)

1.0.0

* Relased App


