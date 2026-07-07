# BforeAI PreCrime App for Splunk

## Overview
PreCrime Intelligence, the predictive threat intelligence domain list, serves as your pre-emptive shield against tomorrow’s threats. By mapping and predicting malicious domain patterns through extensive datasets, we analyze network metadata to establish baselines and detect anomalies before they become breaches. Our advanced algorithms and machine learning models process vast amounts of data, enabling proactive threat detection and prevention. This cutting-edge technology helps organizations stay ahead of cyber threats, ensuring robust security and continuity. PreCrime Intelligence transforms raw data into actionable insights, offering unparalleled protection in the ever-evolving landscape of cybersecurity.




## Compatibility Matrix

* Unix OS
* Splunk version: 9.2.x, 9.1.x, 9.0.x
* Python version: Python3


## Installation

You can install from file  ( https://pov.bfore.ai/bforeai-precrime-splunk-app-latest )
or from the SplunkBase:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `bforeai-precrime-splunk-app-v1.x.x.spl` installation file.
4. Click on `Upload`.
5. Restart Splunk.

## Configuration

Configuring BforeAI PreCrime Splunk App:

### Proxy

Configure proxy settings:

||||
|---|---|---|
| Enable Proxy   | Optional  | To enable or disable the proxy |
| Proxy Host     | Mandatory | Host or IP of the proxy server |
| Proxy Port     | Mandatory | Port for proxy server          |
| Proxy Username | Optional  | Username of the proxy server   |
| Proxy Password | Optional  | Password of the proxy server   |

### Logging

Configure the Logging level:

1. Navigate to the `Configuration` tab.
2. Click on the `Logging` tab.
2. Select the log level click on `Save`.

### General Settings

#### Account
Go to BforeAI PreCrime > Configuration
Click Add from the top right corner. 
Add a unique Account Name, API URL, Username and Password.
Click on the Add button. 
Once The Account is added. The list of all the added Accounts is visible on the Configurations page.
		

#### Input

Users can manually create Modular Input by following below steps.
Go to BforeAI PreCrime >Inputs.
Click on create new input
And fill all parameters shown in this table.
Click on the save button.

#### API Feed
The API Feed is composed by Json information with the keys:
	Id: big integer - ID of the domain name
	Name: String - Domain name
	Created: Datetime - Date of processed analysis for this record
Score:   
 	{
    "Id": 272806910, 
    "Name": "thelawomanleaders.com", 
    "Created": "2024-07-02T00:02:10", 
    "Score": 1.0
    }

Based on the API feed score the domains are classified in 4 categories. 

    0-0.49 Safe domains
    0.5  Monitored domains
    0.51-0.79  Suspicious domains
    >= 0.8  Malicious domains



DATA MODEL CONFIGURATION
------------------------------
* Data Model Acceleration is disabled by default. Admin can enable acceleration and set the acceleration period by the following steps:
      1. On Splunk's menu bar, Click on Settings -> Data models
      2. From the list for Data models, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled.
      3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
      4. Check Accelerate check box to "Enable" data model acceleration.
      5. If acceleration is enabled, select the summary range to specify the acceleration period.
      6. To save acceleration changes click on the save button.

REBUILDING DATA MODEL
------------------------------
* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    1. On Splunk's menu bar, Click on Settings -> Data models
    2. From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the Data model for which acceleration needs to be rebuild. This will display an extra Data Model information in "Acceleration" section.
    3. From the "Acceleration" section click on "Rebuild" link.
    4. Monitor the status of the rebuild in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.


### License:
https://cdn.apps.splunk.com/static/misc/eula.html


## PreCrime Intelligence, by BforeAI

PreCrime Intelligence, the predictive threat intelligence domain list, serves as your pre-emptive shield against tomorrow’s threats. By mapping and predicting malicious domain patterns through extensive datasets, we analyze network metadata to establish baselines and detect anomalies before they become breaches. Our advanced algorithms and machine learning models process vast amounts of data, enabling proactive threat detection and prevention. This cutting-edge technology helps organizations stay ahead of cyber threats, ensuring robust security and continuity. PreCrime Intelligence transforms raw data into actionable insights, offering unparalleled protection in the ever-evolving landscape of cybersecurity.

### Use Cases:
#### Network Protection
PreCrime Intelligence enhances network protection by providing a domain blocklist data feed that includes predictive insights derived from global internet traffic analysis. This feed identifies and predicts malicious domain patterns, allowing organizations to proactively block harmful domains before they can impact network security. By integrating this data feed into their security infrastructure, organizations can preemptively protect against emerging threats and maintain a robust defense against cyberattacks.
#### Anti-phishing
PreCrime Intelligence strengthens anti-phishing measures through a domain blocklist data feed that targets domains associated with phishing activities. By analyzing global internet traffic and domain registration patterns, it identifies potential phishing domains early. Organizations can use this feed to update their security systems in real-time, blocking phishing attempts before they reach end-users. This proactive approach mitigates the risk of credential theft and financial fraud.
#### IoT Protection
PreCrime Intelligence secures IoT environments by offering a domain blocklist data feed that monitors global internet traffic for threats targeting IoT devices. By identifying malicious domains and unusual communication patterns, it helps establish protective measures against potential IoT vulnerabilities. Integrating this data feed into IoT security systems allows for early detection and blocking of harmful domains, ensuring the integrity and security of interconnected IoT devices across various applications.


## Troubleshooting
Please set the logging to Debug, check logs for explicit error messages 

## Support

* Email [support@bfore.ai](support@bfore.ai)

* When contacting to support, please indicate your BforeAI Precrime Splunk App version, Splunk version, if Enterprise or Cloud, and as many information, screenshots and logs, describing what you are attempting to perform, the expected output and the actual output.




# Binary File Declaration
bin/ta_precrime_threat_intelligence/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
bin/ta_precrime_threat_intelligence/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
