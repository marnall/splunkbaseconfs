# Torq Add-on for Splunk

The Torq Add-on for Splunk allows you to trigger Torq workflows as Splunk alert actions, or as
Splunk Enterprise Security "Adaptive Response" actions. 

## Installation

Install TA-torq on your Splunk search head(s). A restart is required after installation.

## Configuration

First, create a Splunk integration in Torq as documented [here](https://kb.torq.io/en/articles/9139999-splunk#h_8d4abe4ec4). Make sure to set an authentication header. Note the endpoint URL, header name, and secret.

Next, in Splunk, navigate to the Torq Add-on for Splunk app. Click "Add integration" and enter the
endpoint URL, header name and secret you noted from the previous step. Click save.

Now you can trigger your Splunk integration from an alert, correlation search, or ad-hoc as an adaptive response action. 

## Triggering from a Splunk alert

1. Find your alert on the "Searches, reports, and alerts" page and click Edit->Edit Alert.
2. Scroll down to "Trigger Actions", click "Add Actions", and select "Trigger Torq Workflow". 
3. Select the integration you created, and if you wish, customize the payload. 
4. Click save.

## Triggering from an Enterprise Security correlation search

1. Navigate to Configure->Content->Content Management.
2. Click your correlation search to edit it.
3. Scroll down to "Adaptive Response Actions" and click "Add New Response Action", then finally  "Trigger Torq Workflow".
4. Select the integration you created, and if you wish, customize the payload. 
5. Click save.

## Triggering ad-hoc from Enterprise Security's Incident Review page

1. Select a notable event and click the arrow in the "Actions" column.
2. Click "Run adaptive response action", click "Add New Response Action", then finally  "Trigger Torq Workflow".
4. Select the integration you created, and if you wish, customize the payload. 
5. Click run.
6. With the notable event expanded, click the refresh icon next to "Adaptive Responses".
7. If the status is "Success", you have successfully triggered your Torq workflow. If not, click "View Adaptive Response Invocations" for information that can help troubleshoot.

## Support
The Torq Add-on for Splunk is owned and supported by Torq.  Please direct enquiries to splunk@torq.io

## CHANGE LOG 
2.0.0 01 April 2026 - Add multi-region hook validation, retry with backoff 
1.0.0 15 August 2025 - Initial release

## Development Notes 
The Torq Add-on for Splunk was written by Cameron Schmidt of Hurricane Labs for Torq
