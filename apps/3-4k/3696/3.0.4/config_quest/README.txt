Config Quest by Discovered Intelligence
===========
For support, please email support@discoveredintelligence.ca

## What's New In This Release? ############################
- Small code tweaks and enhancements
- New 'File Config Quest' dashboard allows you to navigate the directory structure on any or all your Splunk hosts remotely and compare files and view configurations.

## Overview ############################

Config Quest is an awesome lightweight utility from Discovered Intelligence for searching and reviewing Splunk configurations on any Splunk server directly from your search head! Use Config Quest to search for any stanza or configuration parameter, in any selected app, across any Splunk server in your environment.

At the heart of the app are several a powerful dashboards that enable the searching of Splunk configurations by conf file, host, app, stanza and/or parameter. Configurations returned are nicely formatted into the familiar stanza, parameter and value Splunk conf file format, along with text based highlighting to aid visualization and readability. There are dashboards for reviewing configuration changes, finding configuration differences, comparing configurations between hosts and identifying installed application differences.

**New!** You can now also use Config Quest to navigate through the file system across all your Splunk servers remotely, compare files and perform one-click config quests on conf files!

## Why is this app useful? #########################

You can use Config Quest to:
- Instantly search for Splunk configurations across any Splunk server in your environment from one place
- Search for configurations by host, wildcard host, conf file, app, stanza and/or parameter
- Identify configuration differences across all your similar Splunk servers (e.g. all indexers)
- Compare configurations on one host with those of another
- Identify all installed applications and application installation differences across your Splunk deployment
- Centrally review your serverclass.conf and view the serverclasses and apps, along with the deployment clients that have been assigned the serverclasses
- Navigate directory structure of your local or remote Splunk hosts 

## Why not just use btool? #########################

Config Quest does not replace btool, but instead provides a convenient mechanism to remotely review configurations residing on your Splunk servers, without the need to log into the host and run btool or check files manually. There are no scripts to run, no complex logic to learn and nothing to install other than this app on your Search Head. While btool rolls up configurations using Splunk's inheritance based rules, the configs returned by Config Quest are in their raw state prior to rollup, although some defaults are picked up in the results.

## How Does It work? ###########################

The app leverages Splunk's REST based commands, then uses complex formatting and logic to present the data in a familiar Splunk Conf file format by stanza, parameter and value.

## Are there dashboards/reports? ##########################

Yes, there are six dashboards as follows:
- **Current Config Quest** - allows for centralized searching and reviewing configurations across all your Splunk servers
- **Difference Config Quest** - helps you to find differences in specific configurations across your similar Splunk servers
- **Comparison Config Quest** - allows you to compare the configuration on one host with that of another host for a specific Splunk conf file
- **Application Config Quest** - helps you to identify application installation differences across your Splunk servers
- **Serverclass Config Quest** - allows for remote interogation of your Serverclass.conf, presenting a similar view to the deployment server and lists all serverclasses, apps and the deployment clients associated with the various serverclasses. Note: For this to work, you must add your deployment server(s) as search peers.
- **File Config Quest** - allows you to navigate the directory structure on any or all your Splunk hosts remotely and compare files and view configurations

## Important Stuff ###########################

Requirements:
- Only tested to work on Splunk 6.5 and above
- Splunk servers that you want to view configurations from must be added as search peers to the search head that the app is install on
- If you are looking for the configs in system/local or default - choose the 'system' app from the Current Config Quest dashboard

## How do I install this? ###########################

The app is super simple to install.
1. Download the app from Splunkbase
2. Install the app on a search head or search head cluster.
3. Restart Splunk - this is because we have a small amount of JS that helps to colour format configurations
4. Go to the app and start your config quest!

Additional step if you have installed Splunk in a different path to the default Splunk install path for your OS:
5. Update the macro named "**file_quest_os**" in the Config Quest app and modify the Splunk home path to the path of your install. For example, if you installed Splunk on Linux in /app/splunk, then update the Linux section of the macro from "Linux,%2F**opt**%2Fsplunk" to "Linux,%2F**app**%2Fsplunk"

Additional step if you are running Splunk on Windows to change the default OS on the File Config Quest:
6. Firstly, do not update the dashboard directly. Update the macro named "**file_quest_default**" in the Config Quest app and modify the OS to either *Windows*, *Linux* or *Mac*. Please do not deviate from these values.

For support, to request feature enhancements or simply to give us your feedback - please contact us at support@discoveredintelligence.ca

## Future Release ###########################

The following items are planned for a future release. Let us know if you would like us to add something!
- Historic conf file analysis - the ability to archive configurations and then reference old configurations and compare against current configurations

## Q&A ###########################

Any useful support questions and answers will be posted here for others to view

Q. Where would you recommend installing this?
A. Typically this application would be installed on the same Search Head that you do your operational reporting from. However, it can be installed on any Search Head, including Search Heads in Splunk Cloud.

Q. The Difference Config Quest seems to take a long time to run
A. If your environment is large, then broad, unfiltered configuration searches may take a small amount of time to run depending on the configuration file selected and number of hosts you have, but it will complete if you are patient.

Q. I am seeing both local and default configurations being returned
A. Correct, default configurations will be returned when there is no local or app specific configuration taking precedence. There is currently no way to identify whether the configuration presented is in local or default - this is mostly due to the REST API not returning this data.

Q. This application says install only on a SH or SH Cluster but I would like to install this on my Splunk Cloud IDM (Intermediate Data Manager) is this ok?
A. Yes, Config Quest will function perfectly well on the Splunk Cloud IDM instance and allow you to see details of the configurations for your add-ons and apps installed on the IDM server.

Q. I installed Splunk in /app/splunk instead of /opt/splunk and File Config Quest dashboard is returning an error. 
A. If you installed Splunk in a different location to the default for either Windows or Linux, you will need to update the macro named "file_quest_os" in the Config Quest app and modify the Splunk home path to the path of your install, following the same syntax in the macro.

Q. I have a Windows install of Splunk but the new File Config Quest dashboard is defaulting to Linux. Can I change this without updating the dashboard code?
A. Yes, please avoid updating the dashboard directly with a new default as this will make support and future upgrades a lot more challenging. Instead, there is a macro named "file_quest_default" within the Config Quest app, where you can modify the default OS to either Windows, Linux or Mac.