   About

   Visualize hidden Cisco WSA statistics

   The advanced logging app for Cisco WSA redefines monitoring and troubleshooting by aggregating diverse logs from Cisco WSA devices. A standout feature is its unparalleled ability to parse and
   visualize the typically concealed prox_track log, unconfigurable through the GUI. Positioned as both a replacement for and a valuable addition to traditional SNMP-based monitoring, this app
   excels across various crucial areas:

  Overview:

   Comprehensive display of all WSA proxies with current and peak values. Metrics include requests per second, CPU/RAM/Disk load, and server/client connections.

  Timings and Load Values:

   In-depth insights into various timings and load values for Authentication, DNS, and other essential modules.

  Comparative Analysis:

   Unique functionality to not only display values but also facilitate the comparison of metrics between different systems.

  Internal Visibility:

   Leveraging track_stats/prox_track.log, the app provides a profound view into the internal workings of WSA.

  Correlation Graphs:

   Build correlation graphs illustrating the relationship between requests per second and system load, enabling the identification of potential bottlenecks.

  Audit View:

   A dedicated audit view to track user logins and monitor system changes, ensuring a comprehensive understanding of system activity.

  Installation and configuration

     * Install Splunk Enterprise.
     * Install this App.
     * On Splunk: configure UDP or TCP input on a port of your choice and map it to the sourcetype cisco:wsa:systemlogs.
     * On WSA: configure Syslog push for specific log types (see below).
     * Configure prox_track retrieval (see below).
     * If events are stored in non default index: modify following macros: cisco_wsa_shd_index_and_sourcetype, cisco_wsa_prox_track_index_and_sourcetype, cisco_wsa_system_logs_index_and_sourcetype.

  Ad-hoc Analysis

   Instead of continious retrieval, you can just upload logs on demand:

     * On Splunk: App > Cisco WSA Insight, then Settings > Add Data > Upload files from my computer > Select File > Next
     * choose a sourcetype:

          * prox_track: cisco:wsa:prox_track
          * SHD Log: cisco:wsa:shd
          * any other log: cisco:wsa:systemlogs

     * Next, type in the host name of original wsa host, Review, Submit.

  Sourcetypes

   +------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
   |           Log            |           Source            |          Sourcetype           |     Retrieval Method      |                              Comment/Example                              |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   |                          |                             |                               |                           | Multiline (~1300 lines/event)                                             |
   |                          |                             |                               |                           |                                                                           |
   |                          |                             |                               |                           |                   user time: 0.120 (0.040%)                               |
   | track_stats              | /track_stats/prox_track.log | cisco:wsa:prox_track          | ftp/scp pull + script for |                 system time: 0.179 (0.060%)                               |
   |                          |                             |                               | cont. monitoring          |       max resident set size: 0                                            |
   |                          |                             |                               |                           | integral sh'd text mem size: 104528                                       |
   |                          |                             |                               |                           | integral unshared data size: 1739940                                      |
   |                          |                             |                               |                           |integral unshared stack size: 6016                                         |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | System Health Logs / SHD | shd_logs                    | cisco:wsa:shd (extracted from | syslog/ftp/scp            | CPULd 14.1 DskUtil 7.9 RAMUtil 13.2 Reqs 0 Band 0 Latency 0 CacheHit 0    |
   | Logs                     |                             | cisco:wsa:systemlogs)         |                           | CliConn 0 SrvConn 0 MemBuf 0 SwpPgOut 534462                              |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | Audit Logs               | audit_log                   | cisco:wsa:systemlogs          | syslog/ftp/scp            | Interaction Mode: GUI, User: admin, Source IP: l0.1.1.0, Destination IP:  |
   |                          |                             |                               |                           | l0.2.2.2, Location: /login, Event: Successful Login                       |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | CLI Logs                 | cli                         | cisco:wsa:systemlogs          | syslog/ftp/scp            | User admin login from l0.1.1.2 on l0.2.2.2 User admin entered             |
   |                          |                             |                               |                           | 'alertconfig'                                                             |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | GUI Logs                 | gui                         | cisco:wsa:systemlogs          | syslog/ftp/scp            | req:10.1.1.1 user:admin 200 POST                                          |
   |                          |                             |                               |                           | /system_administration/access/network_access HTTP/1.1 Mozilla/5.0         |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | Default Proxy Logs       | proxyerrlog                 | cisco:wsa:systemlogs          | syslog/ftp/scp            | Warning: CONFIG Redirect hostname configuration error                     |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | Status Logs              | status                      | cisco:wsa:systemlogs          | syslog/ftp/scp            | ??                                                                        |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | System Logs              | system                      | cisco:wsa:systemlogs          | syslog/ftp/scp            | User admin commit changes                                                 |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | Authentication Framework | authlog                     | cisco:wsa:systemlogs          | ftp/scp                   | ??                                                                        |
   | Logs                     |                             |                               |                           |                                                                           |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | HTTPS Logs               | httpslog                    | cisco:wsa:systemlogs          | ftp/scp                   | ?? client cert ??                                                         |
   |--------------------------+-----------------------------+-------------------------------+---------------------------+---------------------------------------------------------------------------|
   | Http2 proxy Logs         | http2log                    | cisco:wsa:systemlogs          | ftp/scp                   | ??                                                                        |
   +------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  How to get logs in Splunk?

     * For track_stats logs - use provided script (see below).
     * For logs that support Syslog: UDP/TCP for realtime collection. Alternatively, log pushing.
     * For Splunk UDP input implement suggestions from "Tuning UDP Syslog data" section below.
     * For logs that don't support Syslog - use log pushing. Alternatively, write a script to pull the logs, but it should avoid ingesting duplicate events.
     * For Syslog use the maximum message size (9216 for UDP, 65535 for TCP).
     * Avoid sending access log to the same port as system logs - use a syslog or SC4S server instead.
     * Store the access log in a distinct index from system logs to enhance performance.
     * Splunk can accept syslog data directly, but for high volume traffic it is better to place a syslog server inbetween.

  Compatibility

   This app should work with Splunk 7/8/9 on Windows and Linux platforms.

  Host extraction

   It is important that Splunk recognize WSA either by hostname, FQDN or IP address consistently. If you choose FQDN then it should work for both cisco:wsa:prox_track and cisco:wsa:systemlogs.

     * If Splunk can resolve WSA address (reverse DNS):

          * use "set host - DNS" in the Data inputs > TCP/UDP
          * For track_stats use FQDN for cron script

     * If Splunk cannot resolve WSA address:

          * Modifying hosts file will help for track_stats but not for syslog input.
          * For syslog retrieval the host can be extracted from the syslog header:

            props.conf:

 [cisco:wsa:systemlogs]
 TRANSFORMS-extract_host_from_syslog_header = extract_host_from_syslog_header

            transforms.conf:

 [extract_host_from_syslog_header]
 # Jan 31 18:59:48 wsa.example.com shd_syslog: Info:
 # <14>Jan 31 18:59:48 wsa.example.com shd_syslog: Info:
 # Jan 31 22:56:24 10.20.30.40 Jan 31 22:56:05 wsa.example.com shd_syslog: Info:
 REGEX = ^.{0,50}[A-Z][a-z][a-z]\s\s?\d\d?\s\d\d:\d\d:\d\d\s(\S+)\s\S+:\s[A-Z][a-z]+:
 FORMAT = host::$1
 DEST_KEY = MetaData:Host

  Tuning UDP Syslog data

   To improve readability you can add following stanza to the udp input definition in inputs.conf to remove redundant data received via UDP:

 # Make sure the prio syslog field is removed:
 # Whether or not the input strips <priority> syslog fields from events it receives over the syslog input.
 # A value of "true" means the instance does NOT strip the <priority> syslog field from received events.
 # NOTE: Do NOT set this setting if you want to strip <priority>.
 # Default: false
 # This will change "<14>Jan 31 18:59:48 wsa.example.com" to "Jan 31 18:59:48 wsa.example.com"
 no_priority_stripping = false

 # Make sure Splunk doesn't add a second timestamp
 # Whether or not to append a timestamp and host to received events.
 # A value of "true" means the instance does NOT append a timestamp and host to received events.
 # NOTE: Do NOT set this setting if you want to append timestamp and host to received events.
 # Default: false
 # This will change "14 Jan 31 18:59:48 10.20.30.40 Jan 31 18:59:48 wsa.example.com" to "Jan 31 18:59:48 wsa.example.com"
 no_appending_timestamp = true

  Log pushing

   Log pushing is a robust yet non-realtime log transfer method. Certain log types, such as https_logs and authlogs logs, do not support Syslog, therefore, log pushing is the only available method
   for them.

     * Configure FTP or SSH server on the receiver server.
     * On the receiving SSH server: make sure ~/.ssh and ~/.ssh/authorized_keys have correct permissions:

 chmod 700 ~/.ssh
 chmod 600 ~/.ssh/authorized_keys

     * On WSA: Configure log retreival method: set a Rollover by Time - e.g. 2m for initial testing and 2h for production. As directory use e.g. /wsa_logs/wsa.example.com/ (replace log name as
       needed. Make sure the folder exists and has right owndership and permissions). For SCP transfer, after you click Submit, you'll get a message to place the following SSH key(s) into your
       authorized_keys file on the remote (receiver) host. Commit changes.
     * On the receiving server: configure autodeletion using a cron job, (replace log name as needed):

 */10 * * * * find /wsa_logs/wsa.example.com/authlog* -type f -mmin +60 -delete

     * Configure Splunk input (modify as needed):

 [monitor:///wsa_logs/*/authlog*]
 disabled = false
 host_segment = 2
 sourcetype = cisco:wsa:systemlogs

  Retrieving track_stats/prox_track.log

    On linux

   Warning: avoid running this script as root user.

     * Create a folder to create prox_track.log: mkdir /wsa_logs
     * Create a script get_prox_track.sh in this folder (modify USER and DIR variables as needed):

 #!/bin/bash
 USER=getlog
 WSA_HOST=$1
 DIR=/wsa_logs/

 # check if the script with same parameters (user+host) is already running
 pgrep -a ssh | grep $USER  | grep $WSA_HOST         | grep -q prox_track.log
 if [ $? -eq 0 ]; then
   exit
 fi

 if [ ! -d $DIR/$WSA_HOST ]; then mkdir $DIR/$WSA_HOST ; fi
 cd $DIR/$WSA_HOST
 timestamp=$(date +%s)
 if [ ! -f timestamp.txt ]; then touch timestamp.txt ; fi
 scp $USER@$WSA_HOST:/track_stats/prox_track.log $timestamp
 grep -A1000000 -f timestamp.txt $timestamp | grep -A1000000 -P "^\s+ user time: " | grep -A1000000 -E "^Current Date: " | grep -E -f ../patterns.txt > prox_track.log
 grep "^Current Date:" $timestamp | tail -1 > timestamp.txt
 rm -f $timestamp
 find $DIR/$WSA_HOST -type f -name "1[78][0-9]*" -mtime +1 -delete # clean up old timestamp files

     * Add an executable bit: chmod +x get_prox_track.sh
     * To allow passwordless login for the script:

          * On each WSA: create a restricted user using CLI or GUI. User Type: Operator
          * On linux: create (if not yet exist) SSH keys using ssh-keygen command
          * On each WSA using CLI: add (if not already exists) a SSH public key from the linux: sshconfig > userkey > user > [username] > new
          * On linux: to confirm the passwordless login is working try for each WSA (replace username and wsa as needed): scp username@wsa:/track_stats/prox_track.log /dev/null. At the first run
            you'll get a confirmation prompt, type yes to confirm.
          * On linux: in the folder that you just created (e.g. /wsa_logs), place a file patterns.txt with following content:

 ^Current Date:
 ^INFO: proxy running for
 ^INFO: traffic over
 ^INFO: Transparent NTLMSSP
 ^INFO: Basic Auth
 ^INFO: Negotiate Auth
 ^INFO: AuthCache: Capacity
 ^INFO: DNS Cache Stats:
 weightavg
 user time:
 system time:
 block input operations:
 block output operations:
 DNS Time
 Auth Helper Service Time
 Auth Helper Wait Time
 WBRS Wait Time
 WBRS Service Time
 Server Transaction Time
 Server Wait Time
 Client Time
 page faults:
 involuntary context switches

          * On linux: the folder structure:

 /wsa_logs/
 ├── get_prox_track.sh
 └─── patterns.txt

          * On linux: to check if the script run: /wsa_logs/get_prox_track.sh wsa2.example.local against every WSA host (replace the hostname as needed).
          * After the first run a destination folder for each WSA will be created with a timestamp.txt file inside of it. No log file will be saved on the first run - it appears on a second run
            5-10 minutes after.
          * On linux: the folder structure after successful setup and second run:

 /wsa_logs/
 ├── get_prox_track.sh
 ├── patterns.txt
 ├── wsa1.example.local
 │   ├── prox_track.log
 │   └── timestamp.txt
 ├── wsa2.example.local
 │   ├── prox_track.log
 │   └── timestamp.txt
 ├── wsa3.example.local
 │   ├── prox_track.log
 │   └── timestamp.txt
 └── wsa4.example.local
     ├── prox_track.log
     └── timestamp.txt

          * On linux: create crontab for each WSA (replace wsa1.example.com and wsa2.example.com with FQDNs of WSAs):

 * * * * * /wsa_logs/get_prox_track.sh wsa1.example.local &>/dev/null
 * * * * * /wsa_logs/get_prox_track.sh wsa2.example.local &>/dev/null
 * * * * * /wsa_logs/get_prox_track.sh wsa3.example.local &>/dev/null
 * * * * * /wsa_logs/get_prox_track.sh wsa4.example.local &>/dev/null

          * On linux: create a splunk monitor configuration using GUI or CLI:

 [monitor:///wsa_logs/*/prox_track.log]
 disabled = false
 host_segment = 2
 sourcetype = cisco:wsa:prox_track

          * Attention: No log file will be saved on the first run - it appears on a second run 5-10 minutes after.

    On Windows

   WARNING: Running on Windows not fully supported yet, use on your own risk.
   To run a script to get prox_track logs on Windows (including Windows Service Core) follow these steps:

     * Create a WSA user with "Operator" or "Administrator" role.
     * Create a public/private key pair using PuttyGen and upload a public key to WSA (sshconfig > userkey > user > new).
     * On Windows: create a c:\wsa_logs folder
     * Download cygwin files (https://www.cygwin.com/install.html) without installing using CLI: setup-x86_64.exe --no-admin -D -d -n -N -X -v -l c:\cygwin
     * Copy following executables from c:\cygwin in c:\wsa_logs folder:

 bash.exe
 cygiconv-2.dll
 cygintl-8.dll
 cygncursesw-10.dll
 cygpcre-1.dll
 cygreadline7.dll
 cygstdc++-6.dll
 cygwin1.dll
 date.exe
 grep.exe
 mkdir.exe
 rm.exe
 tail.exe
 touch.exe

       Alternatively, you can just install cygwin.
     * Additionally, put psexec64.exe (https://docs.microsoft.com/en-us/sysinternals/downloads/psexec), pscp.exe (https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) and patterns.txt
       from above in c:\wsa_logs.
     * Put this script as getlog.sh in c:\wsa_logs (this script differs slightly from the script above):

 #!/bin/bash
 WSA_HOST=$1
 DIR=c:/wsa_logs/
 PATH=.:..
 if [ ! -d $DIR/$WSA_HOST ]; then mkdir $DIR/$WSA_HOST ; fi
 cd $DIR/$WSA_HOST
 timestamp=$(date +%s)
 if [ ! -f timestamp.txt ]; then touch timestamp.txt ; fi
 pscp -P 22 -i ../priv.ppk getlog@$WSA_HOST:/track_stats/prox_track.log $timestamp
 ../grep -A1000000 -f timestamp.txt $timestamp | ../grep -A1000000 -P "^\s+ user time: " | ../grep -A1000000 -E "^Current Date: " | ../grep -E -f ../patterns.txt > prox_track.log
 ../grep "^Current Date:" $timestamp | ../tail -1 > timestamp.txt
 rm -f $timestamp

     * Put following file in c:\wsa_logs (name it schedule.xml, replace WSANAME with a hostname of each WSA):



         2022-05-18T16:35:41
         PavelP
         get WSANAME prox_track.log



           S-1-5-18



         true
         true
         IgnoreNew

           PT10M
           PT1H
           true
           false




           2022-05-18T16:35:00

             PT2M





           c:\wsa_logs\bash.exe
           c:\wsa_logs\getlog.sh WSANAME > c:\wsa_logs\WSANAME.log
           c:\wsa_logs\


     ]]>

     * Start cmd.exe as a system user (other options are local service or network service): PsExec64.exe -u "nt authority\system" -i -s cmd
     * In new cmd window run a script manually once to accept pscp prompt:

 C:\wsa_logs>c:\wsa_logs\bash.exe c:\wsa_logs\getlog.sh WSANAME
     The server's host key is not cached in the registry. If you trust this host, enter "y" to add the key to PuTTY's cache and carry on connecting.
     Store key in cache? (y/n)

       The previous two steps can be skipped by copying HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\SshHostKeys to HKEY_USERS\S-1-5-18
     * After the first run a destination folder for each WSA will be created with a timestamp.txt file inside of it. No log file will be saved on the first run - it appears on a second run 5-10
       minutes after.
     * Create a Scheduled Tasks using a provided XML file:

 C:\wsa_logs>schtasks /create /tn WSANAME /xml scheduler.xml
       SUCCESS: The scheduled task "WSANAME" has successfully been created.

     * Check a status of the task: C:\wsa_logs>schtasks /query /tn WSANAME /v /fo list
     * A final structure of c:\wsa_logs after a successful run:

 C:\wsa_logs
     │   bash.exe
     │   cygiconv-2.dll
     │   cygintl-8.dll
     │   cygncursesw-10.dll
     │   cygpcre-1.dll
     │   cygreadline7.dll
     │   cygstdc++-6.dll
     │   cygwin1.dll
     │   date.exe
     │   getlog.sh
     │   grep.exe
     │   mkdir.exe
     │   patterns.txt
     │   priv.ppk
     │   pscp.exe
     │   PsExec64.exe
     │   rm.exe
     │   schedule.xml
     │   tail.exe
     │   touch.exe
     │
     ├───wsa1.example.local
     │       prox_track.log
     │       timestamp.txt
     │
     └───wsa2.example.local
             prox_track.log
             timestamp.txt

  Troubleshooting

     * Are events coming in?
     * Are events in the right index?
     * Do events have right sourcetype?
     * Are events parsed correctly?
     * Use the "Log Check" view.
     * Write an email to splunk@compek.net to get assistance.

  Version History

     * 0.0.11 - added Audit-Timeline view, support for audit, cli, gui, proxyerr, system and status logs.
     * 0.0.10 - added options to adjust visualization modes (switch area/line, disable stacked mode, linear/logarithmic)
     * 0.0.9 - moved Swap statistics in a separate panel (SHD* > Swap) for better visibility
     * 0.0.8 - applied required changes to keep compatibility with Splunk Cloud (use jquery 3.5)
     * 0.0.7 - added CPU load over Requests charts
     * 0.0.6 - added uptime info, CPU and RAM views
     * 0.0.5 - added connections view
     * 0.0.4 - improved visualizations
     * 0.0.3 - added host overview
     * 0.0.2 - added multihost compare views
     * 0.0.1 - first public release (beta)

   Contact: splunk@compek.net
