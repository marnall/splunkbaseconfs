ABOUT
This App visualizes DNS traffic and helps to pinpoint errors and anomalies (like DNS-Tunneling).

This App takes an output of tcpdump as input, parses it and displays results as following charts and tables:

Total Events
Parsing Errors
Query Type Distribution
Return Code Distribution
Protocol (UDP/TCP) Distribution
Top Queries
Top Level Domains
Top Reverse Resolution Entries (PTR)
Top DNS Errors
Slowest Transactions
Top Destinations
Top Sources
Count
DNS Packet Length
Number of Labels in the dns_qry_name
Duration
Possible DNS Tunnelling

The DNS Traffic can be collected simultaneously from many different devices:

-windows (by capturing with dumpcap locally and parsing with tcpdump on linux)
-linux
-switch mirror port (SPAN)
-TAP device
-manual import from a saved network dump (pcap file)

REQUIREMENTS
tcpdump - to collect and dump live DNS traffic
dumpcap (part of Wireshark) - to collect DNS traffic on Windows

INSTALLATION
For a single desployment (to collect DNS traffic from one system only) you need to install Splunk Enterprise + DNS_Insight App and configure input (see below).
For a distributed desploymeint (to collect DNS traffic from many systems):
  install Splunk Universal Forwarder + DNS_Insight on each system
  install Splunk Enterprise + DNS_Insight App on a separate server to collect logs
  configure (if not yet done) input on Splunk Enterprise
  configure output on each Universal Forwarder
  install TA-tcpdump (https://splunkbase.splunk.com/app/4818/)
   OR
  configure DNS traffic recording and parsing (see below)
  restart Universal Forwarder

Update (15.dec.2019 v0.0.4): the prefered way is to install TA-tcpdump (https://splunkbase.splunk.com/app/4818/) instead of configuring tcpdump recording and parsing:
  * it is more secure
  * no need to create any local files
  * real time, no need to wait until the pcap is rotated

The installation instruction below is OBSOLET, use TA-tcpdump instead:

Here is an example of a complete setup using a CentOS 7 or Debian 10 as a source of a DNS data input:

ATTENTION: running tcpdump as suggested can be a security risk and an example provided for information only! Consult a security expert to minimize it if unsure!

Check if there is enough free space on the hard drive. You can consider to use a separate partition for the tcpdump data.

aa-complain /usr/sbin/tcpdump # set tcpdump to complain mode - debian only
useradd -d /nonexistent -s /usr/sbin/nologin tcpdup # add a restricted tcpdump user
mkdir var/tcpdump # create a folder where pcap files and a script are stored
chown :tcpdump /var/tcpdump # change ownership of the directory
chmod g+w,o-w /var/tcpdump # change permissions of the directory

create /var/tcpdump/pcap2txt.sh file with this content:

#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
INFILE=$1
OUTFILE=/var/tcpdump/tcpdump.txt
LOG=/var/tcpdump/out.log
date >> $LOG
/usr/sbin/tcpdump -tttt -nns0 port 53 -r $INFILE > $OUTFILE 2>> $LOG
wc $OUTFILE >> $LOG

add an executable bit:
chmod +x /var/tcpdump/pcap2txt.sh

This script will create a text dump from the recorded data after the rotation which can be sent to the splunk indexer using rsyslog/syslog-ng or splunk-forwarder. This input should be configured as a "port53tttt" sourcetype on the splunk indexer.

now start tcpdump (change the interface name as needed):

nohup tcpdump -pnns0 port 53 [-i ens32] -w /var/tcpdump/tcpdump.pcap -W100 -C100 -z /var/tcpdump/pcap2txt.sh -Z tcpdump &>>/var/tcpdump/out.log &
where:

-pnns0 - no promicious mode, don't convert protocol and port numbers etc. to names
-C100 -W100 - create a ring buffer of 100 files a 100MB (10GB in total)
-w - where to store recorded data
-z /var/tcpdump/pcap2txt.sh - run a simple script after rotation
-Z tcpdump - run as restricted "tcpdump" user
This app tested with CentOS 6/7, Debian 9/10 and Splunk 6/7/8/9.


Contact: splunk@compek.net
