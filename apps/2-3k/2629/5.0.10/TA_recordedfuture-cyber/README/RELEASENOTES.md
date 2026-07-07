# Version 5.0

## What's new in 5.0
* Removed the dependency on Splunk Add-on Builder.
    * Not using inputs.conf to comply with Splunk Cloud requirements.
    * Removed almost all external dependencies.
* Refactored to only use REST API calls.
* New configuration page.
* Storing Risk List metadata in kvstore instead of index.

## What has been removed in 5.0

* **Alerts** will no longer be indexed by default. Instead they are
fetched when needed from the API. The old behavior can be recreated with
a scheduled saved search if needed.

# Upgrading from previous versions

The setup needs to be run after the upgrade. The API key (previously
called token in our documentation) will not carry over from the old
configuration. The same goes for proxy, custom risk lists, custom alerting rules
and loglevel configurations.

## Files that can be removed

The following files can be removed from the 'bin' folder, since they
are not used anymore:

<pre>
ta_recordedfuture_cyber  # The whole folder
input_module_recorded_future_alerts.py
global_checkbox_param.json
recorded_future_alerts.py
recorded_future_enrichment.py
recorded_future_risk_list.py
ta_recordedfuture_cyber_declare.py
TA_recordedfuture_cyber_rh_recorded_future_alerts_metadata.py
TA_recordedfuture_cyber_rh_recorded_future_alerts.py
TA_recordedfuture_cyber_rh_recorded_future_risk_list.py
TA_recordedfuture_cyber_rh_settings.py
</pre>


## What's new in 4.0

* Support for Recorded Future Fusion.
  * With Fusion it's possible to tune risklist according to
    requirements (ex ignore certain types of threats that aren't
    applicable).
  * Any number of more targeted risklists can be added to the Splunk
    system to improve detection accuracy.
  * Proprietary risk data can be applied to enhance risklists.
* New dashboards:
  * New enrichment dashboard for **URL** where more targetted (compared to
    the existing Domain enrichment dashboard) enrichment can be made.
  * New enrichment dashboard for **Malwares**.
* New correlation dashboards:
  * New correlation dashboard for **URLs** which correlates full URLs
    rather than domains.
* New **Splunk Explorer dashboard**. This is a dashboard intended to
  assist customers to explore and discover the correct risklists,
  sourcetypes and fields for correlation scenarios.
* Support for monitoring **Recorded Future alerts** within the Splunk
  system. 
  * A new modular input can retrieve selected alerts and create events
    for the alerts.
  * A new dashboard presents the alert status.
* New **Global map** dashboard shows where IPs detected using the IP
  risklist are located.
* Extensive app documentation is available within the app.
* A number of reports have been added to facilitate monitoring and
  troubleshooting of the app.

Also see the [Changelog](/app/TA_recordedfuture-cyber/recorded_future_help_changelog) for more details.

## What has been removed in 4.0

* The **monitoring** dashboards have been removed. This goal is better
  achieved through alerts in Recorded Future. Monitoring of these
  alerts can be setup.

# Upgrading from previous versions

The setup needs to be run after the upgrade. The API key (previously
called token in our documentation) will not carry over from the old
configuration. The same goes for proxy and loglevel configurations.

## Files that can be removed

The following files can be removed from the 'bin' folder, since they
are not used anymore:

<pre>
logger.py
RFAPI.py
rf_config_handler.py
rf_entityquery.py
rf_logger.py
rf_risklist.py
Utils\api_key.py
Utils\app_env.py
Utils\__init__.py
Utils\rf_logger.py
</pre>

## Migration of macros.conf

Users who have previously been using the **```rf_hits```** macro are encouraged
to switch to the new macro rf_correlate. This macro takes two
arguments:
* field - the field name that should be correlated (similar to
  rf_hits).
* risk_list - the risklist used to correlate. By adding this parameter
  it's possible to use the macro to correlate other types of events
  or to use custom risklists.
  
There is one important difference between rf_hits and rf_correlate:
rf_correlate performs a join rather than a lookup to correlate. The
join statement only returns events that matches thus removing the need
to filter (ex ```| search Risk=*```).

### Migration example:

Using **rf_hits**:
```
index=main sourcetype="netscreen:firewall" earliest=-24h 
      | `rf_hits(dst)`
      | search Risk=*
      | sort -Risk
```

Using **rf_correlate**:
```
index=main sourcetype="netscreen:firewall" earliest=-24h 
      | `rf_correlate(dst,rf_ip_risklist.csv)`
      | sort -Risk
```
 
This example searches for all events during the last 24 hours where
the _dst_ field correlates against the *rf_ip_risklist.cvs*
risklist. Finally it sorts the matches acording to the *Risk* in
descending order.

### Depreciation warning

* rf_hits is scheduled for depreciation.

## transforms.conf

If local config changes have been made these need to be revised.

* The name of the risk lists have changed. Ex:
  * ```rf_ip_threatfeed.csv``` is now called ```rf_ip_risklist.csv```
