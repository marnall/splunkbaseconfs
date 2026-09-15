# Search performance architecture

**Author:** Eric Cobbs

**Required dependency:** Splunk Enterprise Security 8.x

## Current approach

- Detection inventory panels use cross-app REST searches for correctness across Splunk Enterprise and Splunk Cloud permission models.
- Compatible aggregate panels use accelerated Risk and Incident Management data model summaries through tstats.
- Detailed risk-quality, finding-SLA, and investigation panels retain native searches because their required fields are not consistently available in every accelerated model deployment.
- No duplicate CDCC data model is shipped; the app reuses Enterprise Security and CIM acceleration.

## Next optimization tier

A supported scheduled-result or summary-index cache can replace live inventory REST searches after its permissions and retention behavior are validated for both standalone and search-head-cluster deployments.
