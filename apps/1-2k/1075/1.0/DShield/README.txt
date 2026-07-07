Copyright (C) 2012 Bojan Zdrnja, INFIGO IS d.o.o.

Add-on:             DShield for Splunk
Last Modified:      06-24-2012
Splunk Version:     4.x
Authors:            Bojan Zdrnja <bojan.zdrnja@infigo.hr

DESCRIPTION:

The DShield for Splunk application allows you to search, navigate and
summarize SANS Internet Storm Center's DShield data (http://www.dshield.org).

DShield is a community-based collaborative firewall log correlation system. It
receives logs from volunteers world wide and uses them to analyze attack
trends. It is used as the data collection engine behind the SANS Internet
Storm Center (ISC). It was officially launched end of November 2000 by
Johannes Ullrich. Since then, it has grown to be a dominating attack
correlation engine with worldwide coverage.

If you have any comments please contact the author at bojan.zdrnja@infigo.hr.

More information about INFIGO IS is available at http://www.infigo.hr/en.

==========================================================================

REQUIREMENTS:

Since the application automatically retrieves data from SANS Internet Storm
Center and DShield, the Splunk server needs access to the Internet,
specifically to the http://isc.sans.edu web site.

The following URLs are accessed:

* http://isc.sans.edu/feeds/daily_sources - retrieves the daily All IP source
  from DShield. This is the main data source that contains lists of IP
  addresses reported to DShield. It is retrieved once per day and can be
  between 40 and 50 MB in size.

* http://isc.sans.edu/api/handler - used to retrieve the current SANS Internet
  Storm Center Handler on Duty (HoD)

* http://isc.sans.edu/api/infocon - used to retrieve the current Threatcon
  level

* http://isc.sans.edu/rssfeed.xml - used to retrieve information about current
  SANS Internet Storm Center diaries. This is automatically refreshed every 20
  minutes.


Besides access to the Internet, for Google maps visualization the Google maps
for Splunk application is needed as well
(http://splunk-base.splunk.com/apps/22365/google-maps).


=============================================================================

APPLICATION SETUP:

Just follow the setup screen. The two main configuration parameters include
when you want to pull the DShield data and what are your networks.

Keep in mind that DShield releases a new version of data every day at 4 AM UTC
so you might want to synchronize with that (no point in pulling data more
often).

*** Manual synchronization ***

In case you want to manually pull data from DShield just use the following
command:

| syncdshield

Keep in mind that it might create duplicates if your scheduled is working as
well (not handled at the moment, will be added in future versions).
Also, keep in mind that it can take some time to pull 50 MB so please be
patient.

Set up your networks so the main status screen will show if your networks are
detected by DShield as attackers! This can be an early warning system so use
this for alerting.

==============================================================================

Changes in v1.0 (06/24/2012):

* Initial release.

