Mothership is a Splunk App that provides a single pane of glass into large multi-instance Splunk deployments. Mothership dispatches SPL on remote Splunk instances on a scheduled interval and retrieves and stores search results locally. Field extraction is preserved, requiring no configuration other than a valid username and password for a service account on the remote machine.  An administrative interface with REST services is provided to simplify management and reporting. All remote search results are stored in RBAC controllable stores (i.e., lookups, indexes).

Minimum Splunk Enterprise Version 6.x

#### Release Notes

##### Version 1.0.0
Initial GA release of the Mothership App for Splunk
