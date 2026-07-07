Supported Versions
------------------
Splunk App for Microsoft Active Directory supports the following Windows versions

	* Windows Server 2003 SP2
	* Windows Server 2003 R2
	* Windows Server 2008 (Standard, Enterprise, Datacenter)
	* Windows Server 2008 R2 (Standard, Enterprise, Datacenter)
	* Windows Server Core 2008 R2 (Standard, Enterprise, Datacenter)
	
Explicitly, this app DOES NOT support Windows Server Core 2008, as it does not support
Powershell and .NET, both of which are required by the app.

Windows Server Updates
----------------------
All servers must be at the latest Service Pack.  

Windows Server 2003
-------------------
Windows Server 2003 must have KB968930 installed (Windows Powershell and WinRM).

Windows Server 2008 R2 Server Core
----------------------------------
Enable Windows Powershell:

	- Log in as an Administrator
	- Run "sconfig"
	- Press 4, then 2 to enable Powershell

The system will prompt you to restart on enabling Powershell

Group Policy Changes
--------------------
In order to implement the Splunk App for Active Directory, the following Group Policy 
Changes must be made for Domain Controllers.  This can be done by linking a new
"Splunk App Support" Group Policy Object to the Domain Controllers container (where
the "Default Domain Controllers Policy" is linked)

1) Enable Windows Powershell Support

	Computer Configuration ->
		Administrative Templates ->
			Windows Components ->
				Windows Powershell ->
					Turn on Script Execution = Enabled
						Execution Policy = Allow local scripts and remote signed scripts
						
2) Enable Active Directory Audit (on Windows Server 2008 and above systems)

	Computer Configuration ->
		Windows Settings ->
			Security Settings ->
			  Local Policies ->
				Audit Policy
					Enable every setting EXCEPT "Audit Process Tracking"
					For each setting, enable BOTH Success and Failure

Configuring Indices
-------------------
By default, the Splunk_TA_windows logs events into the main index.  The Add-Ons for Splunk App for
Active Directory log events into one of three indices:

	* perfmon		= All performance data
	* winevents		= All Windows Event Log data
	* msad			= Everything else
	
If you decide on a different indexing scheme, you will need to create the indices, adjust the 
inputs.conf on the Add-Ons before deployment.  In addition, you will need to adjust eventtypes.conf
and macros.conf for the new index locations.

Deploying Add-ons
----------------------------
Each domain controller must have splunk_TA_windows deployed.  This Add-On gathers Windows Event Logs and
converts them with CIM compliant field extractions.  In addition, each domain controller must have
either

	* TA-DomainController-NT5 (Windows Server 2003)
	* TA-DomainController-NT6 (Windows Server 2008 and later)
	
deployed - this contains additional DC only components for gathering health data.

DNS Servers must have the appropriate DNSServer Add-On deployed:

	* TA-DNSServer-NT5 (Windows Server 2003)
	* TA-DNSServer-NT6 (Windows Server 2008 and later)
	
This contains additional DNS only components for gathering health and DNS data.

Configuring Debug Logging on DNS Servers
----------------------------------------
To gain insight into the actual DNS queries and responses that are being sent, you need to enable Debug
Logging on your DNS Servers.  On each DNS Server:

	* Open the DNS Manager
	* Expand the DNS node to view the host
	* Right click on the host and select Properties
	* Select the "Debug Logging" tab
	* Check the following elements:
		* Log packets for debugging
		* Packet Direction: Outgoing and Incoming
		* Transport Protocol: TCP and UDP
		* Packet Contents: Queries/Transfers, Updates, Notifications
		* Packet Type: Request, Response
	* Click on OK
	
You can leave Other Options check-boxes clear.  Debug Logging takes significant resources.  If you do not turn
on debug logging, you will not be able to see any detail in the DNS Reports section, but the data volumes indexed
will be reduced significantly, and the performance of the DNS servers will be better.

Configuring Active Directory Searching
--------------------------------------
Some portions of the Splunk App for Microsoft Active Directory use a live LDAP-based link to
connect to Active Directory and retrieve current data.  You must configure the activedirectory.conf
file for this to work.  A typical file looks like this:

	#
	# Configuration of your Active Directory server for searches by the
	# Active Directory app.
	#
	[server]
	ldapurl=ldap://127.0.0.1
	basedn=dc=organization,dc=local
	bindas=cn=Administrator,cn=Users,dc=organization,dc=local
	password=unlisted
	
All four fields under server must be completed.  This file must be available on each Search Head that is running
the app.  The bindas parameter must be a user with privileges to search and retrieve any non-system object within
any domain partition within the directory.  It is recommended that the Administrator of the Forest not be used 
for this purpose.

Configuring Perl
----------------
The ldapsearch command used throughout to obtain LDAP information uses Perl in order to be cross-platform.  You must
install Perl 5.10 (or later) and a number of modules.  perl is normally installed by default on Linux systems.  ActiveState 
(http://www.activestate.com/) provides a free community-supported version of perl.

In addition, you will need to install a number of modules.  If you do not have all required modules installed, then the
ldapsearch will generally return error code 2.  The list is as follows:

	Config::IniFiles
	Log::Dispatch::File
	Log::Log4perl
	Net::DNS
	Net::LDAP
	Text::CSV
	Time::Duration
	URI::Escape
	
To install a module in Windows, use:

	ppm install <module-name>
	
To install a module in Linux, use:

	perl -MCPAN -e "install <module-name>"
	
Note that dependent modules will need to be installed in both cases. There are reports that Config::IniFiles needs to have
Module::Build installed first. Ensure that all modules install successfully.  On Linux, you must be root to install modules.  
If you are running a platform other than Linux or Windows, consult your CPAN documentation on installing modules.  All the 
modules listed are pure Perl modules, so they should work cross-platform.

NOTE: At this time, running the perl commands on Windows x64 is not possible due to the following bug:

	https://rt.cpan.org/Public/Bug/Display.html?id=59790

The bug report has a diff for the broken files (which are standard files for Windows platforms and distributed with the
perl distribution).  At this time, there is no timeline for when this fix will be implemented by the author.  As a result,
we cannot recommend nor support the use of this application on Windows.

Operational logs regarding the ldapsearch command are logged in the perl.log file and available in the internal indices.


