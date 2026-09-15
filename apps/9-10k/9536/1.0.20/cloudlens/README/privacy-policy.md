# EventTimeline Privacy Statement

EventTimeline processes alert results and CloudTrail evidence already available to
the Splunk search head where the app is installed. The Free Edition does not
send findings, timeline evidence, credentials, or configuration data to an
external service.

EventTimeline stores normalized findings, timeline evidence, deduplication claims,
and app settings in Splunk KV Store collections. Splunk administrators control
access through Splunk roles and should apply their organization's retention,
access-control, backup, and data-governance requirements to the Splunk
deployment.
