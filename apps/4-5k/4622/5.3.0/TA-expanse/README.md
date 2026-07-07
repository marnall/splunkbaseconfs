# Xpanse Addon for Splunk

Xpanse Splunk App is a splunk app which captures, indexes, and correlates real-time data in a searchable
repository from which it can generate graphs, reports, alerts, dashboards, and visualizations. The data is collected
using Expander REST Apis.


### Supported Versions

Splunk Enterprise:

* Version 8.1 or later

Python:

* Version 2.7 later or version 3.5 or later
* Note that while we support python 2 & python 3, Splunk v8.1+ only supports python3.
  TODO https://jira-dc.paloaltonetworks.com/browse/EXPANDR-6252

Expander API:

* V2 alerts
* V1 Assets (IP Ranges, Responsive Ips, Certificates, Domains)
* V1 Services

### Deprecations

## v5.1.0
* Fixes for cloud compatibility checks. This includes updating the Splunk SDK

## v5.0.17
* Resolve issues with alerts imports in 5.0.x
* Update cloud_management_status field for alerts CIM

## v5.0.16
* Resolve appinspect issues from 5.0.15
* Add service active_classifications
* Fix asset_identifiers

## v5.0.15
* Remove business_unit_hierarchies from alert processing allow_listed_alert_fields_mapping so business_units is flat list

## v5.0.14
* added a new kv store for xpansecloudassets
* added a few new alerts and services fields
* enabled retry on all 5xx status codes to be more resilient to api outages
* changed the logic of kv-store updates to write data to splunk as it comes in instead of waiting for the full api crawl to complete

## v5.0.13

Few bug fixes

## v5.0.12

Few bug fixes a few column updates

## v5.0.11

Fix a bug with alert deduplication

## v5.0.10

Fix a bug where retried alerts will fail because their ids are getting passed in as strings

## v5.0.9

Sync alerts, services, and assets simultaneously Set timeout on services and assets syncs to prevent alerts from never
syncing in Set alerts that are missing alert context fields to be retried on subsequent syncs

## v5.0.4

Bugfixes caused by checkpointing

### v5.0.2

Bugfixes caused by ipv6

### v5.0.1

Fix some None checks when processing alerts.

### v5.0.0

Swap data ingestion from ev1 to ev2 apis rename kv stores for migration

#### v4.0.0

Behavior support is deprecated from TA version 4.0.0+

#### v3.1.0

Events and exposures KV lookup are deprecated from TA version 3.1.0, and replaced with issues.

Tested on Ubuntu 16.04 and Ubuntu 18.04

## Building Zip or Tarball package

Follow the step below to create a zip/tar archive to be installed on splunk.

1. Increment the version in build.sh
2. run the build.sh script in the **root directory**. This will create a TA-Expanse.tar.gz file in the parent directory of this project


## Installation, Inputs Setup, and Usage
Instructions for installation, inputs setup, and usage can be found here [here](https://docs.google.com/document/d/1jnDnIj5NXxNqu50mN1sqRbb0dmeDZJG8f5xBDb4eclQ/edit?usp=chrome_omnibox&ouid=103980193370890528166
).

When testing release candidates, you can upload your tar.gz directly to your Splunk test instance.

## Running Tests

Running tests cases requires pytest and requests-mock. Use pip to install these packages.

Note: We currently support Python 2.7 & >=3.5.

To switch between python versions, use pyenv to set the version.
Install pyenv and install pip in both python 2 & python 3.
```bash
brew install pyenv
pyenv global 3.7.3
brew install pip
pip install pytest requests-mock

pyenv global 2.7.18
brew install pip
pip install pytest requests-mock
```

```bash
pip install splunklib splunk-sdk six solnlib
```

**Warning: Pyton 3.12 is not currently supported with splunk-sdk. This version of python causes the
following error: No module named 'splunklib.six.moves'**

From `bin` directory, use pytest command to run tests.

```bash
cd bin
pytest tests/
```

Testing using live server and kv store requires credentials. This can be
specified in `bin/testconfig.json` using the following format.

```json
{
  "token": "put-api-token-here",
  "kv_store_username": "put-splunk-username-here",
  "kv_store_password": "put-splunk-password-here",
  "kv_store_collection": "put-collection-name-here",
  "server_url": "put-server-url-here"
}
```

you can quickly spin up an enterprise server for testing with the following docker command

```shell
docker run -d -p 8000:8000 -p 8089:8089 -e "SPLUNK_START_ARGS=--accept-license" -e "SPLUNK_PASSWORD=password" splunk/splunk:latest  
```

this will create a splunk instance with all the expected ports of the app exposed and the user credentials:

username: 'admin' password": 'password'

*If running on Mac M series chip, you will likely get the following error when pulling the Splunk image: no matching
manifest for linux/arm64/v8 in the manifest list entries*

Use the following as a workaround:

- Enable "Use Rosetta for x86_64/amd64 emulation on Apple Silicon" within Docker Desktop
```shell
docker run -d --platform=linux/amd64 -p 8000:8000 -p 8089:8089 -e "SPLUNK_START_ARGS=--accept-license" -e "SPLUNK_PASSWORD=password" splunk/splunk:latest
```

## Cleaning up the KV store

Sometimes when testing you will need to clean-up the KV store so you can re-ingest data.

```bash
./splunk clean kvstore -app TA-expanse
```

## Testing

The following query in splunk (assuming you select 'main' as your alert index) can be helpful for making sure you sync
in all alerts

```shell
index="main"
| fields alert_id, _time, severity
| sort 0 alert_id
| streamstats current=f last(alert_id) as prev_alert
| eval alert_delta = alert_id - prev_alert
| table alert_id, prev_alert, alert_delta
```

When looking for kvstore data, you can use a query like the following:
```shell
|inputlookup xpanse_services_lookup
```

## LINTING

Before pushing your changes, you should lint your stuff. You can brew install flake8 and autopep8 to accomplish this then run them before pushing

the following command will check for any errors in the bin directory
```shell
flake8 bin/
```

it will spit out which files need to be formatted which you can correct with autopep8 here is an example of that

```shell
 autopep8 bin/event_type_to_cim.py --in-place
```

## Submitting
You must run validate your tar.gz against appinspect to ensure the build will pass Splunk's checks. This can be 
accomplished via CLI or Postman, see [here](https://dev.splunk.com/enterprise/docs/developapps/testvalidate/appinspect/)
for more details. We have an Expanse account that is used to upload new app versions within Splunkbase.
* Note: Make sure your venv directory is not getting included in the bundled tar. `build.sh` assumes /venv is the venv 
directory so any other name will require updating the build script. The appinspect report will come back with failures 
regarding files in your venv path (e.g check_for_binary_files_without_source_code : venv3/lib/python3.9/site-packages/setuptools/gui.exe)
<!---Protected_by_PANW_Code_Armor_2024 - eGRyfC94ZHIveHBhbnNlL2V4cGFuZGVyLWludGVncmF0aW9uLXByb2plY3RzL2V4cGFuc2Utc3BsdW5rLXRhfDUyNnxtYXN0ZXI= --->
