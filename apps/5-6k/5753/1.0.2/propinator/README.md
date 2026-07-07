# Propinator v1.0

## An Opinionated parsing configuration generator

### Overview

Propinator is an app from Discovered Intelligence that suggests opinionated Splunk parsing configurations for *unstructured* events. 

The app provides a unique functionality - a dashboardthat lets you select events associated with a specific index and sourcetype and generates the Great Eight `props.conf` stanza applicable at inputs and parsing phases in the forwarding and indexing tier. It also lets a user test and validate the generated attribute values by showing a preview of how it would look like after applying those generated attributes. Users also have the flexibility to edit the attribute values and then apply those edited values to the raw events to preview and test them. Once satisfied with the values, the stanza is shown in a panel exactly as how it would appear in the configuration file so you can copy it to a clipboard using the Copy to Clipboard button and manually paste it in the `props.conf` of the appropriate tier.


### Installation and Configuration

This is a Search Head only app. Standard installation procedures apply for this app on a Splunk Enterprise deployment. This app is ready for use right out of the box. However it can be enriched further by editing the lookup `propinator_data.csv` if required.

### Under the hood

The core logic is implemented by integrating a custom command `propinator` and a lookup table `propinator_data.csv`.

In case you are applying this command in an ad-hoc search query, you can generate the props by passing the required argument `mode=suggest` with the command.

See below how you can apply this in an ad-hoc query.

```SPL
index=<your_index> sourcetype=<your_sourcetype> | head 100 | table _raw | propinator mode=suggest
```

### Capability Enhancement

The lookup table `propinator_data.csv` is simply a knowledge object that holds a list of known time formats and their regexes. You can add new time formats into this lookup if required to enhance the capability of this app. Make sure to always append new rows to the lookup and not overwrite it. If you want to disable a particular row, just change the `ignore` column for that row to `1`. Also remember to enclose the new values in double quotes.

### Test Regex

Here's a handy search for testing the regexes.

```SPL
index=<your_index> | stats latest(_raw) as _raw by sourcetype | appendcols [| inputlookup propinator_data.csv | stats list(re) as re] | filldown re | eval ts_matches = mvmap(re, if(match(_raw, re), mvappend(ts_matches,re), ts_matches)  ) | fields - re | eval count=mvcount(ts_matches)
```

### Logging & Troubleshooting

Logging is integrated with Splunk under filename `propinator.log` and will be located in `$SPLUNK_HOME/var/log/splunk/`. This log file will rotate on reaching 20MB size and will have 4 backup files named as `propinator.log.1` to `propinator.log.4`. 

It can be searched within Splunk like so:

```SPL
index=_internal source="*/var/log/splunk/propinator.log"
```This log file will rotate on reaching 20MB size and will have 4 backup files named as `propinator.log.1` to `propinator.log.4`.

The `propinator` custom command can **optionally** accept `log_level=DEBUG` as an argument to enable troubleshooting.

### Limitations

Current version of the app is designed to tackle unstructured events, a future version may be developed that will also generate parsing configuration for popular structured events like XML, JSON etc. 

We have covered as much possible combinations of timestamp formats in the lookup, however it is recommended to keep the lookup updated with more timestamps as and when a new one is encountered that couldn't be parsed by the app.

### Word of Caution

Note that though the user has the option to select the no. of raw events to process, it may be prudent to NOT run this over 100s and 1000s of events to prevent the app from consuming more than required CPU and memory. For the app to stay true to purpose, it is assumed that the events that you select are homogenous in terms of event structure and format. This makes selecting a 100 rows sufficient to generate the parsing attributes. In case multiple disparate log sources may be having the same sourcetype assigned due to the absence of best practices in onboarding, the app is designed to suggest parsing configurations for the most frequent format among the selected events within that time window. On the same note, while copying the generated stanza into a `props.conf` file in the indexing tier, you need to be aware that you could be replacing/overriding any existing parsing confs for that sourcetype. And the existing stanza might already be applied correctly for certain log sources but not applicable for others, make sure to have appropriate sourcetype name for the suggested props and make changes at the `inputs.conf` as well if required.
