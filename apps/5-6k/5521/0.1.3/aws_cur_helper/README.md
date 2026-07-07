## Overview

This app provides a data pipeline for the AWS CUR source, macros for searching the events and summaries 
created, and alerts to monitor the pipeline.

## Pipeline

* We assume that there is an AWS TA billing input the ingests the CUR.
* Each CUR is summarized twice - at daily and monthly granularity. See summary_aws_cur* searches.
  * action.summary_index._name should be adjusted to match your indexes.
* The aws_cur_assemblies lookup catalogs CURs and their summaries. See lookup_aws_cur_assemblies* searches.

## Monitoring

* alert_source_aws_billing checks if eventcount in the index matches eventcount in the CUR manifest
* alert_summary_aws_billing checks if there are summaries for each CUR
* alert_summary_aws_billing_comparison checks if the sum of costs in the CUR matches the sum of costs in
  each summary
  
## Macros

* `aws_billing_index` and `aws_summary_index` should be adjusted to match your indexes.
* `get_latest_cur` will return the most recent CUR. The latest CUR is not necessarily for the current month
  * `get_latest_cur(month=YYYYMM)` will return the most recent CUR for the month specified
  * `get_latest_cur(month=YYYYMM`, filter) will return the most recent CUR for the month and aws_cur_assemblies filter specified
  * the txid field in aws_cur_assemblies is used to work around multiple ingest bug ADDON-24471. 
    (see https://docs.splunk.com/Documentation/AddOns/released/AWS/Releasenotes#Known_issues)
* `get_latest_cur_summaries(source)` will return the most recent CUR summary for the source provided.
* `get_next_cur_to_summarize()` will return the 3 most recent CURs that haven't been summarized yet

## Fields

* Default kv extraction truncates field names in the CUR, because they contain slashes.
  A transform is provided that does a better job of preserving field names, replacing slashes with underscores.
