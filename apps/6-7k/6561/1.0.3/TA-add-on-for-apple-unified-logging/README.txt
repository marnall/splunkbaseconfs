This is an add-on is designed for CIM mapping between MacOS unified logging output and following datamodels:
- Authentication
- Endpoint (Processes)


To gather the logs from MacOS operting systems, install Splunk Universal Forwarder 9.0.0+ to MacOS endpoints. 

Example inputs.conf document:

[logd]
interval = 30
logd-exclude-fields=formatString,timestamp,timezoneName

[logd://SplunkSecurity]
interval = 30
logd-predicate =  ((process == "sshd" and (eventMessage contains "PAM" or eventMessage contains "keyboard-interactive/pam" or eventMessage contains "disconnected")) OR (process beginswith "su" and eventMessage contains "tty") OR (processImagePath contains "loginwindow" and eventMessage contains "SessionAgentNotificationCenter" and (eventMessage contains "com.apple.sessionagent.screenIs" or eventMessage contains "com.apple.fastUserSwitchBegin" or eventMessage contains "com.apple.system.loginwindow.shutdownInitiated" or eventMessage contains "com.apple.system.loginwindow.logoutcancelled" or eventMessage contains "com.apple.system.loginwindow.restartinitiated" or eventMessage contains "com.apple.sessionDidLogin" )) OR (process == "pppd") OR (process == "logind" and eventMessage contains "SessionAgent for") OR (process == "screensharingd" and eventMessage contains "Authentication:") OR (processImagePath CONTAINS[c] "backupd" && eventMessage CONTAINS[c] "backup") OR (subsystem == "com.apple.opendirectoryd" and eventMessage CONTAINS "Password changed for") OR (subsystem == "com.apple.loginwindow.logging" and eventMessage CONTAINS "LWAccountTracking handleUserListChangeNotification") OR (process == "loginwindow" and eventMessage LIKE[c] "*AccountTrackingCommon doAccountsScanWithSearchNode*local account names*") OR (processImagePath contains "sharingd" and subsystem contains "com.apple.sharing" and (eventMessage contains "New incoming transfer" or eventMessage contains "User response updated" or eventMessage contains "Progress for transfer" or eventMessage contains "startSending")) OR (process == "coreauthd" and subsystem == "com.apple.BiometricKit" and eventMessage contains "BKMatchOperation::matchResult:withDictionary:") or (process == "opendirectoryd" and (eventMessage contains "Failed kerberos password verification" or eventMessage contains "Successful kerberos password verification")) OR (process == "apsd" and eventMessage contains "Changing status for uid") OR (process == "authorizationhost" and eventMessage contains "Failed to authenticate user") OR (process == "kernel" and eventMessage LIKE[c] "*mounted*on device*") OR (process == "deleted" and eventMessage contains "Disk mounted at") )
logd-backtrace = true
logd-debug = true
logd-info = true
logd-loss = no
logd-signpost = yes
logd-exclude-fields = bootUUID, timestamp, formatString
index=macOS

[logd://SplunkProcesses]
interval = 30
#logd-predicate =  (subsystem == "com.apple.launchservices" and (eventMessage contains "LaunchedApplication" or eventMessage contains "Opening URL" or eventMessage LIKE[c] "*LAUNCH: Application*launched with pid*, starting the application.*"))
logd-predicate =  ((subsystem == "com.apple.launchservices" and eventMessage beginswith "NotifyAboutLaunchedApplication") or (subsystem == "com.apple.CommCenter" and eventMessage contains "handleLSNotitifcation_sync: Application"))
logd-backtrace = true
logd-debug = true
logd-info = true
logd-loss = no
logd-signpost = yes
logd-exclude-fields = bootUUID, timestamp, formatString
index=macOS

[logd://SplunkNetworkState]
interval = 30
logd-predicate =  (subsystem == "com.apple.CoreUtils" and process == "rapportd" and (eventMessage contains "PrimaryIP changed" or eventMessage contains "SysMon: WiFi state" or eventMessage contains "SysMon: WiFi SSID" or eventMessage contains "SysMon: WiFi join"))
logd-backtrace = true
logd-debug = true
logd-info = true
logd-loss = no
logd-signpost = yes
logd-exclude-fields = bootUUID, timestamp, formatString
index=macOS

[logd://SplunkSandboxBreakouts]
interval = 30
logd-predicate =  (senderImagePath contains "Sandbox" and messageType == 16 and (eventMessage LIKE[c] "*deny(*file-read-data*" or eventMessage LIKE[c] "*deny(*file-write-data*"))
logd-backtrace = true
logd-debug = true
logd-info = true
logd-loss = no
logd-signpost = yes
logd-exclude-fields = bootUUID, timestamp, formatString
index=macOS




# Binary File Declaration
# Binary File Declaration
