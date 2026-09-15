[quantumgenie_cbom://<name>]
*  Pulls CBOM/cryptographic discovery records from a QuantumGenie workspace into Splunk.

quantumgenie_url = <string>
* Base URL of the QuantumGenie deployment, e.g. https://app.quantumgenie.ai
* Required.

api_token = <string>
* Integration API token generated from QuantumGenie's "Integration API Tokens" page.
* Required. Stored using Splunk's secure credential storage, not in plain text in inputs.conf.

polling_interval = <integer>
* How often, in seconds, to poll the QuantumGenie API for new records.
* Default: 300 (5 minutes). Minimum recommended: 60.

interval = <integer>
* Standard Splunk modular input scheduling interval, in seconds.
* Should match polling_interval unless you have a specific reason to diverge.
