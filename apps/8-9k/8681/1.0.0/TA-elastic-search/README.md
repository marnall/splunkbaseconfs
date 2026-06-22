# Elastic Search Add-on for Splunk

OVERVIEW
--------
The Elastic Search Add-on for Splunk collects indexed data from an Elasticsearch instance and ingests it into Splunk as JSON events. It uses the official Elasticsearch Python SDK and manages per-input checkpoints to ensure only new data is fetched on each run.

* Author - Vatsal Jagani
* Creates Index - False


### What's inside the App

* No of XML Dashboards: **3**
* No of Custom Inputs: **1**


TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------
This add-on can be set up in two ways:

1. **Standalone Mode:**
   * Install the `TA-elastic-search` add-on on the single Splunk instance.

2. **Distributed Mode:**
   * Install the `TA-elastic-search` add-on on the heavy forwarder (for data collection).
   * Install the `TA-elastic-search` add-on on search heads (for field extraction via `props.conf`).
   * The add-on does not need to be installed on indexers.


INSTALLATION, DEPENDENCIES & CONFIGURATION
-------------------------------------------
1. On your Elasticsearch instance, create a dedicated read-only user for this add-on with the following privileges:
   * **Cluster privileges:** `monitor` (required for Point-in-Time API)
   * **Index privileges:** `read` and `view_index_metadata` on the indices you want to collect (e.g. `logs-*`)

2. Install the add-on from Splunkbase or by uploading the package in Splunk Web.

3. Navigate to **Apps > Elastic Search Add-on for Splunk > Configuration**.

4. Under the **Accounts** tab, click **Add** and fill in:
   * **Name** — a unique identifier for this account.
   * **Host** — hostname or IP address of the Elasticsearch instance.
   * **Port** — port number (default: 9200).
   * **Use HTTPS** — enable for secure communication (recommended).
   * **Verify SSL Certificate** — verify the server's SSL certificate (recommended). Disable only when connecting to an Elasticsearch instance with a self-signed certificate.
   * **Username** — the read-only Elasticsearch user created in step 1.
   * **Password** — password for that user (stored encrypted).

5. Navigate to the **Inputs** tab and click **Create New Input**:
   * **Name** — unique identifier for the input.
   * **Interval** — how often (in seconds) to poll Elasticsearch (10-3600s).
   * **Index** — Splunk index to store the collected events.
   * **Account** — select the account configured in step 4.
   * **Elasticsearch Index** — index name, wildcard pattern, or comma-separated list to collect from (e.g. `logs-app`, `logs-*`, `logs-app,metrics-*`).
   * **Time Field** — timestamp field used for checkpointing (default: `@timestamp`).
   * **Batch Size** — documents fetched per Elasticsearch request (default: 10000, range: 500-50000). Higher values reduce round-trips but use more memory.
   * **Start Time** *(optional)* — ISO 8601 timestamp or relative time (e.g. `now-7d`) used only on the very first run when no checkpoint exists. Defaults to `now-24h` if left empty.
   * **Advanced Filter Query** *(optional)* — Elasticsearch Query DSL JSON to further narrow results, applied on top of the time-based checkpoint filter. Example: `{"term": {"log_level": "ERROR"}}`.

6. Enable the input. Events will appear in the selected index with sourcetype `elasticsearch:json`.


ELASTICSEARCH VERSION COMPATIBILITY
------------------------------------
This add-on supports Elasticsearch **7, 8, and 9**. It uses the v8 Elasticsearch Python SDK, which sends API compatibility headers accepted by all three server versions.


DATA COLLECTION
---------------
Each input polls a configured Elasticsearch index at the specified interval. The add-on maintains a checkpoint per input so that only documents newer than the last successful fetch are retrieved. All documents are written to Splunk as individual JSON events.


TROUBLESHOOTING
---------------
Each input writes its own log file to:
```
$SPLUNK_HOME/var/log/splunk/ta_elastic_search_<input_name>.log
```

To search add-on logs directly in Splunk Web:
```
index=_internal sourcetype=ta_elastic_search:logs
```

To filter to a specific input:
```
index=_internal sourcetype=ta_elastic_search:logs source="*ta_elastic_search_<input_name>*"
```

Log level can be changed under **Configuration > Logging** without restarting Splunk.

A **Proxy** tab is visible on the Configuration page (included by the UCC framework by default) but is not used by this add-on. The Elasticsearch Python SDK does not read Splunk proxy settings, so configuring proxy values there has no effect on data collection.


UNINSTALL ADD-ON
----------------
To uninstall the add-on:
* SSH to the Splunk instance.
* Go to `$SPLUNK_HOME/etc/apps`.
* Remove the `TA-elastic-search` folder.
* Restart Splunk.


RELEASE NOTES
--------------

#### Version 1.0.0 (Apr 2026)
* Add-on is created to collect indexed data from elastic search into Splunk.
* It support Elastic Search (ES) version 7, 8 and 9.


OPEN SOURCE COMPONENTS AND LICENSES
------------------------------------
* elasticsearch (Python SDK) — Apache License 2.0
* splunktaucclib — Apache License 2.0
* solnlib — Apache License 2.0


SUPPORT
-------
* Contact - Vatsal Jagani
  * Email: vatsaljagani85@gmail.com
* License Agreement - https://cdn.splunkbase.splunk.com/static/misc/eula.html
* Copyright - Copyright Vatsal Jagani, 2026
