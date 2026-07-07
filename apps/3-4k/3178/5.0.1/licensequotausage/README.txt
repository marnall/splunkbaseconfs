App ID = licensequotausage
App Label = License Usage
App Splunk Version Compatibility = Splunk 6.4 or later
Author = Dennis Raesner
Description = This app contains a variety of dashboard panel views that
provide additional detailed data to supplement Licensing under System,
and the License Usage dashboards under DMC/Indexing.  Some
of the views are of the quota usage per day, per month, an overlay of
the total quota, daily quota and percentage used, and views by index and
sourcetype.  Some panels have 2 variations - any can be deleted for 
customization.
System Requirements = Linux or Windows
Version = 3.9


Installation & Configuration  (the following setup instructions can also
be viewed by selecting the Setup dashboard from within the License Usage app)

All configuration changes must be made as the Splunk admin user. 

Must Be Installed On The License Server, or Search Head depending on
where the _internal logs are sent, and specifically the license_usage.log file.
Best practice is to send the _internal logs to the indexer/s so in this case
the app would be installed on the search head/s.
The _internal index must be allowed in the user's Access Controls/Role/Indexes.

To Include The "_internal" Index In The User's Role To View The License Data
Select:
Settings -> Access Controls -> Roles -> the specific user role under Role Name
Add the _internal index to the Selected Search Indexes column under Indexes
Save

To Set Up Included Reports As Alerts
Open one or more of the following reports via Open in Search, or Edit -> Clone
and edit the GB's Used or TB's Used value to suit your company needs for
different alert levels:
High Daily License Quota Usage - Over 100 GB's
High Daily License Quota Usage - Over 250 GB's
High Daily License Quota Usage - Over 500 GB's
High Daily License Quota Usage - Over 750 GB's
High Daily License Quota Usage - Over 1 TB
Save As -> Alert

To Set Up Included Reports For Email Delivery
Open one or more of the following reports via Edit -> Edit Schedule and select
Schedule Report. Schedule a cron job to run every day around 23:55 since the
daily license usage data rolls over to 0 at midnight
Today's Host Usage
Today's Host Usage By Pool
Today's Index Usage
Today's Index Usage By Pool
Today's SourceType Usage
Today's SourceType Usage By Pool
Today's Usage By Index, SourceType & Host
Today's Usage By Index, SourceType & Host By Pool

To Set Up Included Dashboards For Email Delivery
Open the following dashboards via Edit -> Schedule PDF Delivery and select
Schedule PDF. Schedule a cron job to run every day around 23:55 since the daily
license usage data rolls over to 0 at midnight
Today's License Usage - Bytes Used
Today's License Usage - Bytes Used By Pool

To Change The Range Levels For The Included Reports
Open the following reports via Open in Search, or Edit -> Clone and edit the
low, elevated and severe values to suit your company needs for different alert
levels (current settings as shown below are in GB's):
Daily License Quota Usage By Range - Last 7 Days
Daily License Quota Usage By Range - Last 30 Days
low=0-1000
elevated=1001-2000
severe=2001-3000
Save

To Change The Range Icon Levels For The Included Dashboard
Open the following dashboard via Edit -> Edit Source and edit the following
values to suit your company needs for different alert levels (current settings
as shown below are in GB's):
Daily License Quota Usage By Range Icon
Low - Maximum Range Value - GB's=1000
Elevated - Minimum Range Value - GB's=1001
Elevated - Maximum Range Value - GB's=2000
Severe - Minimum Range Value - GB's=2001
Severe - Maximum Range Value - GB's=3000
Save


Running the App
Select the License Usage icon from the vertical app menu bar.


Troubleshooting
No troubleshooting should be required, but if necessary post any questions to 
https://answers.splunk.com/app/questions/3178.html
Also, the author can be contacted at dennisraesner@att.net
