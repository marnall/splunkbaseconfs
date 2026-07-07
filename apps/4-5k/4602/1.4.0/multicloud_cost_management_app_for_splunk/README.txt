
MultiCloud Cost Management v1.4.0
This multicloud billing app is designed to give insights into your spending with cloud services. It allows you to see which services are costing money unnecessarily across AWS, Azure and Google Cloud environments.

It is important to note that this app will work for ANY combination of the previously mentioned Cloud Environments set up. ALL of them are optional. If you do not have all of these Cloud environments, only follow the instructions for the specific cloud environment(s) that you have.
------------------------------------------------
Prerequisites

If your Splunk environment is on-premise (not Splunk Cloud) you'll need to ensure that the SPLUNK_HOME variable is set. This should be set to the top directory of your Splunk installation (e.g. /opt/splunk)

You must also have the required data onboarded. The data source requirements are listed below.
------------------------------------------------
Data Source Requirements
Amazon Web Services
For AWS the Multicloud App requires that the Splunk Add-on for Amazon Web Services (AWS) is installed and configured. The following data sources are required.

VM Asset Data: AWS Description input with the 'aws:description' sourcetype. The specific API required is 'ec2_instances'.
Volume Asset Data: AWS Description input with the 'aws:description' sourcetype. The specific API required is 'ec2_volumes'.
IP Asset Data: AWS Description input with the 'aws:description' sourcetype. The specific API required is 'ec2_addresses'.
VM CPU Utilization Metrics: Cloudwatch input with the 'aws:cloudwatch' or 'aws:cloudwatch:metric' sourcetype. The specific Metric Namespace required is 'AWS/EC2'.
Billing Data: Billing (Legacy) input with the 'aws:billing' sourcetype.
Information on how to configure these data sources can be found on the documentation site for the Splunk Add-on for Amazon Web Services (AWS) here

Microsoft Azure
For Azure the Multicloud App requires that the Splunk Add-on for Microsoft Azure and Splunk Add-on for Microsoft Cloud Services are installed and configured. The following data sources are required.

VM Asset Data: Azure Resource input from the Splunk Add-on for Microsoft Cloud Services. The resource type required is 'Virtual Machine'.
Volume Asset Data: Azure Compute input from the Splunk Add-on for Microsoft Azure. The option required is 'Collect Managed Disk Data' with a sourcetype of 'azure:compute:disk'.
IP Asset Data: Azure Virtual Network input from the Splunk Add-on for Microsoft Azure. The option required is 'Collect Public IP Address Data' with a sourcetype of 'azure:vnet:ip:public'.
VM CPU Utilization Metrics: Azure Storage Table input from the Splunk Add-on for Microsoft Cloud Services. This requires a storage table setup within Azure to store VM metrics. Follow the instructions within the addon to achieve this.
Billing Data: Azure Billing and Consumption input from the Splunk Add-on for Microsoft Azure. This requires a sourcetype of 'azure:billing'.
Information on how to configure these data sources can be found on the documentation sites for the Splunk Add-on for Microsoft Azure and Splunk Add-on for Microsoft Cloud Services.

Google Cloud Platform
For GCP the Multicloud App requires that the Splunk Add-on for Google Cloud Platform is installed and configured. The following data sources are required.

VM Asset Data: Resource Metadata input required with a sourcetype of 'google:gcp:resource:metadata'. The specific API required is 'Instances'.
Volume Asset Data: Resource Metadata input required with a sourcetype of 'google:gcp:resource:metadata'. The specific API required is 'Disks'.
IP Asset Data: Unfortunately, IP Asset data is not easily supported through GCP and therefore is not used within this app.
VM CPU Utilization Metrics: Cloud Monitoring input with the specific Cloud Monitor Metric of 'compute.googleapis.com/instance/cpu/utilization'
Billing Data: Google Cloud BigQuery Billing input.
Information on how to configure these data sources can be found on the documentation site for the Splunk Add-on for Google Cloud Platform.

------------------------------------------------
Installation Instructions
Download the app from Splunkbase.

Either unpack the app in $SPLUNK_HOME/etc/app or install the app from file using the App Manager Page.

First, go to the Inputs of this app, and input the appropriate information to onboard Azure, Google Cloud or AWS prices. To use the GCP pricing inputs you must enable Cloud Billing API within your project.

Configure the macro `aws_index` to search the index/indexes where your AWS data is stored.

Configure the macro `azure_index` to search the index/indexes where your Azure data is stored.

Configure the macro `gcp_index` to search the index/indexes where your Google Cloud data is stored.

This can be found in Settings -> Advanced Search -> Macros

------------------------------------------------
Overview
Multicloud Cost Management for Splunk App is designed to give insights into your spending with cloud services. It allows you to see which services are costing money unnecessarily.

This app provides a set of dashboards and saved searches to help to give insights into where savings could be found within your cloud infrastructure without reducing the performance.

This app retrieves up to date costing from AWS, Azure and Google using API calls to give accurate cost saving estimates based on recommendations regarding changes to your Cloud Infrastructure.

GBP and USD conversion is supported across all cost estimations and summations. Conversion rates are onboarded hourly by default. Default values are also configurable. Fuctionality is also set to change the conversion rate on the fly.

General Spending Overview
This Dashboard displays an overview of your spending historically.

Clicking on a particular month on the column chart displays the breakdown of costs within that month.

VM Instances
On this page, we can see VMs that are being unutilised and what configurations on these instances are costing capital.

The Estimated cost of Stopped Instances per Month is calculated a predictor that takes all instances currently in the stopped state and extrapolates the cost of their downtime for the entire month.

On the Unused Instances panel, we can see instances that have not been utilised for a specified consectutive number of days and the cost of that accumulated downtime

VM Utilization
Here we can investigate which instances show low utilization. We look here specifically at low CPU usage of instances. We can filter to see where the max CPU and average CPU are less than a specific value.

We can then drilldown on a specific instance to see the cpu utilization over a customizable time range.

Volumes
Volumes that are unattached to instances still apply a cost to your accounts.

These panels show the extent of the volumes that are unused and the extent of the cost during the time in which they have been unused.

The Estimated Cost Per Month panel represents an estimated cost for all unused volumes extrapolated across the entire month.

IP Addresses
The IP Addresses dashboard displays information regarding both unused and unattached ip addresses.

Cloud services charge for the reservation of ip addresses when they are not in use.

This dashboard shows the accumulated cost of unassociated ip addresses, an estimate for the ip addresses that are not in use, and also the location of the unassociated ip addresses split by account.

If the duration of a IP address shows "Unknown", it is likely that the IP address has never been associated.


------------------------------------------------

Contact Information
For any enquiries or requests for more customised billing, alerting and prediction please contact: apto_support@aptosolutions.co.uk