================================================================================
 TA-windows-firewall-posture - version 1.0.3
================================================================================

 Companion add-on to "Microsoft Windows Firewall Observability"
 (https://splunkbase.splunk.com/app/7790).

--------------------------------------------------------------------------------
 WHY
--------------------------------------------------------------------------------
 The main app watches EVENTS: connections in pfirewall.log, and changes in the
 Windows Event Log. Both are streams - they tell you what happened while Splunk
 was watching.

 They cannot tell you the current STATE. If a host had its firewall turned off
 before you deployed Splunk, no change event will ever be produced and the host
 simply looks quiet. Worse: a host with "Log dropped packets" disabled produces
 no traffic log at all, and is indistinguishable from a host with no network
 activity.

 This add-on closes that gap by inventorying the configuration itself.

--------------------------------------------------------------------------------
 WHAT IT COLLECTS
--------------------------------------------------------------------------------
 sourcetype = windows:firewall:profile   every 30 minutes, 3 events per host
   Profile state (Domain / Private / Public), default inbound and outbound
   actions, whether allowed and dropped packets are logged, log file path,
   size limit and whether the file actually exists - plus a compliance verdict
   and the list of findings.

 sourcetype = windows:firewall:rule      once a day, one event per enabled rule
   Every enabled rule flattened with its port, address and application filters,
   its policy source, and a risk score. Rules that allow inbound traffic from
   any address, on any port, with no application binding are flagged.

 Both scripts are READ ONLY. They call Get-NetFirewallProfile,
 Get-NetFirewallRule and the associated Get-NetFirewall*Filter cmdlets. They
 never create, modify or delete a rule or a setting.

--------------------------------------------------------------------------------
 WHY POWERSHELL CMDLETS AND NOT NETSH
--------------------------------------------------------------------------------
 The NetSecurity cmdlets return .NET objects whose property names are the same
 on every Windows installation. Collectors built on "netsh advfirewall show"
 parse localised console text: on a French, German or Japanese Windows the
 field labels change and the extraction silently returns nothing.

 This add-on is therefore language independent, which matters as soon as your
 estate is not uniformly English.

--------------------------------------------------------------------------------
 WHERE TO INSTALL IT
--------------------------------------------------------------------------------
 Short version: install the add-on on every tier that COLLECTS, PARSES or
 SEARCHES the data. Enable the inputs on ONE of them - the Windows forwarders.

   Component                      Install?   Enable inputs?
   ---------------------------------------------------------------------------
   Universal forwarder (Windows)    YES          YES
   Heavy forwarder (if any)         YES          no
   Indexer                          YES *        no
   Search head                      YES          no
   Deployment server                optional     no

   * Not needed on the indexers IF a heavy forwarder sits in front of them:
     whichever component parses first is the one that needs it.

 Why each tier needs it:

   * Forwarder - this is where the PowerShell scripts actually run. Without
     the inputs enabled here, nothing is ever collected.

   * Indexer or heavy forwarder - a universal forwarder does NOT parse. It
     reads and ships. The first parsing component downstream decides where an
     event starts and ends (LINE_BREAKER, SHOULD_LINEMERGE, TRUNCATE) and what
     its timestamp is (TIME_PREFIX, TIME_FORMAT). Skip this tier and a host's
     300 rule events may be merged into a handful of malformed ones.

   * Search head - the field extractions (KV_MODE), aliases and calculated
     fields run at search time. Skip this tier and the "Firewall Posture"
     dashboard of the main app finds raw text and no usable fields.


 TOPOLOGY A - one forwarder, one indexer (most common, and the simplest)
 ----------------------------------------------------------------------

   Windows host                     Splunk instance
   +----------------------+         +---------------------------+
   | Universal Forwarder  |  :9997  | Indexer                   |
   |                      |-------->| (also the search head on  |
   | TA installed         |         |  a standalone deployment) |
   | inputs ENABLED       |         | TA installed              |
   +----------------------+         | inputs left DISABLED      |
                                    +---------------------------+

   Two installations. The Splunk instance carries both the indexer role and
   the search head role, so a single install there covers both needs.


 TOPOLOGY B - a heavy forwarder in between
 -----------------------------------------

   UF (Windows)  -->  Heavy forwarder  -->  Indexers        Search head
   TA, inputs ON      TA, inputs off        TA NOT needed   TA, inputs off

   The heavy forwarder parses, so the indexers never see unparsed data and do
   not need the add-on.


 TOPOLOGY C - search head cluster
 --------------------------------

   Same as A or B, but push the add-on to the cluster members with the
   deployer rather than installing it by hand:

     splunk apply shcluster-bundle -target https://<member>:8089


 In every topology the inputs are enabled on the Windows forwarders and
 nowhere else. Enabling them on a Linux indexer is harmless - the PowerShell
 modular input does not exist there - but it is pointless noise.

 The add-on has no UI and creates no index.

--------------------------------------------------------------------------------
 INSTALLATION
--------------------------------------------------------------------------------
 0. Create the destination index first, on the indexers. The inputs fail
    silently if it does not exist.

      splunk add index windows_firewall

 1. ON THE INDEXER (and search head) - parsing and field extraction.

      splunk install app TA-windows-firewall-posture_<version>.tgz
      splunk restart

    If you ran that as root on Linux, fix the ownership afterwards, otherwise
    splunkd cannot write the files:

      chown -R splunk:splunk $SPLUNK_HOME/etc/apps/TA-windows-firewall-posture

    Leave the inputs alone here. They must stay disabled.

 2. ON THE WINDOWS FORWARDERS - collection.

    Extract the package into the apps directory:

      cd "C:\Program Files\SplunkUniversalForwarder\etc\apps"
      tar -xzf C:\temp\TA-windows-firewall-posture_<version>.tgz

    Then create local\inputs.conf inside the add-on to enable the inputs:

      [powershell://wfo_firewall_profiles]
      disabled = 0
      index = windows_firewall

      [powershell://wfo_firewall_rules]
      disabled = 0
      index = windows_firewall

    Set "index" to the one your search head declares in the
    `windows_firewall_index` macro of the main app. Then restart:

      net stop SplunkForwarder && net start SplunkForwarder

    For more than a couple of machines, push the add-on together with its
    local/ directory from a deployment server, and let the server class
    restart the forwarders.

 3. VERIFY, within 30 minutes.

      index=windows_firewall sourcetype=windows:firewall:profile | head 5
      | `wfo_posture_profiles` | stats count by Computer, profile

    Three events per host per run for the profiles. The rule inventory runs
    once a day at 03:17 - lower its schedule temporarily on a test machine if
    you do not want to wait.

    To test the collection script alone on any Windows machine, without Splunk:

      & "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows-firewall-posture\bin\wfo_get_firewall_profiles.ps1"

    You should get three key=value lines carrying compliant= and findings=.

--------------------------------------------------------------------------------
 REQUIREMENTS
--------------------------------------------------------------------------------
 * Windows 8.1 / Windows Server 2012 R2 or later - the NetSecurity PowerShell
   module, which provides Get-NetFirewallProfile and Get-NetFirewallRule.
 * PowerShell 3.0 or later, and .NET Framework 4.5 or later. Both are
   prerequisites of the Splunk powershell:// modular input itself.
 * The forwarder must run as Local System, which is both the Splunk
   requirement for PowerShell inputs and enough to read the firewall
   configuration.

 * POWERSHELL SCRIPT EXECUTION MUST BE PERMITTED.

   A LocalMachine execution policy of "Restricted" - the default on Windows
   client editions - blocks this add-on AND Splunk's own PowerShell harness
   (splunk-powershell.ps1, in $SPLUNK_HOME\bin). Symptom when running a script
   by hand:

     ... cannot be loaded because running scripts is disabled on this system.

   Windows Server defaults to RemoteSigned and is usually fine as shipped.

   Check which scope is in effect:

     Get-ExecutionPolicy -List

   Reading the result:
     * A scope set to Restricted or AllSigned is what blocks you.
     * MachinePolicy and UserPolicy come from Group Policy and CANNOT be
       overridden locally - take it to your Windows team.
     * ALL FIVE SCOPES "Undefined" does NOT mean nothing is blocking you. It
       means no policy is set, so the edition default applies: Restricted on
       Windows client editions, RemoteSigned on Windows Server. This is the
       most common case on a workstation, and the easiest to fix - no GPO is
       in the way.

   Confirm what is actually in force with the plain command:

     Get-ExecutionPolicy

   Set it to the usual minimum, per machine:

     Set-ExecutionPolicy RemoteSigned -Scope LocalMachine

   Or, preferably on a fleet, by Group Policy:

     Computer Configuration > Policies > Administrative Templates >
     Windows Components > Windows PowerShell > Turn on Script Execution >
     "Allow local scripts and remote signed scripts"

   RemoteSigned is sufficient. Unrestricted and Bypass are not required and
   weaken the machine.

   NOTE: this add-on deliberately does NOT attempt to bypass the execution
   policy - for instance by wrapping the scripts in a script:// input calling
   powershell.exe -ExecutionPolicy Bypass. Overriding a control the
   administrator has chosen is not an add-on's job. If your policy forbids
   PowerShell scripts, that is a decision to revisit with your Windows team,
   not something to work around from Splunk.

--------------------------------------------------------------------------------
 WHAT TO DO ABOUT THE FINDINGS
--------------------------------------------------------------------------------
 Profile findings (sourcetype windows:firewall:profile)

   firewall_disabled
     The profile is off. Turn it back on and find out who turned it off:
       Set-NetFirewallProfile -Name <Domain|Private|Public> -Enabled True

   default_inbound_allow
     Every unbound port of the host is reachable. Restore the safe default:
       Set-NetFirewallProfile -Name <profile> -DefaultInboundAction Block

   dropped_packets_not_logged
   allowed_connections_not_logged
   log_size_below_20mb
   log_file_missing
     The host produces no usable firewall traffic log, so it can never appear
     in the traffic dashboards of the main app. One command fixes all four:

       Set-NetFirewallProfile -All -LogAllowed True -LogBlocked True -LogMaxSizeKilobytes 20480 -LogFileName "%systemroot%\system32\LogFiles\Firewall\pfirewall.log"

     One line on purpose: backtick continuations do not always survive a copy
     and paste into a console. Run it from an elevated PowerShell. If the log
     path is already correct, -LogFileName can be omitted.

     log_file_missing clears itself as soon as the first packet is filtered
     and the file is created - usually within seconds.

     Note: allowed_connections_not_logged is reported because this add-on
     judges observability posture as much as security posture. Logging allowed
     connections is voluminous, and some organisations disable it deliberately
     on chatty servers. If that is a considered decision in your environment,
     remove the corresponding line from bin/wfo_get_firewall_profiles.ps1 so
     it stops counting against the compliance verdict.

 Rule findings (sourcetype windows:firewall:rule)

   inbound_allow_any_source          the rule accepts any remote address
   inbound_allow_any_port            the rule accepts any local port
   inbound_allow_no_application      the rule is not bound to a program
   inbound_allow_any_any_any         all three at once - the worst shape
   administrative_port_open_to_any   RDP, SMB, SSH, WinRM or a database port
                                     reachable from any address

     Narrow the rule rather than deleting it, so you keep the service working:
       Set-NetFirewallRule -Name <id> -RemoteAddress <CIDR list>
       Set-NetFirewallRule -Name <id> -Program "<full path>"

     Check the policy_source field first. A rule pushed by Group Policy must
     be fixed in the GPO, not on the machine - a local change is overwritten
     at the next refresh.

--------------------------------------------------------------------------------
 TROUBLESHOOTING
--------------------------------------------------------------------------------
 No events at all, on any host
   * Does the destination index exist on the indexers? The inputs fail
     silently otherwise.  splunk add index windows_firewall
   * Are the inputs actually enabled? They ship disabled.
     splunk btool inputs list --debug | findstr wfo_firewall
   * Execution policy - see REQUIREMENTS above. Check splunkd.log on the
     forwarder for "running scripts is disabled on this system".

 Events arrive but carry no fields
   The add-on is missing on the search head, or on the indexer. Field
   extraction (KV_MODE, aliases, EVALs) happens at search time on the search
   head; line breaking and timestamping happen at index time on the first
   parsing tier. See WHERE TO INSTALL IT.

 Several rules merged into one event
   The add-on is missing on the indexer, or on the heavy forwarder in front of
   it, so LINE_BREAKER never applied.

 Rule events look cut off, no severity field
   TRUNCATE is too low for a rule carrying a very long address or port list.
   The default in this add-on is 25000; raise it in local/props.conf if your
   GPO rules are unusually large.

 Test a script by hand without changing the machine policy
   powershell.exe -ExecutionPolicy Bypass -NoProfile -File "<path>\bin\wfo_get_firewall_profiles.ps1"

 Scripts blocked as "downloaded from the internet"
   Get-ChildItem "<path>\bin\*.ps1" | Unblock-File

--------------------------------------------------------------------------------
 SIZING
--------------------------------------------------------------------------------
 Profiles : 3 events x 48 runs per day  = ~144 events/host/day, a few hundred KB
            per host per month.
 Rules    : 200-400 events once a day. Raise the schedule interval, or set
            $OnlyEnabled = $false in the script only if you really need the
            full inventory including disabled rules.

--------------------------------------------------------------------------------
 RELATED ADD-ONS
--------------------------------------------------------------------------------
 Windows Firewall Status Check Add-on (Splunkbase 7012) collects the on/off
 state of the three profiles through netsh. If that is all you need, it is a
 lighter option. This add-on additionally collects the default actions, the
 logging configuration, the log file health and the rule inventory - which is
 what the "Firewall Posture" dashboard and the "Host Not Logging Dropped
 Packets" detection are built on.

--------------------------------------------------------------------------------
 RELEASE NOTES
--------------------------------------------------------------------------------
 1.0.3
   * README: "Where to install it" section with a per-component table and the
     three common topologies. Execution policy documented as a prerequisite,
     including how to read an all-Undefined Get-ExecutionPolicy -List result.
     New "What to do about the findings" section mapping every finding to its
     remediation. New troubleshooting section.
   * Collection scripts validated against real Windows hosts, in addition to
     the mocked-cmdlet test suite.

 1.0.2
   * TRUNCATE raised to 25000 on windows:firewall:rule. The previous value
     (8000) was below the Splunk default of 10000, and the risk scoring fields
     are written at the end of the event - a long RemoteAddress list on a GPO
     rule could silently drop them.

 1.0.1
   * Both inputs now ship disabled by default. Enable them explicitly in
     local/inputs.conf - see INSTALLATION.
   * README: topology section, rationale for the cmdlet based collection,
     comparison with related add-ons.

 1.0.0
   * Initial release: profile posture and rule inventory collection.

--------------------------------------------------------------------------------
 LICENSE
--------------------------------------------------------------------------------
 Refer to https://www.splunk.com/en_us/legal/splunk-general-terms.html
