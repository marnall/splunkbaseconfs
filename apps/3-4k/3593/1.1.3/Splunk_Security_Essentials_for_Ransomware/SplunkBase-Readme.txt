# Table of Contents

1. App Description
2. Functionality Overiew
3. Use Cases
4. Datasources Used
5. Installation
6. First Time Seen Searches
7. Time Series Searches
8. General Splunk Searches


# App Description

Detect insiders and advanced attackers in your environment with the free Splunk Security Essentials for Ransomware app. This app uses Splunk Enterprise and the power of our Search Processing Language (SPL) to showcase 40+ working examples of anomaly detection related to entity behavior analysis (UEBA). Each use case includes sample data and actionable searches that can immediately be put to use in your environment.

The use cases leverage analytics to give analysts the ability to detect unusual activities like users who print more pages than usual (spike detection) or logon to new servers (first seen behavior), the ability to see when adversaries change file names to evade detection, and more. Each use case includes the expected alert volume, an explanation of how the search works, description of the security impact, and you can save searches directly from the app to leverage any alert actions you have installed such as creating a Notable Event or Risk Indicator in ES, an External Alarm in UBA, or sending email for review.

# Functionality Overview

The use cases for the app fall into three categories – time series analysis, first time analysis, and general Splunk searches.
 
The time series analysis tracks numeric values over time (# of pages printed per user, # of interactive logon sessions per account, etc.) and looks for spikes in these numbers. This is done by leveraging standard deviation in the stats command to look for data samples many standard deviations away from the average. Importantly, these are not hard set thresholds (bad: alert if more than 150 pages printed), these are not organization-wide thresholds (bad: alert if a user prints more than 10 stdev above the organization average). These are per-user thresholds (good: alert if any user prints > 3 stdev above their personal average). Just as important is the implementation of confidence (great: alert if any user prints > 3 stdev above their personal average, and we have enough data points to think that means something). Finally, this app supports large scale environments by automatically creating a summary index search that runs daily, and then a historical search that analyzes the summarized data.
 
The first time analysis is simpler conceptually – many things are rare for a user. Service accounts typically log into the same set of servers – if a service account all of a sudden logs into another device, or logs in interactively, that’s new. This detection is also done via stats, using first() and last(). The app also supports peer groups here, using eventstats to find the values shared amongst people in the peer group to filter out objects that are new for a particular subject (e.g., this git repo is new for user John Smith) but not new for their peers (filter out if John’s teammate has regularly checked out from that same repo). As of 1.1.0, the app also supports super high scale environment (and better search efficiency overall) by caching data to a lookup. 
 
The final category, general Splunk searches, encompases many different techniques within Splunk. Here, we leverage much of the great work that has been done inside of Splunk with tools like the URL Toolbox for Shannon entropy detection, Levenshtein filename mismatch detection, detections based on transaction, and more.

# Use Cases

## Access Domain
* Authentication Against a New Domain Controller
* First Time Logon to New Server
* Significant Increase in Interactively Logged On Users
* Geographically Improbable Access (Superman)
* Increase in # of Hosts Logged into
* New AD Domain Detected
* New Interactive Logon from a Service Account
* New Local Admin Account
* New Logon Type for User
* Short Lived Admin Accounts
* Significant Increase in Interactive Logons

## Data Domain
* First Time Accessing a Git Repository
* First Time Accessing a Git Repository Not Viewed by Peers
* Healthcare Worker Opening More Patient Records Than Usual
* Increase in Pages Printed
* First Time USB Usage
* Increase in Source Code (Git) Downloads

## Network Domain
* Detect Algorithmically Generated Domains
* Remote PowerShell Launches
* Source IPs Communicating with Far More Hosts Than Normal
* Sources Sending Many DNS Requests
* Sources Sending a High Volume of DNS Traffic

## Threat Domain
* Detect Data Exfiltration
* Sources Sending Many DNS Requests
* Sources Sending a High Volume of DNS Traffic

## Endpoint Domain
* Concentration of Hacker Tools by Filename
* Anomalous New Listening Port
* Concentration of Discovery Tools by Filename
* Concentration of Discovery Tools by SHA1 Hash
* Concentration of Hacker Tools by SHA1 Hash
* Familiar Filename Launched with New Path on Host
* Find Processes with Renamed Executables
* Find Unusually Long CLI Commands
* Hosts with Varied and Future Timestamps
* New Host with Suspicious cmd.exe / regedit.exe / powershell.exe Service Launch
* New Parent Process for cmd.exe or regedit.exe
* New Path for a Common Filename with Process Launch
* New RunAs Host / Privileged Account Combination
* New Service Paths for Host
* New Suspicious Executable Launch for User
* Processes with High Entropy Names
* Processes with Lookalike (typo) Filenames
* Remote PowerShell Launches
* Significant Increase in Windows Privilege Escalations

# Datasources Used

* Domain Controller Logs
* Windows Process Launch Logs (Event ID 4688)
* Endpoint Agent Logs (Carbon Black, Sysmon)
* Windows System Logs
* Source Code Repository Logs
* Firewall Logs
* Windows Account Management Logs
* Electronic Medical Record System Access Logs

# Installation

For Single Server Installations, app setup is very straightforward. It can be installed directly from SplunkBase through the UI inside of your Splunk installation if you have direct internet access. Or you can download the app from SplunkBase and install it from Manage Apps in your Splunk install. (Note, due to a Chrome design quirk, sometimes when you download a tgz file Chrome will automatically decompress it as a tar file. If you have that experience, just download using Safari instead.)

For Distributed Installations, app setup is equally straightforward. It can be installed on the Search Head only, in the same way as you would a single server installation. The app supplies a distsearch.conf that prevents the heavy volume of lookups from being added to your bundle replication, avoiding impact to the indexers.

By default, after installing the app, there will be no increase in indexed data, searches, or etc. All actual impact to your real environment (apart from the ~250 MB on the search head, mostly with all that demo data) will be when you save and enable searches. More on that next!

# Performance Impact

The Performance Impact of the searches will vary wildly by your environment. If you are searching the Windows logs for 2 desktops, the performance impact of the most intensive searches will be nothing. Searches for Domain Controller logs with hundreds of thousands of users will be more so. Ultimately though, any search you add is just that -- a search. Because we will generally schedule these analytics to run once a day, they can be run at off hours when there is a dramatically lower impact to system utilization. Additionally, all searches have been vetted by Splunk's performance experts to ensure they are as performant as possible. For customers running in larger environments, it is highly recommended to leverage the lookup cache for first time seen searches, and the high scale / high cardinality time series searches that leverage summary indexing. Those are detailed in the following sections.

# First Time Seen Searches

This method of anomaly detection tracks the earliest and latest time for any arbitrary set of values (such as the first logon per user + server combination, or first view per code repository + user combination, or first windows event ID indicating a USB Key usage per system). With normal usage, you'd check to see if the latest value is within the last 24 hours and alert if that's the case (with our demo data, rather than comparing to right now() we compare to the largest value of latest()). This is a major feature of many Security Data Science tools on the market (though not Splunk UBA) that you can get easily with Splunk Enterprise.

## First Time Seen Searches - High Scale Version

When viewing any of the first time seen examples (those which use the Detect New Values assistant), such as "First Logon to New Server" or "New Interactive Logon from Service Account" (or frankly any examples that contain "first" or "new" in the name), without leveraging caching you need to run a search over the entire time window that is in scope. For example, if you want to detect new interactive logons by service account you will need to search over your entire time window (typically 30 days, 45 days, although sometimes customers look for upwards of 100 days). This is great for many use cases, where you're running over a few tens of thousands of events. Even for some longer searches, if they're running at 2 AM when no one is online, it's not a big problem to have a search run longer than you'd want in the middle of the day. However, you can also cache the data locally. In this scenario, we will look over the last day of data, add in the historical data to recompute the earliest and latest, update the cache, and then find the new values. 

This is great because it means your performance can be dramatically better (for baselines of 100 days, and assuming slower cold searches, you can see performance improvements of well over 100x!). The downside here is that you have to store that cache. Because this is a lookup file, we will put it in a CSV on the search head. If each row has a couple of timestamps and a couple of 30 character fields, and you have 100,000 combinations, that lookup would be 7 MB -- hardly a thing. However, if you have 300 million combinations, that's 230 MB, which is non-trivial! For most Splunk customers, this isn't a problem -- they have 150 GB disks for their SHs and they don't have to think twice. For some customers that have super-minimal partitions (not recommended!) with only 10GB available, this can be a much bigger issue.

A final note on this approach -- with lookups in the Splunk Security Essentials for Ransomware app, we automatically prevent the lookups from being distributed to the indexers in the bundle -- this prevents your bundles from getting too big, which makes for super reliable Splunk installations, so you don't have to worry about anything. However! If you put these lookups in any other apps (for example, you copy-paste the searches to your production app, or you move the saved search into a different app), you won't have that blacklist. That's not a big problem for the lookups that are a few megs in size, but for the 250 MB files, particularly many 250 MB files, that could impact the stability of your environment. This is very easy to manage -- just make sure that you have a process for managing the lookups, if you start going big in this direction. It's easiest just to keep things in the Splunk Security Essentials for Ransomware app anyway. 

# Time Series Searches

This method of anomaly detection tracks the earliest and latest time for any arbitrary set of values (such as the first logon per user + server combination, or first view per code repository + user combination, or first windows event ID indicating a USB Key usage per system). With normal usage, you'd check to see if the latest value is within the last 24 hours and alert if that's the case (with our demo data, rather than comparing to right now() we compare to the largest value of latest()). This is a major feature of many Security Data Science tools on the market (though not Splunk UBA) that you can get easily with Splunk Enterprise.

## Time Series Searches - High Scale Version

When viewing any of the time series examples (those which use the Detect Spikes assistant), such as "Increase in Pages Printed" or "Healthcare Worker Opening More Patient Records Than Normal," (or frankly any use cases that contain "Increase" in the name), without leveraging the high scale search you would need to run the search over the entire time range. Additionally, since we're storing data per day, per object, if we're looking at users who print more than normal with a 100 day baseline and 100k users, that would be 10M rows to store in memory. Running the search over 100 days every time the job runs requires more resources can be rough for some scenarios (though if you're running it at 2 AM, decide how important that really is), and storing 10M rows in memory is definitely rough (my guideline, 800k - 2M is a good upper limit for performance). 

For these scenarios, we will actually schedule two searches. The first search runs every day and stores the daily summary to a summary index. Effectively, if we are tracking how many patient records a nurse opens, we're going from 300 events per nurse each with a bunch of metadata, to a single record with a username, datestamp, and number. That is the dataset that will be analyzed by the second search, which actually calculates the standard deviation. This has two benefits: the first is that you're running over an aggregated dataset (imagine a 300x, or 1000x improvement just in sheer volume). The second is that number of records Splunk has to store in memory. This part is a little arcane, so you can just take my word for it, but effectively Splunk has to manage the cardinality (amount of variation in the fields) for both the time series, and whatever you are analyzing. In that scenario listed above, of a 100 day baseline with 100k users, where you would normally have to store 10M records in memory, by preprocessing the time series analysis, you can store only 100k in memory. I suggested 800k - 2M where you can control it, 100k is way lower. 

This is a huge benefit, and Summary Indexing is incredibly powerful, but there are two downsides. Obviously we have to manage a second scheduled search, and make sure that it is not skipping (you can backfill if it does skip -- just look at the fill_summary_index.py script, and the --dedup flag via google). And just as obvious, we will also have to store data in that summary index, which means more storage on your Splunk indexers (though generally not that much). Notably, summary indexed data does not count against your license, so there's no limitation or downside there. 

Self-promotion: for more on how to use Summary Indexing in this way, check out http://www.davidveuve.com/tech/how-i-do-summary-indexing-in-splunk/ (as true almost 6 years ago as today!). 

# General Splunk Searches

The remainder of the searches in the environment are straightforward Splunk searches. They typically don't require a baseline (certainly not a 30 day, or 100 day one), and so can be run over the last half hour of data easily. In truth, you will get just as much (for a couple, even more!) value if you just copy-paste the raw searches here into your Splunk environment and start using them. These searches are easy and straightforward. 
