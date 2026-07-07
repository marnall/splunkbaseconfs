# Gytpol Splunk App

The Databl Gyptol App configures the inputs from Gyptol to be readable by Splunk. It seperates fields and maps them to the CIM Datamodel. Security Related fields will map to the Vulnerability Data Model in Enterprise Security.

It includes a collection of dashboards to read the data as it comes in. 

Owner: Simon / Owen 

## Installation

### Prepare Splunk

install this app. Then configure a data input to receive, either from SYSLOG, or direct. Select the port you wish to use for the input.

Set the sourcetype manually to 'gyptol' and set the index. If you dont use a 'gytpol' index, you need to update the macro to send to your chosen index.

![Splunk Input example](/README/images/ingest_setup.png "Splunk Input example")

### Configure Gytpol

On your Gyptol Server, go to the config file for SIEM integration.

```..\gytpol\data\Analyzer\Config\siem.json```

```..\gytpol\data\Analyzer\Validator\siem.json```

```..\gytpol\data\Analyzer\RSOPRepository\siem.json```

Edit the file with your favourite text editor, and update these fields.

| Field                   | Setting                  | Purpose                                            |
|-------------------------|--------------------------|----------------------------------------------------|
| Host                    | Set to your destinations | Your splunk receiving detination, or Syslog server |
| Port                    | Reciving port            | Receiving Port                                     |
| isSiemIntegrationEnabled| true                     | Enables forwarding of events                       |

Restart the services and it should start sending data.

## Dashbaords

![Splunk Dashboard example](/README/images/gytpol_dashboard_sample.PNG "Dashboard Example 1")

![Splunk Dashboard example](/README/images/gytpol_dashboard_sample_2.PNG "Dashboard Example 2")

![Splunk Dashboard example](/README/images/gytpol_dashboard_sample_3.PNG "Dashboard Example 3")