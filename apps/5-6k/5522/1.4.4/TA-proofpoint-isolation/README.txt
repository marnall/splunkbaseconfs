Copyright (c) 2025 by Proofpoint, Inc.  All Rights Reserved.

Proofpoint, Proofpoint Isolation and the Proofpoint logos are trademarks or registered trademarks of Proofpoint, Inc.

Product Name: Proofpoint Isolation Add-on
Author: Proofpoint Inc
Version: 1.4.4
Date: 2025-01-19
Supported products: Proofpoint URL Isolation and Proofpoint Web Isolation
Splunk requirements: Splunk Enterprise

LIMITATIONS:

This version introduces FIPS compliance, which means downgrading to a previous version is not supported once you upgrade. Attempting to downgrade will result in a full month of isolation data being re-imported, causing duplicates in the ingested data.

The reason for this limitation is that FIPS compliance prohibits the use of MD5, which was previously used to generate a checkpoint value for tracking already imported data. As part of this release, we have replaced MD5 with the secure SHA-256 algorithm for generating checkpoint values, ensuring compatibility with FIPS requirements and improving security.

INTRODUCTION:

The reporting API provides a feed for all user request activity within the Browser/Email and URL Isolation products.

For each entry within the API, the result contains a URL with an associated classification and disposition.

The available dispositions are:

EXIT_ISOLATION    – User exited Isolation.
BLOCK             – Isolation blocked the URL.
ALLOW             – Isolation allows the URL to be displayed.
BLOCK_DOWNLOAD    - Isolation blocked a download attempt.
BLOCK_UPLOAD      - Isolation blocked an upload attempt.
BLOCK_IFRAME      - Isolation blocked the URL from being displayed inside the iFrame.
ALLOW_DOWNLOAD    - Isolation allowed a download.
ALLOW_UPLOAD      - Isolation allowed an upload.
ALLOW_IFRAME      - Isolation allowed the URL to be displayed inside the iFrame.

The available classifications are:

USER              – Action performed by a user.
MALWARE           – Classified as malware.
CONTENT_FILTERING – Classified as URL defined as should block in the content filtering configuration.
PHISH             – Classified as a phishing URL.
BLOCKED_BY_POLICY – Classified as should be blocked by the policy defined in the Mail security product (valid only in URL isolation products).
DLP               - Clocked by DLP policy.

API Endpoints:

Web Isolation URI: https://proofpointisolation.com/api/v2/reporting/usage-data
URL Isolation URI: https://urlisolation.com/api/v2/reporting/usage-data

PREREQUISITES:

1. Splunk Enterprise (tested with version 8.x on Windows and Linux Operating Systems).
2. You will need a reporting API key from https://proofpointisolation.com to use the Isolation Reporting API.

INSTALLATION:

The Proofpoint Isolation add-on can be installed from the Splunkbase App Store or using an installation package from a local system. Both methods are described below.

1. Installing the Proofpoint Isolation add-on from Splunkbase
	a. In the Splunk Web Home page, on top left corner, click on the "Manage Apps" gear icon.
	b. In the Apps page, click on the "Browse more apps" button.
	c. In the Browse More Apps page, search for "Proofpoint Isolation", which should appear at the top of the search result. Click on Install button.
	d. Upon successful installation, the add-on will be in the listing in the Apps page.

2. Installing the Proofpoint Isolation add-on from an installation file:
	a. In the Splunk Web Home page, on the top left corner, click on the "Manage Apps" gear icon.
	b. In the Apps page, click on the "Install app from file" button.
	c. To install, select the add-on package file (for example, ta-proofpoint-isolation.tar.gz).
	d. Upon successful installation, the add-on will be in the listing in the Apps page.

Add an input to collect events from Isolation Reporting API. It can be done using following steps:

1. Using Splunk web UI:
        - Go to "App: Proofpoint Isolation" -> "Inputs" tab
        - Click on “Create New Input” and select Proofpoint Web Isolation or Proofpoint URL Isolation
        - Enter the name of your input (eg. corp_url_isoation or corp_web_isolation depending on the solution)
		- Enter the polling interval (eg. 600 is the recommended default)
		- Select the index where data should be stored
		- Enter the API Key
		- Enter the desired page size (eg. 10000 is the recommended default)
		- Enter the desired chunk size (eg. 10000 is the recommended default)
		- Enter the desired Request Timeout (eg. 60 is the recommended default)
        - Once your inputs have been created successfully, click on start searching.

The interval determines how frequently your Splunk instance will poll for new events. The recommended(and default) setting is 600 seconds, or 10 minutes. Intervals below 300 seconds are not recommended.

The "Request Timeout" field is useful for large ingests. The first execution of the TA will ingest 30 days of isolation records. The larger the data set the longer the delay in the HTTP response; setting a higher value can resolve the "request timed out" issue.

THIRD PARTY COMPONENTS:

This modular input is packaged with the following third-party modules:

splunklib - http://dev.splunk.com/python


# Binary File Declaration
TA-proofpoint-isolation/lib/charset_normalizer/md.cpython-310-x86_64-linux-gnu.so: this file does not require any source code
TA-proofpoint-isolation/lib/charset_normalizer/md__mypyc.cpython-310-x86_64-linux-gnu.so: this file does not require any source code
