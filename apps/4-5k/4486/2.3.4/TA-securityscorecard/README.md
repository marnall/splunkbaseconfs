# SecurityScorecard Addon for Splunk

SecurityScorecard Addon for Splunk captures, indexes, and correlates real-time data in a searchable
repository from which it can generate graphs, reports, alerts, dashboards, and visualizations. The data is collected
using SecuriytScorecard REST Apis.

* Author - SecurityScorecard, Inc.
* Version - 2.3.4

## Compatibility Matrix
* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform independent
* Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment


## Building Zip or Tarball package(optional)

Follow the step below to create a zip/tar archive to be installed on splunk.

1. Remove all .pyc files. In Unix systems run the command `find . -name '*.pyc' -delete` inside TA-securityscorecard folder.
 
2. Remove all editor configurations such as `.idea`, `.vscode` etc.
   
3. Remove the `.git` directory and the `.gitignore` file if it is there.


## Installation

1. Log in to Splunk Web and navigate to Apps > Manage Apps. Click install app from file.
   ![Manage Apps](screenshots/ManageApps.png)
2. Select the file you want to install, then check on the update addon check box and click on upload button.
   ![Upload App](screenshots/UploadApp.png) 
3. Once the installation is complete, restart splunk.

## Uninstall
* To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-securityscorecard folder from apps directory -> Restart Splunk



### New input

![New input](screenshots/NewInput.png)


### Inputs

Go to the apps list and open TA-securityscorecard. 

From inputs screen, click on new input. Enter the values and click on `Add`.

![Inputs](screenshots/input1.png)
![Inputs](screenshots/input2.png)

![Inputs](screenshots/sample_input_configuration.png)


The following input configurations are available.

![Inputs](screenshots/custom_input_field.png)

### Configurations

Click on the `Configuration` tab next to `Inputs` tab. 
![Configurations](screenshots/configuration.png)

## Account
Now Api key is configured inside Account tab. User can Enter an account name and the API key.
While creating input inside Global Account user can see his account names and can select an account
from there corresponding API key will be used for pulling the data from API. 

![Account](screenshots/Api_key_configuration.png) 

## Proxy
If you want to add proxy settings, select `Proxy` option. Enter
your proxy credentials and click `Save`.

![Proxy](screenshots/Proxy.png)

## Logging
To configure logging, Select `Logging`. Select the desired log level and click on `Save`

![Logging](screenshots/Logging.png)


## Search

To see data logged by `SecurityScorecard Add-on for Splunk`, select the `Search` tab. Click on `Data Summary` and select your host. You
can also enter search parameters in search box to filter logs.

![Search](screenshots/Search.png)

![DataSummary](screenshots/DataSummary.png)

![SearchResults](screenshots/SearchResults.png)


## Running Tests

Running tests cases requires pytest and requests-mock. Use pip to install these packages.

Note: We currently support Python 3.6 or above version.

```bash
pip install pytest requests-mock
```

From `bin` directory, use pytest command to run tests.

```bash
cd bin
pytest tests/
```

## BINARY FILE DECLARATION
* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder

## Support
* Support Offered: Yes
* Support Email: support@securityscorecard.io

## Copyright
Â© 2025 SecurityScorecard
