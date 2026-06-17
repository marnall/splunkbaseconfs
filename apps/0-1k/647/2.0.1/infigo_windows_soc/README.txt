Copyright (C) 2011 INFIGO IS d.o.o.

Add-on:             Windows Security Operations Center
Last Modified:      08-11-2011
Splunk Version:     4.2
Authors:            Bojan Zdrnja <bojan.zdrnja@infigo.hr>, Branko Spasojevic <branko.spasojevic@infigo.hr>

DESCRIPTION:

This applications summarizes and visualizes all security relevant information
in your Windows environment.

The application is configured to use the Windows index (index=windows). You
should configure your Splunk to store all Windows logs (Windows Event Logs as
well as Windows Update logs) into this index and the application will work
automatically. Otherwise, you will need to modify dashboards and searches so
your indexes are searched.

Special attention was given to Windows authentication logs. Since Windows
clients normally issue several ticket requests when a user logs in to the
domain, this can cause an incorrect number to be displayed if these login
events are just visualised. In order to correctly calculate the number of 
login events, the Windows Security Center application uses Splunk's
transactions to summarize such events - see searches used in Active Directory
and NTLM dashboards for more information.

If you have any comments please contact us at splunk@infigo.hr.

More information about INFIGO IS is available at http://www.infigo.hr/en.

==========================================================================

Changes in v1.1 (08/11/2011):

* Added setup screen in order to allow easy (re)configuration.
* Added Windows Firewall dashboards.
* Some minor fixes.

