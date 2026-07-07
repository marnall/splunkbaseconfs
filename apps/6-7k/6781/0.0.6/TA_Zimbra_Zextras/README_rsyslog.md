## Rsyslog Server aggregation

A simple setup requires a central syslog server aggregation which is local to the Splunk installation.
As a requirement you have your multiserver Zimbra installation done.

As an example, we suppose that the central syslog server aggregation is an [Rsyslog server](https://www.rsyslog.com/) receiving remote events through [RELP](https://en.wikipedia.org/wiki/Reliable_Event_Logging_Protocol) protocol.

The central Rsyslog server has the IP 10.10.0.0, and the zimbra servers are in the net 10.20.0.0/24.


### Zimbra servers setup
On each Zimbra server create a _/etc/rsyslog.d/70-external.conf_ which contains:

```
if ( ( $syslogfacility-text == 'auth' or $syslogfacility-text == 'local0' or $syslogfacility-text == 'local1' or $syslogfacility-text == 'local7' or $syslogfacility-text == 'mail' ) and
     $programname != 'ldapsearch' and
     $programname != 'sshd' and
     $programname != 'su' and
     $programname != 'systemd-logind' and
     $programname != 'zimbramon' )
then {
        action( type="omrelp"
                name="zimbraQueue"
                target="10.10.0.0"
                port="4321"
                queue.filename="zimbralog"
                queue.type="LinkedList"
                queue.saveonshutdown="on"
                queue.maxdiskspace="1g"
                action.resumeRetryCount="-1" )
}
```

If you like you can create a fs _/var/spool/rsyslog_ of at least 1 GiB space. Adjust the real size you can reserve for the queue in the `queue.maxdiskspace` value.

Install the RELP module. It depends on your OS. There are pre-built packages for RPM and Debian/Ubuntu. See at the Rsyslog web site for more details.

In _rsyslog.conf_ add the output module for RELP:

```
module(load="omrelp")
```

On the mailbox servers send the non syslog server to syslog.
The *log4j.properties* should contains

```
#Appender SYSLOG AUDIT
appender.SAUDIT.type = Syslog
appender.SAUDIT.name = auditSyslog
appender.SAUDIT.host = localhost
appender.SAUDIT.port = 514
appender.SAUDIT.protocol = UDP
appender.SAUDIT.layout.type = PatternLayout
appender.SAUDIT.layout.pattern = <190>${hostName} audit: %-5p [%t] [%z] %c{1} - %m%n

#Appender SYSLOG MAILBOX
appender.SMAILBOX.type = Syslog
appender.SMAILBOX.name = mailboxSyslog
appender.SMAILBOX.host = localhost
appender.SMAILBOX.port = 514
appender.SMAILBOX.protocol = UDP
appender.SMAILBOX.layout.type = PatternLayout
appender.SMAILBOX.layout.pattern = <190>${hostName} mailbox: %-5p [%t] [%z] %c{1} - %m%n

#Appender SYSLOG SYNC ( Mobile )
appender.SSYNC.type = Syslog
appender.SSYNC.name = syncSyslog
appender.SSYNC.host = localhost
appender.SSYNC.port = 514
appender.SSYNC.protocol = UDP
appender.SSYNC.layout.type = PatternLayout
appender.SSYNC.layout.pattern = <190>${hostName} sync: %-5p [%t] [%z] %c{1} - %m%n
```

Adjust the _log4j.properties.in_ accordingly.

Note that the Zimbra installation add copy of syslog to another zimbra admin server and maybe a local copy too. The setup described here doesn't affect this Zimbra configuration.


### Splunk Server Setup
On the Splunk host we describe the installation and configuration or the Rsyslog server aggregator.

First, install the Rsyslog with RELP module. This installation depends on your OS. There are pre-built packages for RPM and Debian/Ubuntu. See at the Rsyslog web site for more details.

In _rsyslog.conf_ add the **imrelp** module:

```
module(load="imrelp")
input(  type="imrelp"
        port="4321" )
```

It's advisable to increase the max message size. Java log could produce large events:

```
global(
        workDirectory="/var/spool/rsyslog"
        maxMessageSize="32k"
)
```

This must be done also on Zimbra servers too.

Add the following _/etc/rsyslog.d/zimbra.conf_:
```
# Default file for Zimbra logs
set $.logfile = "zimbra.log";

# Rule Path
template(name="LogSavePath" type="list") {
    constant(value="/var/log/zimbra/")
    property(name="$.logfile" )
}


# Log MTA log
if (
        ( $inputname == 'imrelp' )  and $hostname startswith "<prefix of outer mta servers hostname>" ) then {
        action(
                type="omfile"
                fileOwner="splunk"
                fileGroup="splunk"
                file="/var/log/zimbra/mtaout.log"
        )
        stop
}

if (
        ( $inputname == 'imrelp' )  and $hostname startswith "<prefix of inbound mta servers hostname>" ) then {
        action(
                type="omfile"
                fileOwner="splunk"
                fileGroup="splunk"
                file="/var/log/zimbra/mtain.log"
        )
        stop
}



# Log LDAP, Mailbox, Auth, Synch and Zmconfig log from mta
if (
        ( $inputname == 'imrelp' ) and
        ( $syslogfacility-text == 'auth' or $syslogfacility-text == 'local0' or $syslogfacility-text == 'local7' )
)
then {
        set $.logfile = $programname & ".log";
        action(
                type = "omfile"
                fileOwner="splunk"
                fileGroup="splunk"
                dynaFileCacheSize ="5"
                dynaFile="LogSavePath"
        )
        stop
}

# Unexpected
if ( $inputname == 'imrelp' ) then {
        action(
                type = "omfile"
                fileOwner="splunk"
                fileGroup="splunk"
                dynaFileCacheSize ="5"
                dynaFile="LogSavePath"
        )
        stop
}
```

Validate your conf by typing

`$ rsyslogd -N1 -f /etc/rsyslog.d/zimbra.conf`

If all is  fine you should see something like

```
rsyslogd: version 8.2210.0, config validation run (level 1), master config /etc/rsyslog.d/zimbra.conf
rsyslogd: End of config validation run. Bye.
```

Otherwise an error with an explanation is issued.

Finally restart the Rsyslog server.

If you have followed these instructions you can send these logs to Splunk using an _inputs.conf_ like

```
[monitor:///var/log/zimbra]
disabled = false
index = mailbox
sourcetype = zimbra:zsyslog
whitelist = ^\/var\/log\/zimbra\/(mail|mailbox|audit|sync|zmconfigd)\.log$

[monitor:///var/log/zimbra/mtaout.log]
disabled = false
index = main
sourcetype = zimbra:zsyslog

[monitor:///var/log/zimbra/mtain.log]
disabled = false
index = main
sourcetype = zimbra:zsyslog
```

