Homepage for Splunk by Discovered Intelligence Inc.

## Overview ############################
Homepage presents logged in users with a 'virtual cockpit' that provides a single-pane-of-glass view into their specific use of Splunk. It does this through the use of a central home page, tailored to the user, that provides insight into the indexes and sourcetypes they have access to, the search jobs they have run, the saved searches and dashboards they have created and the apps they have permission to access. Users are able to dynamically drill-down into more details, re-run searches and jobs, or immediately search specific data sources. All this is done leveraging a simple point-and-click driven approach.

The app is designed to be a useful utility, shared globally across Splunk applications that can leverage it as the default home page for their app.

## Benefits ###########################
The app provides the following benefits:
- Presents users with a virtual cockpit into Splunk, providing at-a-glance key information tailored to the logged in user
- Greatly aids in a users understanding of Splunk, the data sources they can access and their specific search activity
- The point-and-click driven approach simplifies the Splunk learning curve and allows users to search data without typing anything
- The use of drill-down allows for additional relevant information to be displayed
- REST driven approach provides extremely fast performance without the need to search indexed data
- Tested to work at scale with both environments consisting of 100s of Splunk users and smaller environments of a few users
- Can be centrally administered and deployed across many apps in a Splunk environment as the default home page for those apps

## Getting Started ############################
Homepage provides 4 dashboards consisting of a main Homepage dashboard and three supplementary drill down dashboards as follows:
- Homepage (homepage.xml) - the main homepage customized and tailored to the logged in user
- Sourcetype Field Listing (homepage_sourcetype_fields.xml) - linked to from Homepage to provide a listing of fields and values for a given sourcetype
- Saved Searches Listing (homepage_saved_searches_listing.xml) - linked to from Homepage to provide a listing of saved searches authored by the logged in user
- Adhoc Searches Listing (homepage_adhoc_searches_listing.xml) - linked to from Homepage to provide a listing of adhoc searches performed by the logged in user

## Initial Install ############################
The following steps will help you get the app set up.
1. Install the app from splunkbase.
2. Restart Splunk

Points to note:
- The app is purposely hidden, as the home dashboard is designed to be accessed via other apps, not the Homepage app itself
- The app is purposely set with global permissions, in order to ensure the Homepage dashboards are accessible from other apps
- The app will generate a lookup of sourcetypes and indexes upon a restart

## Set the Homepage dashboard to be the homepage of an App ############################
The following steps can be followed to set the Homepage dashboard as the home page of any app.
1. Navigate to the Splunk App that you wish to have Homepage as the home page for.
2. Go to Settings --> User Interface --> Navigation Menus
3. Click to edit the "default" navigation of the app
4. Under the <nav> XML group, add the following line:

  <view name="homepage" default="true" />

5. Remove any other default="true" that might be in the file, then click Save.
6. Navigate back to the app and you will now see that the Homepage page appears as the homepage for the app. There will also be a "Homepage" link is present at the top left of the application's menu bar.

## Requirements ############################
The following requirements exist for this app:
-	Works with Splunk Enterprise version 6.4.x and higher
-	Designed to be installed on a single SH or a SHC
-	Tested to work with the default Splunk User and Power roles. Other custom roles that do not inherit these roles may need similar capabilities.

## Technical Support ######################

For support, please email support@discoverdintelligence.ca

App developed by Discovered Intelligence Inc.
www.DiscoveredIntelligence.ca
