*****************************************
*
* App: Splunk Add-on for SurfWatch Labs API
* Current Version: 2.0.0
* Last Modified: Jan 2016
* Splunk Version: 6.x
* Author: SurfWatch Labs
*
*****************************************


# Overview
The Splunk Add-on for SurfWatch Labs API provides a few basic examples for consuming data from the SurfWatch Labs API and ingesting it into Splunk.  Sample data and dashboards are provided to show various ways to leverage the CyberFacts.


# Quick Start Guide
There are two ways to work with the Splunk Add-on for SurfWatch Labs API - either you can load a small example dataset that comes with the add-on, or you can get an App ID and App Key for direct access to the SurfWatch Labs.  To acquire keys for authorization, you must either be a current SurfWatch Labs API customer, or be conducting an API trial.  For more information on getting started with a trial account please contact sales@surfwatchlabs.com or go to https://www.surfwatchlabs.com/.


## Loading Sample Datasets
If you've just installed the add-on you will see a simple application configuration page.  The page asks for you SurfWatch Labs App ID and App Key.  If you do not have these at this time, you can just click *save* to skip this step for now (you can always add the values back in either by editing local/sw_api.conf or navigating to $SPLUNK_URL/manager/splunk_ta_surfwatchlabs/apps/local/splunk_ta_surfwatchlabs/setup?action=edit).

Once you are past the application configuration page, go to *Settings > Data Inputs > Files & directories* and enable one or both of the following:
* $SPLUNK_HOME/etc/apps/splunk_ta_surfwatchlabs/sample_data/cyberfacts.csv
* $SPLUNK_HOME/etc/apps/splunk_ta_surfwatchlabs/sample_data/cyberfacts.json
This will load data into an index called *swl_sample_cyberfacts*, and it will be associated with either the *sample_cyberfact_csv* or *sample_cyberfact_json* sourcetype.


## Load Data from the SurfWatch Labs API
There are three ways to load data from the SurfWatch Labs API:  collecting (polling for) new CyberFacts, by backfilling historical CyberFacts, and by allowing realtime datafeeds.
Note that to get data from the SurfWatch Labs API, you will need a valid App ID and App Key.

### Collecting CyberFacts
The easiest way to get started is to leverage the provided *get_csv_cyberfacts.py* and  *get_json_cyberfacts.py* input scripts.  If enabled (Settings > Data Inputs > Scripts > get_[csv|json]_cyberfacts.py > Enable), these scripts will poll the SurfWatch Labs API once a day in the middle of the night (GMT).  You can always adjust when they are run through the Splunk UI (Settings > Data Inputs > Scripts > get_[csv|json]_cyberfacts.py > click) or by modifying inputs.conf.

### Backfilling & Collecting CyberFacts
If you'd like to backfill your index, that is, get all historical CyberFacts there are two provided backfill scripts - *backfill_csv_cyberfacts.py* and *backfill_json_cyberfacts.py*.  If you enable (Settings > Data Inputs > Scripts > backfill_[csv|json]_cyberfacts.py > Enable ) these scripts will begin running and starting from yesterday, get a days worth of data, sleep for a few seconds, and then get another days worth of data backwards in time.  These scripts are meant to be enabled around the same time as *get_[csv|json]_cyberfacts.py* script so that no data gaps should occur.
Note that once the script finishes gathering data you will need to disable it so that it does not get executed again.

### Collecting CyberFacts in realtime
To truly collect CyberFacts in realtime you will need to leverage the SurfWatch Labs Realtime API. This will require you to allow incoming POST requests from SurfWatch Labs into your Splunk environment to an endpoint you configure.  For more information please see https://www.surfwatchlabs.com/ or contact support@surfwatchlabs.com.


## CSV and JSON data formats
The Splunk Add-on for SurfWatch Labs API has examples for consuming CyberFacts in both CSV and JSON formats.  Conceptually we consider the CyberFact to be a nested object mapping (an object containing arrays of objects), and so JSON is a natural fit.  However, our CSV format denormalizes this (similar to a dataframe) and so you can ask all of the same questions that you can with the JSON data format.  Which to use really comes down to the kinds of questions you want to ask, and personal preference.  For most people we recommend using the CSV data format in Splunk.


## Searching CyberFacts
By default the same data scripts will populate an index called *swl_sample_cyberfacts*, and all scripts against the SurfWatch Labs API will populate an index called *swl_cyberfacts*.  Once you ingest some data you should be able to see it by searching these indexes or by using the *Search the sample CyberFacts* and *Search for CyberFacts* timeline navigation items.


## Visualizing CyberFacts
Two sample dashboards are provided to show various ways to visualize CyberFact data.  There are dashboards to show filtering the data by data feed and by Industry, as well as other ways to use the data.

## Upgrading from Splunk Add-on for SurfWatch Labs API 1.x to 2.x
The Splunk Add-on for SurfWatch Labs API 2.x uses the same index name (swl_cyberfacts) as 1.x, however in 2.x we renamed the sourcetype *cyberfact* to *cyberfact_json*, and introduced a new sourcetype *cyberfact_csv*.  The example dashboard was also renamed from *cyberfacts* to *cyberfacts_json*, and a new companion *cyberfacts_csv* was added. The input scripts were renamed, once again creating a '_json' and '_csv' pair where before only one  (that dealt with JSON) existed.  And lastly, we've added sample data and added an index *swl_sample_cyberfacts* and two sourcetypes, *sample_cyberfact_csv* and *sample_cyberfact_json* to differentiate this data from potentially production-use data.

It is recommended before upgrading that all input scripts are disabled, and if possible the *swl_cyberfact* index emptied of data.  If you don't delete the data it will be ok, however all new searches will need explicit sourcetypes (which isn't a bad practice anyways).
To delete data from the SurfWatch Labs index:
```
$SPLUNK_HOME/bin/splunk stop
$SPLUNK_HOME/bin/splunk clean eventdata -index swl_cyberfacts
$SPLUNK_HOME/bin/splunk start
```

## Misc
Note that the primary intention of this add-on is to highlight how to get data from the SurfWatch Labs API into your Splunk instance.  A variety of factors specific to your environment (Splunk license indexing rates, single vs distributed indexes, data needs, accounting for Splunk downtime, etc) may require you to tweak settings.  For questions you can always contact support@surfwatchlabs.com.


# Release Notes
**v2.1.0: Feb 2016**
  - Added _by_feed CyberFact dashboards, renamed others to _by_industry
  - Added misc CyberFact dashboard
  - Added a little more sample data
  - Fixed some searches

  **v2.0.0: Jan 2016**
    - Added calls to get CSV data (much easier to use in Splunk), renamed existing to 'JSON'
  - Added sample datasets for minor exploration w/out having an API license

**v1.0.1: Aug 2015**
  - Add SplunkBase link, fix paths on rename

**v1.0: Aug 2015**
  - Initial release
