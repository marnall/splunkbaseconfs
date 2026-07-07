# Neustar App For Splunk v1.0.0
* May 2021
* Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Neustar

## Overview

This is a Splunk App for integrating Neustar UltraGeoPoint IP Address data with the Splunk platform.

You can then enrich IPv4 and IPv6 addresses in your indexed events with additional fields from the UltraGeoPoint datasets.

This App does not index any data. It loads the Neustar UltraGeoPoint data into KVStore collections.A custom streaming search command is then used to lookup IP Address data from IP ranges in the KVStore collections.

## Dependencies

* Splunk 8.0+ Enterprise or Cloud
* AWS IAM User Account credentials (Access Key & Secret Key)
* AWS ARN Role and External ID provided to you by Neustar

## Enterprise Installation

* Untar the App release to your `$SPLUNK_HOME/etc/apps` directory
* Restart Splunk and Login

## Cloud Installation

* https://docs.splunk.com/Documentation/SplunkCloud/8.2.2104/User/PrivateApps

## Full Usage Documentation and Search Examples

Login to Splunk and browse to the App's landing page

## Setup

Login to Splunk as a user with `admin` capabilitys and browse to the App's setup page.

On the App's setup page you can change the default admin user name. This is the user that the S3 polling script will run under. By default it is the internal `splunk-system-user` which should suffice , but you can change this to be any user with admin role capabilitys.

Upon saving the setup page , the AWS S3 polling script will start/restart.

Non-encrypted Setup data is saved to `$SPLUNK_HOME/etc/apps/neustar_app/local/neustar.conf`

Encrypted Setup data is saved to `$SPLUNK_HOME/etc/apps/neustar_app/local/passwords.conf`

## Users

The S3 polling script performs several admin functions.So you will need to be logged in as a user with admin capabilitys in order to setup the App and execute the S3 polling script.

Once the KVStore collections are populated , then any Splunk user should be able to use the `ultrageopoint` custom search command.


## App Object Permissions

Everyone's Splunk environment and Users/Roles/Permissions setup are different.

By default this App ships with all of it's objects globally shared (in `metadata/default.meta` )

So if you need to limit access to functionality within the App , such as who can see the setup page , then you should browse to  `Apps -> Manage Apps -> Neustar App for Splunk -> View Objects` , and adjust the permissions accordingly for your specific Splunk environment.


## Polling Script

A custom scripted input will run in the background and poll AWS S3 for new/updated Neustar UltraGeoPoint datasets.

You can trigger restarting this scripted input either by :

* resaving the setup page
* browsing to the `Polling Script` menu item on the navigation bar and toggling enable/disable

The `Dataset Status` dashboard in the App shows the current status of the polling script and loaded datasets.

## Data download options

The CSV datasets on AWS S3 can be downloaded in 2 ways

* (Recommended) Downloading the full `csv.gz` file. The file will get written to the `s3_downloads` directory underneath the `neustar_app` installation parent directory.Optionally you can perform MD5 checksum verification and delete the file after processing.

* Streaming the `csv.gz` data (no file is downloaded). You'd only use this option if there are constraints prohibiting the file download option.

## KVStore Collections

Neustar UltraGeoPoint data is loaded into 2 KVStore collections

* `geopoint_csv_ipv6`
* `geopoint_csv_ipv4`

## Data Loading Performance

All data is loaded in the background. Your performance mileage may vary depending on your environment.

However , here are some guidelines based on loading full Ultrageopoint datasets in our development environment.

### IPv4 dataset
 
* total records loaded = 59,134,636
* download type = file download
* duration = 2h 29m 24s
* sample query time = sub second
* sample query =  `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint prefix="neustar" allfields=true clientip`
 
### IPv6 dataset
 
* total records loaded = 1,360,057
* download type = file download
* duration = 4m 45s
* sample query time = sub second
* sample query = `| makeresults count=1 | eval clientip="2001:0005:0002:ffff:ffff:ffff:ffff:ffff" | ultrageopoint prefix="neustar" allfields=true clientip`

The `Duration` time is calculated from the start of file downloading through to KVStore loading completion (including MD5 checksum time)

## Development Mode

If you are just developing/testing and you don't want to perform full data loads , then there is an internal setting in `neustar.conf` that you can switch on (by editing the conf file directly) to throttle data loading volumes `dev_mode = true`

## Custom Search Command

Splunk's built in `lookup` command just won't cut it.

So this App ships with a custom streaming search command `ultrageopoint`

This command performs IPv4/IPv6 range lookups on the UltraGeoPoint datasets loaded into KVStore collections

syntax = `ultrageopoint prefix=<string> allfields=<bool> <ip_address_field>`

* `prefix` : optional text to prepend to the output UltraGeoPoint fields. ie: if `prefix=foo` , field "state" becomes "foo_state".
* `allfields` : if `true` , output all UltraGeoPoint fields. If `false` just output "latitude","longitude","city","continent","country","region","state" 
* `ip_address_field` : the name of the field in your event containing an IPv4/IPv6 address

### Examples

* `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint clientip`
* `| makeresults count=1 | eval clientip="2001:0005:0002:ffff:ffff:ffff:ffff:ffff" | ultrageopoint allfields=true clientip`
* `| makeresults count=1 | eval clientip="1.0.67.57" | ultrageopoint allfields=true prefix=neustar clientip | table neustar_*`	

## Sample Data

If you don't have any indexed data with IP Addresses to work with , then you can easily generate some sample data.Here are 3 approaches.

### Generate a single record with IP address field "clientip"

* `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint clientip`

### Read in a list of IP addresses from a CSV lookup file with a "clientip" column

* `| inputlookup my_sample_ipaddress_data | ultrageopoint clientip`
* https://docs.splunk.com/Documentation/Splunk/8.1.3/Knowledge/Usefieldlookupstoaddinformationtoyourevents

### Use Splunk's Event Generator App

* https://splunkbase.splunk.com/app/1924

## Network Calls

### Outbound

HTTPs AWS S3 client (using STS Assume Role) polling for new/updated UltraGeoPoint datasets

## Permissions

By default this App is set to be Globally accessible by all users and apps.

## Additional Lookups

The following static CSV file lookups are included in this App

### countrycode_lookup

Used to resolve additional country code fields

* `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint clientip allfields=true | lookup countrycode_lookup "alpha-2" as country_code`

### orgtypes_lookup

Used to resolve NAICS/ISIC codes

* `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint clientip allfields=true | lookup orgtypes_lookup naics_code`
* `| makeresults count=1 | eval clientip="1.0.67.51" | ultrageopoint clientip allfields=true | lookup orgtypes_lookup isic_code`

## Logging and Errors

Logs get written to `$SPLUNK_HOME/var/log/splunk/neustar*.log`

* `neustar_s3.log` : AWS S3 polling script logs
* `neustar_setup.log` : Setup logs
* `neustar_search_command.log` : `ultrageopoint` custom search command logs

These log files are rotated daily (with a max backup count of 5) and then timestamped.

You can then easily search for logs in Splunk : `index=_internal source=*neustar*.log ERROR`

Also , via the App's navigation bar you have convenient access to dashboards for displaying the logs.


## Troubleshooting

* You are using Splunk 8+ and Python 3
* Look for any app errors as detailed in the "Logging and Errors" section
* Look for any errors in Splunk internal logging : `index=_internal error`
* Any firewalls blocking outgoing / incoming network calls ?
* Are your proxy settings correct if required on your network ?
* Is your AWS authentication/role setup correctly ?


## Contact

This App was developed by BaboonBones, Ltd. for Neustar
* www.baboonbones.com
* info@baboonbones.com


