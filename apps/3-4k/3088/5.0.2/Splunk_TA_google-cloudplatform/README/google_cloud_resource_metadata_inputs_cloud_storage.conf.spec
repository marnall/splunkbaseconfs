##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
## Requirements Specific to the Addon for Testing

[<name>]
google_credentials_name = GCP account used to connect to GCP
google_project = google project ID.
bucket_name = bucket name
google_apis = google resource metadata cloud storage api/interval separated by ",". For instance, buckets/80, notifications/60, objectAccessControls/60, defaultObjectAccessControls/60, bucketAccessControls/60.
index = splunk index.
sourcetype = splunk sourcetype name.
