Copyright 2024 Hurricane Labs

# Version Support #
9.2, 9.1, 9.0, 8.2, 8.1, 8.0 (Python3)

# Why an app for AppInspect? (So Meta) #
An easy way to send your Splunk Apps to AppInspect's API.

# Who is this app for? #
- Anyone who builds Splunk apps. The goal is to make the process easier as well as making sure you are always validating
your app against the newest version of AppInspect.


# How does the app work? #
- This app works with the https://api.splunk.com REST API
- Your .tar.gz or .tgz file will be uploaded into this app's local directory and then removed once it has been
sent to AppInspect for validation.
- Only the most recently generated AppInspect report is kept on disk. A copy of this is located in the
app's local/reports/ directory


# Steps to use: #
1. Login using your Splunk credentials
2. Click or drag and drop on the file drop area (must be a tar.gz/.tgz)
3. Modify settings to fit your specific needs
4. Wait for results
5. Success! Download a copy of the report in the browser.


# Release Notes #
## v 2.2.2 ##
- Change initial configuration setting in app.conf

## v 2.2.0 ##
- Security Patch: Fix directory traversal and SSRF vulnerability.

## v 2.0.0 ##
- UI completely overhauled using Splunk's UI Toolkit
- No longer need to re-authenticate if AppInspect token is still valid
- Save email and tag configurations in settings which are stored in a config file
- Removed email option

## v 1.0.5 ##
- Updated to use Python 3 for Splunk 8. Will not work with Python 2.7.

## v 1.0.4 ##
- Updated support email

## v 1.0.3 ##
- Added 'appapproval' tag

## v 1.0.2 ##
- Added Privacy and Legal section to README
- Updated contact email in README

## v 1.0.1 ##
- Information regarding the custom command `appinspectsendemail` added to README
- Additional README added to /appserver/static folder for attribution of 3rd party libraries
- Tested on Splunk 7.1

## v 1.0.0 ##
- Basic drag and drop / upload / email features / HTML report generation


# Possible Issues #
- Timeouts: If the report takes longer than 120 seconds to generate it will auto-cancel the job and inform you of the timeout.


# Privacy and Legal #
- No information is stored locally when logging in to Splunkbase through the login screen of this app.
- No additional personally identifiable information is logged or obtained in any way through Hurricane Labs.
- This app cannot be redistributed in any way outside of Splunkbase.
- This app cannot be modified or reverse engineered to alter how the app behaves or interacts with Splunk's AppInspect API.


# For support #
- Send email to splunk-app@hurricanelabs.com
- Support is not guaranteed and will be provided on a best effort basis.
