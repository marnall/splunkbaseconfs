# Qualys PCRS App for Splunk Enterprise

This app, which works on top of TA-QualysCloudPlatform, provides analysis and reporting on Policy Compliance posture.

## Table of Contents

1. [Implementation](#implementation)
1. [Contributing](#contributing)

## Implementation
TA pulls and indexes PCRS Policy posture data, and this app leverates it to provide analysis and reporting on that.

### Dependencies
This app depends on TA-QualysCloudPlatform. Please make sure you have installed TA-QualysCloudPlatform, added pcrs_posture_info input and enabled it.

### Installation
1. Download app from Splunkbase. 
2. Login to your Splunk instance. and go to "Manage Apps".
3. Click "Install app from file", and choose this app's tarball. Upload it.

### Usage
You should see "Qualys PCRS App for Splunk Enterprise" under Apps menu. Click on that and you should be taken to default dashboard in app.

## Contributing

Open an issue first to discuss potential changes/additions.

**[Back to top](#table-of-contents)**
