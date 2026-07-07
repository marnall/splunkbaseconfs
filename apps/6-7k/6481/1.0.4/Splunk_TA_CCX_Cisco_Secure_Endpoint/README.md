**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Add-on for Cisco Secure Endpoint (formally Cisco AMP) looks to provide a single field extraction bundle for Cisco Secure Endpoint Logs (AMPQ).
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Cisco Secure Endpoint ingested logs via the Cisco AMP for Endpoints API v1 event_stream using the (AMQP) protocol.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Change, Malware, Intrusion Detection (IDS), and Vulnerabilities.

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1    |
| -------------------------- | --------------------- |
| CIM                        | 6.x, 5.x              |
| Platforms                  | Platform independent  |
| Vendor Products            | Cisco Secure Endpoint |
| Service Provider           | CyberCX               |

**Requirements:**

- Log ingestion via the Cisco AMP link below:

Data can be consumed via bunny

https://api-docs.amp.cisco.com/api_actions/details?api_action=POST+%2Fv1%2Fevent_streams&api_host=api.apjc.amp.cisco.com&api_resource=EventStream&api_version=v1

ConsumeAMQP professor for Apache NiFi

https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-amqp-nar/1.8.0/org.apache.nifi.amqp.processors.ConsumeAMQP/index.html

**Installation:**

_Splunk Cloud Victoria Experience (non-ES) - ingestion via HTTP Event Collector (HEC):_

- The CCX Add-on for Cisco Secure Endpoint should be installed on the AdHoc Search Head (default sourcetype - cisco:secureendpoint).

_Splunk Cloud Victoria Experience (ES) - ingestion via HTTP Event Collector (HEC) configured on the AdHoc search head:_

- The CCX Add-on for Cisco Secure Endpoint when installed on the AdHoc it is replicated by default to the ES Search Head (default sourcetype - cisco:secureendpoint).

_Splunk Cloud Classic or Splunk Enterprise ingestion via HTTP Event Collector (HEC):_

- The CCX Add-on for Cisco Secure Endpoint should be installed on Search Heads, and Forwarder (HF) (default sourcetype - cisco:secureendpoint).

_In case logs are forwarded via UF this Add-on should be installed on the IDXs (default sourcetype - cisco:secureendpoint)._

**Known issues:**

- (none)

**New Release:**
Additional wildcard support for lookup to enhance match.
