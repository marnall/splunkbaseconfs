
Cisco Umbrella Investigate Splunk Add-on (BETA)
--

### Version Support
Tested most recently with Splunk 6.4.2 through 7.1 in Linux and Windows environments.

### System Requirements
- Cisco Umbrella Investigate API key
- A running Splunk instance

### External dependencies in use
These are the external dependencies used to aid in this add-on's functionality.
They are packaged with the add-on, so there's no need to perform any installation,
but it is provided so you can make informed decisions about licensing, etc.

* [dateutil](https://dateutil.readthedocs.io/en/stable/)
* [splunklib](https://github.com/splunk/splunk-sdk-python/tree/master/splunklib)
* [pyinvestigate](https://github.com/opendns/pyinvestigate)
* [IPy](https://github.com/autocracy/python-ipy)

### Installation

1. Install into Splunk with your method of choice:

    - **Splunk Web:** go into the Manage Apps page and click the “Install app from
      file” option, then follow the instructions.
    - **Splunk CLI:** download the `opendns_investigate.tgz` file to your Splunk
      node of choice and install with the following command:

      ```sh
      $SPLUNK_HOME/splunk/bin/splunk install app opendns_investigate.tgz -auth <username>:<password>
      ```

   Both methods will require a restart of the Splunk node.

2. After starting the node, navigate back to the Manage Apps page, find the listing
   for the Cisco Umbrella Investigate add-on and click the “Set up” option. This will load
   the standard setup page for the add-on.

Next, we need to create a scheduled search. You will need to create a one with the
ability to get any kind of destination from log files. For instance, the field
itself may be called “dest”, or in the case of some Bluecoat logs may be called
“cs_host”.

This scheduled search should query for certain time ranges. For instance, it may
poll every hour for the data from two hours before it is run. So it may run every
5 minutes after the hour (e.g. 11:05AM) and look for data within a one hour segment,
beginning two hours before (9AM – 10AM if the current time is 11AM).

***NOTE***: Make sure permissions are set correctly so the add-on and user have
permissions to view the search report.

Make sure that the scheduled search name matches the exact name, as this is
case-sensitive.

An example saved search query would be:

```
index="bluecoat_logs" earliest=-2h latest=-1h | fields cs_host
```

This way, the `cs_host` field for requests in Bluecoat logs will be filtered in a
simple to parse way for the add-on to process.

Next, be sure to enable the scripted input for the add-on. You will need to:

1. Go to the Data Inputs settings under "Settings".
2. Under "Local inputs", click "Scripts".
3. Click to enable the add-on's scripted input:
`$SPLUNK_HOME/etc/apps/opendns_investigate/bin/investigate_input.py`  
4. Configure the schedule it will run on by clicking its link and modifying the interval value

##### Distributed System Installation

When installing on a distributed cluster, enable the add-on (scripted input) on one
of the Search heads. That node will run the add-on process.

### Configuration
You will be prompted to enter information into the setup page when you first start
the add-on. These include:

- **Saved search name**: The name of the saved search you want us to pull domain/IP
  information from.
- **Field name**: The names of the fields within the saved search which has the
  fields you wish to look up through the Investigate API. Multiple fields should be
  comma-separated.

### Where To Save Your API Key and Proxy Credentials
You will need to enter your Cisco Umbrella Investigate API key and proxy credentials (if needed) 
in data inputs. This is to ensure your credentials are stored in an encrypted format. 
Go to Settings -> Data Inputs -> Cisco Investigate Credentials. Click 'new'. You can enter any 
name you like, and enter the credentials. Click next, and your credentials will be encrypted and saved. 
If you are ever issued a new api key, you can update it here. Important: only save one set of credentials. 

### Usage ###
When the Investigate app runs, it stores the results in three different KV store
collections. They all have corresponding lookup transforms:

* `investigate_domains`: Stores information for domains and hosts.
* `investigate_ips`: Stores information for IP addresses.
* `investigate_hashes`: Stores information for ThreatGrid samples for file hashes.

To view contents of the KV store collection containing your Investigate data,
create a Splunk search that looks up the appropriate input transform, e.g.:

```
| inputlookup investigate_domains
```

From here, you can use the contents of the KV store collection to enrich event
data within Splunk.

#### `investigatefilter` search command
There is a custom search command which can filter out search results to only contain
hosts with a certain status from the Investigate API—e.g., you can filter out only
search results that have a malicious host. For example, if you have an index named
`bluecoat_logs` which stores hosts in a field named `host`, then you can run this
command in the search box to filter out indices to only include those whose `host`
field is a malicious host, according to the Investigate API:

```
index="bluecoat_logs" | investigatefilter host_field=host
```

By default, the `status` parameter is assigned an argument of -1 (i.e.,
malicious). You can, however, search for any supported status code (-1, 0, or 1).
For example, to filter out indices to only include hosts that are deemed benign,
you can run:

```
index="bluecoat_logs" | investigatefilter host_field=host status=1
```

If you wish, you can make this your saved search for the Investigate add-on so that
it only enriches data with malicious hosts.

##### Parameters
* **host_field**: The name of the field in your index that contains a host.
* **status**: The status code you wish to include in the search results. e.g., if
  `status` is -1, then search results will only contain indices whose field given
  by `host_field` contains a host whose status is -1.

#### KV Store Pruning

A script has been provided for pruning of KV Store collections used by this add-on.
The following two methods can be configured and enabled:

* **time-based**: Entries older than a user-supplied time modifier, e.g. "-7d@d" would
  delete everything older than 7 days.
* **size-based**: A limit can be set on the max number of rows in a collection.
  When run, the pruning script will delete rows in time-ascending (i.e. oldest first)
  order until the number of rows is equal to the maximum.
  
Both of these options can be set in the add-on setup page.

1. Go to the Data Inputs settings under "Settings".
2. Under "Local inputs", click "Scripts".
3. Click to enable the add-on's scripted input:
`$SPLUNK_HOME/etc/apps/opendns_investigate/bin/investigate_prune_kv.py`  
4. Configure the schedule it will run on by clicking its link and modifying the interval value

### Proxy Server

If you would like to direct traffic through a proxy server, set in the add-on setup
page. The format must be ip:port, and both are required. If the box is empty you
won't use a proxy. Proxy credentials are stored in Settings -> Data Inputs -> Cisco Investigate Credentials. 
See above for information on storing credentials. 

### Host Name and Port

If you are not running Splunk on the default hostname and port (localhost and 8089), set the 
host name and port in the setup page. This way the add on can correctly connect to Splunk.

### Additional information
Here are some examples of KV store keys that are complementary to the Investigate
API:

- `dest`: Destination of the event/request which can either be a domain or IP
- `last_queried`: The last time the Investigate API was queried for this input
- `status`: Integer value representing that status of that destination (-1, 0, 1)
- `status_label`: The text label associated with that particular status code

For more information about the remaining fields, see the
[Investigate API documentation](https://docs.umbrella.com/developer/investigate-api/).

### Support
splunk@opendns.com
