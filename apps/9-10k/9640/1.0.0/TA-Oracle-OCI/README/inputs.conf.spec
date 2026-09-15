#   README/inputs.conf.spec for TA-Oracle-OCI
#
# Modular input mirroring the auth fields used by the archived
# "Splunk Addon for OCI" (Splunkbase app 5222) setup page — same field
# names, so existing client-provided credentials (Tenancy OCID, User OCID,
# Fingerprint, Private Key .pem, Passphrase, Region) drop straight in.
#
# Unlike 5222, this input is implemented fresh against the current `oci`
# Python SDK, installed at deploy time against Splunk's *actual* embedded
# Python interpreter (see bin/requirements.txt) rather than shipping
# pre-compiled Python-3.7 binaries. That mismatch was the root cause of
# 5222 breaking on Splunk 9.3+/10 — installing fresh avoids it entirely.

[oci_stream://<name>]
tenancy_ocid = <string>
* Tenancy OCID. Example: ocid1.tenancy.oc1.....

user_ocid = <string>
* User OCID of the OCI IAM local user associated with the API key.
  Example: ocid1.user.oc1....

fingerprint = <string>
* Fingerprint of the OCI IAM API key.
  Example: aa:aa:aa:aa:aa:ae:aa:aa:aa:aa:aa:aa:ac:aa:aa:aa

key_file = <string>
* Fully qualified path to the RSA private key .pem file on the Splunk
  instance running this input (heavy forwarder recommended).
  Example: /opt/splunk/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
  Do not place the key under default/ or version control.

pass_phrase = <string>
* Passphrase for the private key, if it is encrypted. Leave blank if not.
  Stored securely via Splunk's credential store, not in inputs.conf
  (see README.md — the setup page / storage/passwords endpoint handles
  this rather than a plaintext stanza value).

region = <string>
* OCI region the stream lives in. Example: us-ashburn-1

stream_ocid = <string>
* OCID of the OCI Stream to consume. Example: ocid1.stream.oc1.iad.....

stream_endpoint = <string>
* Streaming service endpoint for the stream's region.
  Example: https://cell-1.streaming.us-ashburn-1.oci.oraclecloud.com

sourcetype_override = <string>
* Optional. If set, ALL events from this stream use this sourcetype,
  skipping auto-detection. Leave blank (recommended) to auto-detect
  per-event from the record's source/type field, matching the same
  logic the HEC/push method uses - com.oraclecloud.audit -> oci:audit,
  .vcn.flowlogs -> oci:flowlogs, .cloudguard.problem ->
  oci:cloudguard:problem, .loadbalancer -> oci:loadbalancer,
  .objectstorage -> oci:objectstorage, anything else -> oci:log.

worker_processes = <integer>
* Number of partitions to consume in parallel. Default: 1

message_limit = <integer>
* Max messages fetched per poll cycle. Default: 10000

retry_interval = <integer>
* Seconds to sleep after a throttling/backoff response. Default: 90

poll_interval = <integer>
* Seconds to sleep between poll cycles when no backoff occurred.
  Default: 10
