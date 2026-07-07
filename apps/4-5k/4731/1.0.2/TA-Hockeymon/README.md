# Table of contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Issues](#issues)

## This is the introduction <a name="introduction"></a>
This add-on is designed to ingest scores and statistics from the NHL's open web API. Visualizations and datamodel for this data are included in the <a href="https://splunkbase.splunk.com/app/4732/">App for Hockey Monitoring</a> on Splunkbase. 

## Installation <a name="installation"></a>
1. Download and install TA-Hockeymon on an instance of Splunk Enterprise with a web interface enabled.
2. Navigate to the add-on's input section.
3. Create a new input and enter a day to begin ingestion. Ingesting from 2013-09-01 takes ~850MB of license. Estimate around 150MB per season.
4. The scores and events will begin to populate the designated index as the input progresses. Do not issue a restart while historical events are ingested. This can take a few hours depending on system specifications.
5. The add-on will continually check for newly completed games based on the interval provided in step 3
6. Proceed with installation of <a href="https://splunkbase.splunk.com/app/4732/">App for Hockey Monitoring</a>

## Issues <a name="issues"></a>
Either via <a href="https://gitlab.com/wguest/TA-Hockeymon">GitLab</a> or hockeymon@wadeguest.com

