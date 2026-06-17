Barracuda Web Filter

This application was designed for Splunk to give users usable data surrounding the requests being sent to their Barracuda Web Filter.  The application was designed using data from a Barracuda Web Filter 310, even though the access logs should be universal across the Barracuda Web Filter family of appliances I cannot guarantee it will work with other versions.

Pre-deployment Assumptions:

1. You have enabled syslog logging on your Web Filter appliance.
2. The logs are being absorbed by Splunk and given a sourcetype name "barracuda". Sourcetype renaming is in place in this application.
3. You are using LDAP authentication.  If you are not you may need to tweak the stanza named barracuda_without_ldap in transforms.conf

Reports in this Application:

   Top Users by Spyware Type
   Top Domains by Spyware Type
   Top Spyware Types
   Top Source IPs by Spyware Type
   Bandwidth Usage
   Top Ten Bandwidth Consumers by User ID
   Bandwidth Consumed by Hour of Day
   Bandwidth Consumed by Day of Week
   Domains by # of Requests
   Top Domains Accessed by User
   Domains by Bandwidth Consumed
   Most Accessed Content Type by Domain
   Users by # of Requests
   Categories by # of Requests
   Users by Bandwidth Consumed
   Content Type by Bandwidth Consumed
   Top Category per User
   Top Content Types
   Source IPs by # of Requests
   Dest IPs by # of Requests
   Source IP by Bandwidth Consumed
   Dest IP by Bandwidth Consumed

You can also use the "Log Search" tab to manually search the logs using the defined categories.

There is now a "Threat Intelligence" tab that includes any notable events flagged as matching Phishtank.com URLs. New feeds to be added in the future.

