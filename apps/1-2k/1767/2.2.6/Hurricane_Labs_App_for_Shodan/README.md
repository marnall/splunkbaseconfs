Tested up to Splunk 9.1.2 (Not tested below 6.0)


# About this App #
Hurricane Labs App for Shodan allows you to search Shodan for relevant information about your hosts.
All lookup configuration for this app is done through a custom lookup interface on the app's Config page.


# Notice #
- Free API Keys will no longer work with this app
- The SA-Shodan app (https://splunkbase.splunk.com/app/1766/) has been bundled into this app.
SA-Shodan is now considered deprecated.


# Requirements #
- You must purchase an API key from Shodan (https://www.shodanhq.com/) before using this app.
- Make sure to provide your API key on the Setup page of this app even if you are upgrading as SA-shodan is deprecated.


# APP UPDATE WARNING #
If you happen to be upgrading from version 1.4 or earlier of this app, please read the following as older
versions of the app were using a lookup called `shodan_lookup.csv`.

If you're not sure if you're using this you
can run `| inputlookup shodan_lookup.csv` and see if you get results back. If so, do the following:

The `shodan_lookup.csv` is no longer being used. Instead, IPs are added to a KV Store called `shodan_my_subnets`.
If you are updating this app from a previous version then you will need to output anything in your
`shodan_lookup.csv` to the KV Store. Below is a step-by-step instruction on how to do this.

## Updates for v 2.2.6 ##
- Update splunklib to 2.1.0

## Updates for v 2.2.5 ##
- Update splunklib to 1.7.4
- Fixed issue causing | getshodan command to fail

## Updates for v 2.2.4 ##
- Update Shodan Python library to 1.28.0
- Update splunklib to 1.7.0
- Added notification to setup page indicating that free API keys will no longer work

## Updates for v 2.2.1 ##
- Fix for setup page not working on Splunk 8.1 and below

## Updates for v 2.2.0 ##
- XML version set to 1.1 for jQuery 3.5 support
- Overhaul of setup page to use React.js instead of Backbone.js
- Removal of unused jQuery validation library

## Updates for v 2.0.8 ##
- Bugfix for retrieving 2+ pages

## Updates for v 2.0.7 ##
- Modified to support Python 2.7 and 3.7

## Updates for v 2.0.6 ##
- Added ssl field to KV Store
- Added note to README under Modifying limits.conf on how to accommodate longer field byte lengths.

## Updates for v 2.0.5 ##
- Fixed out of range error when not using net: prefix.

## Updates for v 2.0.4 ##
- Fixed typo on configuration page

## Updates for v 2.0.3 ##
- Added `time.sleep(1)` to help with API timeout issues. Will still occur with large data-sets. (see debugging section below)
- Modified message on configuration page to make it clearer which KV store is not populating.
- Added `General Debugging` section to README
- Moved splunklib from `lib` into `bin/lib`

## Updates for v 2.0.2: ##
- Splunklib has been moved to lib directory to allow for Splunk Cloud installs
- Lingering console.logs() in JavaScript have been removed

## Updates for v 2.0.1: ##
- Minor bug fixes

## Updates for v 2.0.0: ##
- IMPORTANT: This replaces the SA-Shodan app, which was originally a separate add-on. This is now merged into this app.
If you have SA-Shodan already installed, it is recommended to remove that app.
- The configuration page has been completely redone. It now uses a KV Store collection to add/update/delete IPs.
You can enter either an IP or subnet.
- If you do not have anything in the KV Store the dashboard will now warn you instead of throwing a Python error
in the panels.
- You no longer have to wait for the scheduled Shodan search to run in order to populate the JSON file.
It will now update the file every time you make an edit on the configuration page.
- The search command has changed from `| shodan` to `| getshodan` - see below under 'Searching'.
- If you happen to be using the `| shodan` search command in any saved searches, reports, alerts, or dashboards you will
want to be sure to change that to the `| getshodan` command.


## The configuration page provides the following statuses: ##
- `It looks like data has not been added to the shodan_output KV Store yet.`
    – This means no IPs are currently set in the shodan_output KV Store. You can debug this by running the following to
    see if Shodan is returning a API timeout or other message:
    `| getshodan [|inputlookup shodan_my_subnets | stats values(ipAddress) AS ips | eval netlist=mvjoin(ips, ",")  | table netlist]`
- `Syncing data...` – The data from the KV Store is being updated.
- `Everything is up to date.`

## General Debugging ##
- If you are not receiving any results, but you have set up a list of IPs and Subnets on the Configuration page
you can run `| getshodan [|inputlookup shodan_my_subnets | stats values(ipAddress) AS ips | eval netlist=mvjoin(ips, ",")  | table netlist]`.
This will tell you if the API is returning a timeout or other error message.
- Additionally, you can try to manually chunk the request by running:
`| getshodan [| inputlookup shodan_my_subnets start=<int> max=<int> | lookup shodan_output query as ipAddress OUTPUT query as matched_query | search NOT matched_query=* | stats values(ipAddress) AS ips | eval netlist=mvjoin(ips, ",")  | table netlist] | outputlookup shodan_output append=t`
    - The above search will append results into the `shodan_output` KV store, looking for anything already added and
    removing it so its not sent to Shodan's API again.
    - IMPORTANT: This should only be done if you are trying to process hundreds or more IP addresses (or large CIDR blocks) and you keep running into a
    timeout error. The Shodan API is prone to timeouts with large data-sets, so this is a last resort option. If you run this manually and then go
    back to the configuration page to add new IPs, it will effectively empty out the KV Store again as it does not
    append new values by default.

## Modifying `limits.conf` ##
**Note:** Before modifying any configuration within your environment, be aware of any potential drawbacks.
- If you find certain fields are getting cut off, this is most likely because of settings in limits.conf, specifically under `[spath]`.
By default, the returned data is limited to 5000 bytes, you can modify this to accommodate a longer byte length:
```
[spath]
extract_all = <boolean>
* Controls whether to respect automatic field extraction when spath is
  invoked manually.
* If set to "true", all fields are extracted regardless of settings.
* If set to "false", only fields used by later search commands are extracted.
* Default: true

extraction_cutoff = <integer>
* For 'extract-all' spath extraction mode, this setting applies extraction only
  to the first <integer> number of bytes. This setting applies both the auto kv
  extraction and the spath command, when explicitly extracting fields.
* Default: 5000
```

## Searching ##
- Search commands are now entirely based on Shodan's search filters:
- For reference: https://help.shodan.io/the-basics/search-query-fundamentals
- The base command is `| getshodan`

### Some search examples: ###
`| getshodan net:127.0.0.1`
`| getshodan hostname:facebook.com`
`| getshodan org:"Starhub Mobile" city:Singapore`
`| getshodan nginx country:"DE"`

## Proxy support ##
- If you need to route requests to the Shodan API through an outbound proxy, edit the "http" and "https" options in the proxy stanza of shodan.conf. Values follow the schema http(s)://<ip|host>:<port>. HTTP basic auth is supported as well, like so: http(s)://user:pass@<ip|host>:<port>


## Support: ##
- This app is developer supported by Hurricane Labs.
- You can send any inquiries / comments / bugs to splunk-app@hurricanelabs.com
- Response should be relatively fast if emails are sent between 9am-5pm (Eastern)
