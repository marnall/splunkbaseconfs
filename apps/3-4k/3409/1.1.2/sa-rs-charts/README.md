# Custom Views and extended views for splunk
**Software License Agreement**

Author: Robert Schild (info@rocket-consulting.eu)
Usage: As a Splunk App (JS Extension) for use custom views in XML/HTML and JSStack

While installing Splunk Software you already accepted the Splunk Software License Agreement
(http://www.splunk.com/view/SP-CAAAAFA) which is valid above the Apps installation directories.

## Compatibility
- Splunk Enterprise 6.1, 6.2, 6.3, 6.4, 6.5

## Changelog
- **2016-12-09** rsc  - created

## Release Notes
- **v1.0** - basic extensions for views
- **v1.1** - cleanup, documentation
- **v1.2** - cleanup code, better code for better handling

## Installation
- **on SH**: install

## General Information
- Splunk views (JS) extensions for better views

## TODO

## Overview
- Provides custom views for splunk (HTML-views) in JS
- this is a lite-version, with limited functionality (contact me to get a pro-version)
- all objects are global - can be used (include in custom HTML-views) in other UI-apps

## Prerequisites, requirements
- Usage in your apps: Copy from the examples : the simple-XML, the corresponding CSS and the corresponding widget.js into your app directory
- You don't need to copy the whole (sa-rs-chart) app - do references (for the views) at the sa-rs-charts app
- check out the simple-xml(examples) and customize your dashboard (copy code or do it from (examples)scratch)
- don't forget to check out naming for tokens, (element)IDs, search-IDs, ... while customize
- sometimes it's a little bit hard to customize (eg. custom filter view), but if you check out the examples, it should be clear, I hope (There is some inline documentation wihtin the js-files)

## required lookups
- for the example there is a lookup (lookup: "custom_filter_lookup" in the kv-store: "kvstorefiltercoll") defined. An example for the structure ("custom_filter_view.csv")is in the lookups directory.

## required Indexes
- n/a

## required TAs or other Apps
- n/a
