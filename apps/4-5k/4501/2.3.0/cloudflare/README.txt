Cloudflare App for Splunk® by Cloudflare Inc.
==========
For support, please e-mail analytics@cloudflare.com


## Description ############################

The Cloudflare App for Splunk leverages Cloudflare logs to provide insights on performance, reliability, security and ZeroTrust
for websites and applications.

This application includes fourteen (14) dashboards powered by a custom Cloudflare Data Model. By default the
application is shipped with Data Model Acceleration turned off but can be optionally turned on for improved speeds
when loading dashboards and panels.

The application also includes 3 dashboards for ZeroTrust logs based on index searches.

The application also includes Common Information Model (CIM) compliant search-time field extractions and field
aliases. Furthermore, line breaking configurations are included in the application.

The Cloudflare App for Splunk is compatible with all Splunk Enterprise 7.x releases and supports single Search Head
deployments as well as being deployed on Search Head Clusters.

## Application Requirements ############################

1. Splunk Enterprise version 7.x
2. Cloudflare logs are expected to be in JSON format with a sourcetype of cloudflare:json
3. Cloudflare ZeroTrust logs are expected to be in JSON format with sourcetype as given in the below table.

 | Log type                        | Sourcetype         |
 | ------------------------------- | ------------------ |
 | ZeroTrust Access requests logs  | cloudflare:access  |
 | ZeroTrust Audit logs            | cloudflare:audit   |
 | ZeroTrust CASB logs             | cloudflare:casb    |
 | ZeroTrust Gateway DNS logs      | cloudflare:dns     |
 | ZeroTrust Gateway HTTP logs     | cloudflare:http    |
 | ZeroTrust Gateway Network logs  | cloudflare:network |

## Cloudflare Logs Data Onboarding Notes ############################

1. For documentation on the available methods for collecting Cloudflare logs please refer to the Cloudflare Log
Docs website here: https://developers.cloudflare.com/logs/about/

2. For ease of onboarding and integration, it is recommended to use Cloudflare’s Logpush Service to push logs
to Amazon S3 which can then be pulled into Splunk using the Splunk Add-on for AWS. Instructions on how
to install the Splunk Add-on for AWS and configure inputs can be found here: https://docs.splunk.com/Documentation/AddOns/latest/AWS/Description
– this link also contains details on where to install the Splunk Add-on for AWS as it is dependent on the type of deployment you have.

3. Please note that if you are performing the data onboarding from a separate instance of Splunk and not
where the Cloudflare App for Splunk is located it is strongly advised to copy the proper section of the
props.conf packaged with the Cloudflare App for Splunk to the instance which is collecting the Cloudflare
JSON data.

4. By default within the application JSON key-value extraction is turned on at search time by setting KV_MODE
in the props.conf packaged with the application to json. If you happen to set up INDEXED_EXTRACTIONS
for the cloudflare:json, cloudflare:access, cloudflare:audit, cloudflare:casb, cloudflare:dns, cloudflare:http and cloudflare:network sourcetypes at the point of which you are onboarding data then you will need
to set KV_MODE=none in the props.conf packaged with the application to ensure field values are not
extracted twice and thus impacting the dashboards.


## Application Installation Instructions ############################

The Cloudflare App for Splunk is easy to install and configure. Please follow the steps below to install and configure
the application within your Splunk environment.

1. Ensure the Application Requirements documented above are met.

2. Download the application from Splunkbase.

3. Install the application on your Search Head or Search Head Cluster using standard application deployment
methods. Information on installing applications on Splunk can be found in the Splunk documentation here:
https://docs.splunk.com/Documentation/Splunk/latest/Admin/Deployappsandadd-ons

4. Once installed the application needs to be configured. A Set Up page is bundled with the application. To
configure the application following these steps:
  a. Access the application on your Search Head by clicking on the “Cloudflare App for Splunk” from
     your Splunk launcher home page or from the Apps dropdown menu. You will be prompted with the
     application Set Up screen.
  b. Enter the Index name where the Cloudflare JSON logs are stored. This value must be entered in
     the format index=index_name. By default the value is set to index=cloudflare
  c. Choose whether to enable Data Model Acceleration. By default, acceleration is disabled.

5. The application is now installed and can be found on your Splunk launcher home page or through the Apps
dropdown menu to the top left. Enjoy!


Post-Installation Notes:

- The Index Name can be changed after initial configuration by following below step.
   1. The Index Name can also be manually found by going to Settings > Advanced search > Search macro within the Cloudflare App for Splunk. In order to  change the definition to  point to  the custom  index in  this format. index=<custom index name>'
   Notes:- If anyone is not using default index(which is cloudflare) value in Splunk Add-on for AWS then one must have to follow the above step to change the index in macros definition as well.

- The Cloudflare App for Splunk comes with a custom Cloudflare Data Model which has an acceleration time
frame of 1 Day but is not accelerated by default. If you enable Data Model acceleration it is recommended
that the Data Model is only accelerated for 1 or 7 days to ensure there are no adverse effects within your
Splunk environment. You can enable or disable acceleration after initial configuration by accessing the App
Set Up page by clicking on Apps dropdown > Manage Apps > Set Up link to the right of Cloudflare. Data
Models can also be manually configured by going to Settings > Data models. More information on data
model acceleration can be found here: https://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels
