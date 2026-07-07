# README for Sideview's TA_cisco_cdr app

This app provides the relatively simple index-time config necessary to onboard
Cisco CallManager CDR and CMR data.
Note however that almost all of the complexity around that dataset has to be
deal with at search-time (or is more suitably addressed at index time) and as
such there is a much larger commercial app called "Cisco CDR Reporting and
Analytics" that provides all that other complexity as well as SPL and UI-level
features and functionality.    90 day Trial licensing for that main app is
available from Sideview.

Documentation
For all documentation see:
https://sideviewapps.com/apps/cisco-cdr-reporting-and-analytics/documentation

Requirements
  Splunk Enterprise 8.2 or higher
  This app is designed to be deployed wherever there are or might be data
  inputs indexing Cisco CallManager CDR or CMR files.

Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud in theory although since the data
  inputs will never be there, in practice there is NO REASON TO DO SO.
