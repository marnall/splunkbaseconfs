# Custom Views and extended views for splunk
**Software License Agreement**

Author: Robert Schild (info@rocket-consulting.eu)
Usage: As a Splunk App (JS Extension) for debugging use

While installing Splunk Software you already accepted the Splunk Software License Agreement
(http://www.splunk.com/view/SP-CAAAAFA) which is valid above the Apps installation directories.

## Compatibility
- Splunk Enterprise 6.1, 6.2, 6.3, 6.4, 6.5

## Changelog
- **2016-12-29** rsc - created
- **2017-01-18** rsc - enhanced functionality
- **2017-01-20** rsc - bugfix earliest/latest time in associated searches, informations reg. searches added

## Release Notes
- **v1.0.0** - basic version
- **v1.1.0** - enhanced (debug) functionality + search manager links
- **v1.1.1** - bugfix earliest/latest time in associated searches

## Installation
- **on SH**: install

## General Information
- Splunk developer console/bar (JS) - an extension for smarter debugging

## TODO
- n/a

## Overview
- a smart developer bar for quick and smarter debugging
- all objects are global - can be used in other UI-apps (only copy the dashboard.js within your app-static-context or copy paste the content into your dashboard.js)
- **Developer Console functions** - improving your development
- "Bump" (with page reload) & "debug/refresh" always on screen
- Element inspection with highlighting - quick overview with IDs & classes & associated search manager(s) - link to searchbar & job inspector directly
- console logging (console.dir) for (selected) dashboard objects
- easy to implement in all apps & dashoboards - only copy "dashboard.js" within your app(s)
- simple, but useful :)

## Prerequisites, requirements
- n/a

## required Indexes
- n/a

## required TAs or other Apps
- n/a
