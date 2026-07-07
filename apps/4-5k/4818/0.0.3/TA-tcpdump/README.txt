About
-----

This TA enables a direct tcpdump input on a linux system running Splunk Universal Forwarder. 


Possible use cases
------------------

  * DNS Insight https://splunkbase.splunk.com/app/1827/
  * DHCP Insight https://splunkbase.splunk.com/app/1837/

Requirements
------------
  * CentOS 7+, Debian 10+ and similar

Installation
------------
**Method 1: scripted input**

  * install TA-tcpdump on UF and configure forwarding
  * enable script input in inputs.conf
  * modifiy bin/tcpdump.path if needed (interface)
  * modify tcpdump capabilities:
    * check that splunk user (by default "splunk") belongs to his own group: id splunk
    * chgrp splunk /usr/sbin/tcpdump
    * chmod 750 /usr/sbin/tcpdump
    * setcap cap_net_raw,cap_net_admin=ep /usr/sbin/tcpdump
  * restart UF

**Method 2: run tcpdump as a service and write output to a log**

  * install TA-tcpdump on UF and configure forwarding
  * enable monitor input in inputs.conf
  * copy provided tcpdump.service file to /etc/systemd/system and modify it (interface name, port) if needed
  * execute 'systemctl daemon-reload'
  * execute 'systemctl enable tcpdump'
  * execute 'systemctl start tcpdump'
  * copy provided tcpdump file to /etc/logrotate.d 
  * restart UF


Troubleshooting
---------------
  * splunkd.log: ERROR ExecProcessor - message from "/usr/sbin/tcpdump -pnns0 -i eth0 -tttt port 53" tcpdump: eth0: No such device exists - check "ip a" output and change the interface name in inputs.conf
  * splunkd.log: ERROR ExecProcessor - message from "/usr/sbin/tcpdump -pnns0 -i eth0 -tttt port 53" (SIOCGIFHWADDR: No such device) - check "ip a" output and change the interface name in inputs.conf
  * splunkd.log: ERROR ExecProcessor - message from "/usr/sbin/tcpdump -pnns0 -i ens32 -tttt port 53" tcpdump: verbose output suppressed, use -v or -vv for full protocol decode - not an error, but STDOUT from tcpdump, can be ignored
  * splunkd.log: ERROR ExecProcessor - message from "/usr/sbin/tcpdump -pnns0 -i ens32 -tttt port 53" listening on ens32, link-type EN10MB (Ethernet), capture size 262144 bytes - not an error, but STDOUT from tcpdump, can be ignored

Disclamer
---------
Running tcpdump permanently is a security risk. Don't run it on important productive systems. All what you do with this add-on is on your own risk.

Contact
-------
Please email me splunk@compek.net if you have any issues. I actively support my apps and am anxious to receive any feedback.

email: splunk@compek.net
