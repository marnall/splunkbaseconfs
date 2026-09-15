Inno Streaming Add-on for AWS S3
===============================

Deploy, from the Splunk UI, an AWS Lambda into your own AWS account that streams
S3 objects into Splunk over HEC:

    S3 ObjectCreated  ->  Lambda  ->  HEC  ->  index

Deployment runs in-process against the AWS API (boto3). No AWS console, no AWS
CLI, and no outbound calls to the vendor are required. AWS credentials entered in
Splunk are stored encrypted (storage/passwords) and can be wiped automatically
after a successful deploy.

Requires a valid license key (Licensing tab). License verification is fully
offline - the add-on and the deployed Lambda never phone home.


1.0.0
-----
First general-availability release.

- Deploy the S3 -> HEC ingest Lambda from the Splunk UI via the AWS API (boto3);
  runs on Splunk Cloud (Victoria) and on-prem Enterprise / Heavy Forwarder.
- Deployed Lambda is a compiled Go binary (provided.al2023, x86_64) that streams
  and decompresses objects, batching to HEC.
- Compression auto-detected from content, never from the file name: gzip, zstd,
  bzip2, or uncompressed. Everything is decompressed as a stream, so memory does
  not grow with object size.
- Object layout auto-detected:
    * line-oriented - NDJSON, syslog, CSV, ALB / CloudFront / VPC Flow Logs and
      S3 access logs. One line is one event; JSON-object lines are indexed
      structured, other lines are indexed as-is. No line is dropped.
    * JSON envelope {"Records":[...]} - CloudTrail, AWS Config, GuardDuty - and
      bare JSON arrays. Each element becomes one event, streamed element by
      element, so a CloudTrail file with 100k records costs the memory of its
      largest single record.
- Routing table: map a key prefix to its own index and sourcetype (longest prefix
  wins), so one deployment feeds many log types. A route can post to HEC /raw
  instead of /event, which lets the sourcetypes the Splunk Add-on for AWS already
  ships do the line breaking and field extraction, and can skip a leading header
  line (VPC Flow Logs).
- The object key suffix filter is now optional - leave it empty to ingest every
  new object regardless of extension.
- AWS credentials stored encrypted; "Delete credentials after successful deploy"
  (default on) wipes them once the Lambda is created, and the Deploy tab offers a
  manual wipe at any time.
- Offline RSA license verification, node-locked to your AWS account id, with a
  configurable grace period. Enforced at deploy time and per Lambda invocation.
- Hourly license_status events (sourcetype s3_lambda_deployer:license) for your
  own expiry alerting; Deploy tab warns from 14 days out.
- Air-gapped support: corporate proxy settings for AWS API egress, and "Export
  deploy script" produces a self-contained shell script (Lambda binary embedded)
  that an operator can run from a machine with AWS access.
- Preview shows the exact AWS API calls before anything is created.

IMPORTANT - license expiry and your S3 retention window
- When the license expires (after the grace period) the deployed Lambda STOPS
  forwarding. Objects that land in S3 while the license is expired are NOT queued
  or replayed: ingestion resumes only for objects created after you renew.
- You can re-ingest older objects, but ONLY while they still exist in the bucket.
  If the license stays expired longer than your S3 retention / lifecycle period,
  AWS deletes those objects and that data CANNOT be recovered or backfilled into
  Splunk - by the vendor or by any other means.
- Align your renewal with the bucket's retention policy. The hourly
  license_status events and the Deploy-tab warning (from 14 days out) are there so
  you can alert on this before the window closes.


Fixed in this release
- Pressing Deploy again after a successful deploy returned HTTP 500 ("JSON reply
  had no payload value"). Once the post-deploy credential wipe had cleared the
  stored AWS keys, the STS-key check dereferenced a null value instead of falling
  through to the "missing required settings" message. It now reports the missing
  credentials cleanly.


Support: support@innosw.net
