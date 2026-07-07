# Table of contents
1. [Introduction](#introduction)
2. [Prerequisites](#prereq)
3. [Installation](#installation)
4. [Issues](#issues)

## This is the introduction <a name="introduction"></a>
This app contains visualizations for data ingested from TA-Hockeymon. It uses two accelerated data models and two search-managed lookups to represent the data. There is a custom command to communicate with the NHL Stats API to pull information for NHL teams.

## Prerequisites <a name="prereq"></a>
Data ingested from <a href="https://splunkbase.splunk.com/app/4731/">TA-Hockeymon</a>

## Installation <a name="installation"></a>
1. Download and install Splunk app for Hockey Monitoring on a search head
2. After installation and data ingestion is complete, accelerate the two data models within the app.
    1. By default, there is a macro pointing to "index=hockey" for this data. Change this macro to point to the correct index
    2. Go to "Settings"->"Data Models"
	3. Click the "Edit"->"Edit Acceleration" dropdown for each data model and enable acceleration. The default summary range is fine but can be changed if desired.
3. Run two searches manually to initialize lookups by going to "Settings"->"Search, reports and alerts", find these searches and select "Run"
	1.  Hockeymon Players - Lookup Gen
	2.  Hockeymon Teams - Lookup Gen
4. These searches can be scheduled if desired.
6. After steps 2-3 are complete, the app is setup is complete

## Issues <a name="issues"></a>
Either via <a href="https://gitlab.com/wguest/splunk_app_for_hockey_monitoring">GitLab</a> or hockeymon@wadeguest.com
