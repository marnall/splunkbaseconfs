Author: Augur Security Inc.

Dislaimer: Use as is. Neither Splunk nor the author is responsible for the use
or misuse of this app.

### App Deployment Prerequisite
- This app works better with CIM model plugin for Splunk 
- If CIM model is not installed, the macros "mac_cim_network_traffic_predictions" will require update where "cim_Network_Traffic_indexes" needs to be replaced with the index names of firewall logs.

### python version
- packaing tool kit has issue with python 3.10+
- install 3.9.5 to be compatible

### Libmagic
- one of the packaging dependency is libmagic.  Install it in MacOS with `brew install libmagic`
- install python wrapper with `pip install python-libmagic-bin`

### app inspection
- use this command to inspect any errors: `splunk-appinspect inspect --included-tags cloud --included-tags self-service ./seclytics-splunk-app`

### Packaging the app
- create python virtual environment
- install packaging toolkit: `pip install splunk-packaging-toolkit-1.0.1.tar.gz`
- run `slim package ./seclytics-splunk-app`

### beta release
- Sending the app to git branch will trigger a build in circleCI.  Successful build will result in a packaged file in s3://public-api-bulk/seclytics-splunk-app-beta/
- Merging to master release will build official package under s3://public-api-bulk/seclytics-splunk-app/ and the latest is linked in the parent bulk directory for download.

### cloud vetting
- https://dev.splunk.com/enterprise/docs/releaseapps/cloudvetting


### version change log:
- v1.7.2: removes the dependencies on Indicator plugin
- v1.7.1: update commands to Augur and optimized the fields feedback logic
