# =====================================================
#           Application configuration file
# =====================================================

[Logging]

TYPE = <string>
* Specify where to log messages sent from SOAP API CALL.
* Must be "syslog" or "file"
* Default: file


SYSLOG_FAC = <string>
* Syslog facility
* A valid syslog facility could be set:
  – auth (LOG_AUTH): for security/authorization events
  – authpriv ( LOG_AUTHPRIV): for security/authorization events, usually related to privilege escalation
  – cron (LOG_CRON): cron events
  – daemon (LOG_DAEMON): system daemon events
  – ftp (LOG_FTP): ftp service events
  – kern (LOG_KERN): UNIX/Linux kernel messages
  – syslog (LOG_SYSLOG): syslog internal messages
  – user (LOG_USER): user messages
  – local0–local7 (LOG_LOCAL[0-7]): eight facilities (local0 to local7) reserved for user-specified applications
* Default: syslog

LOG_LEVEL = <string>
* Minimum Log Level:
  – DEBUG: detailed and often verbose information, typically for debugging problems
  – INFO: expected messages, usually confirming things are working as expected
  – WARNING: indicates something unexpected happened but the app should be able to continue working
  – ERROR: more serious issues and will interfere with the application’s operation
  – CRITICAL: serious errors and implies the program itself may be unable to continue
* Suggested: DEBUG or INFO
* Default: DEBUG

SYSLOG_SOCKET = <string>
* Syslog socket
* Default: /dev/log

LOGFILE_NAME = <string>
* If you choose to log directly to a file, this is the file name.
  You have also to set TYPE = file.
  The path of the file will be "SPLUNK_HOME/var/log/splunk"
* Default: name2info.log

LOGSTDOUT = <boolean>
* Log messages to stdout too. Pretty useless in most situations.
* Default: false


# Setting for SOAP API CALL
[Soap]
adminUrl = <string>
* The Zimbra admin url.
  Something like https://zimbra.example.com:9071/service/admin/soap
* Default: none

admin = <string>
* The Zimbra Admin User
* Default: admin

pwd = <string>
* The password of the Zimbra Admin User.
* Default: none

NullStr = <string>
* What return if lookups or command  call fails or returns nothing.
* Sometime an empty string slows subsearch.
Default: 'void'


# Setting for GetAccountRequest in name2info command.
[Account]
Attributes = <string>
* name2info attributes to return.
  Pay attention: all attributes must exist.
  Keep in mind that the special Account attributes
  'zimbraMailSize' and 'zimbraMailboxId' are always returned
  and they must not be listed here.
* Separate each attribute name with a comma. You can write
  multiline for better reading:
    Attributes = zimbraId,\
      zimbraMailHost,\
      zimbraSieveRejectMailEnabled
* Allowed values:
     zimbraId
     zimbraMailHost
     zimbraSieveRejectMailEnabled
     zimbraMailQuota
     zimbraQuotaWarnPercent
     zimbraQuotaWarnInterval
     givenName
     sn
     mail
     zimbraAccountStatus
     zimbraMailStatus
     zimbraFeatureConversationsEnabled
     zimbraPrefSentMailFolder
     zimbraMailTrashLifetime
     zimbraMailSpamLifetime
     zimbraMailSieveScript
     zimbraSharedItem
     zimbraFeatureMailForwardingEnabled
     zimbraFeatureMailForwardingInFiltersEnabled
  and any other returned by GetAccountRequest.
* Default: all the above allowed values


# Setting for GetDistributionListRequest in name2info command.
[MailingList]
Attributes = <string>
* name2info attributes to return.
  Pay attention: all attributes must exist.
* Separate each attribute name with a comma. You can write
  multiline for better reading:
    Attributes = zimbraMailAlias,\
      zimbraHideInGal,\
      mail
* Allowed values:
     zimbraMailAlias
     zimbraHideInGal
     mail
     displayName
     zimbraMailHost
     zimbraDistributionListSendShareMessageToNewMembers
     cn
     zimbraMailStatus
     uid
     zimbraId
     zimbraCreateTimestamp
* Default: all the above allowed values
