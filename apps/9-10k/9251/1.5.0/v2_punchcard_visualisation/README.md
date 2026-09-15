# v2-Punchcard-visualisation

Custom Punchcard visualization for Splunk, packaged as app ID `v2_punchcard_visualisation`.

## Sample Searches

```
index=_internal | head 100000 | stats count by date_hour sourcetype
```

```
index=_internal | head 100000 | stats count by date_minute sourcetype
```

```
index=_internal | head 100000 | stats count, avg(date_minute) by date_minute sourcetype
```
