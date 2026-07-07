##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
## Requirements Specific to the Addon for Testing

[<name>]
google_credentials_name = GCP account used to connect to GCP
google_project = google project ID.
location_name = Name of the Location
google_apis = google resource metadata kubernetes api/interval separated by ",". For instance, subnetworks/60, node_pools/60, operations/60, clusters/60.
index = splunk index.
sourcetype = splunk sourcetype name.
