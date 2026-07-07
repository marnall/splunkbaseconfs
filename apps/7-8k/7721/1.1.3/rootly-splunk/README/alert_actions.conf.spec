[rootly]

param.integration_url = <string>
* Rootly integration URL

param.summary = <string>
* Optional override for the alert summary sent to Rootly.
* Defaults to the Splunk Alert Name.

param.description = <string>
* Description to send to Rootly.

param.custom_fields = <string>
* Optional JSON object with additional fields to send to Rootly.
* Example: {"region": "us-east-1", "priority": "high"}
* These fields are merged into the rootly namespace of the alert payload.
