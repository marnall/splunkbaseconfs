###############################################
# Version 2.6.6
# Authors Tristan Collins
# Release Date: 29 Aug 2022
#
###############################################
Minor bug fixes:
- Scripting errors reported on elearning and adoption dashboards
  - updated tabs.js
  - updated tabs.css
  - updated elearning.xml
  - updated adoption.xml







###############################################
# Version 2.6.5
# Authors Tristan Collins
# Release Date: 16 Feb 2022
#
###############################################
Minor bug fixes and dashboard enhancements:
- Added System Info > Health > CPU Utilisation - For workload pricing customers to have an overview of what is impacting their environment
- Update for jQuery 3.5 requirements for all dashboards.
- Fixed issue with Index Config Overview search not completing - Bucket events on 8.2.x
- Fixed issue with EDU dashboard search missing records that use SCORMLESSONSTATUS "completed" vs. "passed"





###############################################
# Version 2.6.3
# Authors Yaniv Feldman, Tristan Collins
# Release Date: 03 Aug 2021
#
###############################################
Minor bug fixes and dashboard enhancements:
- lower panels in content creation dash were readded
- bug: disable schedule for saves search: History collect events meta data
- bug: Index Details - The previous query did not show roles with access correctly
- changed sort descending and top 10 charts in apps analysis, ad hoc search analysis, dashboard analysis
- remove the app-restart requirement as it no longer contains indexes.conf
- Enablement dashboard rework to remove manual transcript editing on upload.





###############################################
# Version 2.6.2
# Auhtors Tim Clark, Yaniv Feldman, Tristan Collins
# Release Date: 29 Sep 2020
#
###############################################

Before using version 2.6.0 of the app please carefully read these instructions:
The CST app is collecting Splunk's internal data to help you understand how Splunk is used in your organization. 
For that, the CST app is using a summary index. 
First, You'll need to create a new summary index. We recommend you name it cst_summary, however you choose a different name. 
If you chose a different name for the summary index, pleae do the following:
	- In the CST app, change the definition of search macro `cst_summary_index` to: index=<your_new_summary_index_name>

The new Adoption Analysis Dashboards provide insights on application usage and content creation. 
Before running the app for the first time, run the following summary searches:
(Settings-->Searches,Reports, and Alerts-->App:CST2.6)
  - History collect adhoc searches
  - History collect app access
  - History collect dashboard access
  - History collect events meta data
  - Daily collect app metadata
  - Daily collect dashboard metadata
  - Daily collect savedsearch metadata
  - Daily collect events metadata
Once these searches have finished successfully the CST summary index should be populated with data which will appear in the Adoption Analysis Dashboards

Release Notes:
- Added new Adoption Analysis Dashboards:
  - Content Creation Analysis
  - App Analysis
  - Dashboard Analysis
  - Saved Search Analysis
  - Ad-Hoc Search Analysis
  - Platform Adoption Monthly Analysis  

- Added summary searches to populate visualizations in the dashboards above:
  - History collect adhoc searches
  - History collect app access
  - History collect dashboard access
  - History collect events meta data
  - Daily collect adhoc searches
  - Daily collect app access
  - Daily collect app metadata
  - Daily collect dashboard access
  - Daily collect dashboard metadata
  - Daily collect savedsearch metadata
  - Daily collect events metadata
  - Splunk Monthly Adoption Metrics

- Education reports:
  - Search optimisation
  - Included ILT course detail

- Added Dark Mode


Known issues:
- Education Transcript upload: Transcript csv export header row needs to be manually changed to uppercase before uploading in order for reports to work:
  REGISTRATIONID,FIRSTNAME,LASTNAME,EMAIL,DOMAINNAME,SCHEDULEID,COURSENAME,REGISTRATIONTIMESTAMP,REGISTRATIONSTATUS,SCORMLESSONSTATUS,ELEARNINGSTARTDATE,ELEARNINGCOMPLETIONDATE,REGISTRATIONENTEREDDATE,SCHEDULEDSTARTDATE,SCHEDULEDENDDATE,ELEARNINGLASTACCESSDATE,ATTENDED,PASSED,CLASSTYPE
- eLearning Details Report: There are issues with how courses are displayed (complete, incomplete, etc. ) due to how they are reported in underlying transcript file.
  We are working with the education team to get this resolved.

#############################################
# Customer Success Toolkit
# Version 2.5.9
# Authors: Tim Clark
# Release Date: 3.12.2019
#
##############################################

Description:
The Customer Success toolkit is intended to assist with Customer Success efforts facilitated by your CSM.

Installation:Installation is for Search Heads only (nothing required for Indexers; do not install it on the Cluster Master).  
Installation can be completed via GUI or CLI

CST contains 3 scheduled searches. While most customers do not keep the associate data past 30 days, the duration and frequency may be adjusted. The duration may be reduced; but it is recommended they run at least 4 times per day.

EDU: In order for Enablement and EDU data to populate properly, you will need to obtain the appropriate CSV from your CSM. This 
EDU file must be uploaded into the "education_reports" index with a "edu_reports" sourcetype. This is fully explained in the 
associated Installation Instructions (found on SplunkBase for this application).

Note: EDU-related csv files with double=quotation marks at the beginning and end of lines need to be removed.
This is not relative to csv field values which may be delimited or encapsulated in quotes; but only
relates to entire textual lines beginning and ending with double-quotes. This is further described in the
Description section of SplunkBase for this application.

Success Planning - Please edit the source of the dashboard to include the URL provided by your CSM.

Index Definition: You may put the EDU-related data into any index, but we recommend creating and using a
name like "education_reports" as you index name.

Possible Issues:
Due to security restrictions, if REST enpoints are restricted, many dashboards may not populate
Splunk, by default only keeps about 30 days of _internal index data, so this must be increased to see the longer data 
views of 180 days (for example).