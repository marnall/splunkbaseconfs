# TA-opd

## OVERVIEW
TA-opd scans for open ports. This app should be installed on your Heavy Forwarder. Nmap will also need to be installed. The app will look for nmap in these paths:
- nmap
- /usr/bin/nmap
- /usr/local/bin/nmap
- /sw/bin/nmap
- /opt/local/bin/nmap
These are the only files that the app may access outside the app directory.

 This app uses python-nmap
(https://bitbucket.org/xael/python-nmap) to run Nmap commands. The following modular inputs can be set up:
- Banner Scan (sourcetype=opd:banners)
- Full Scan (sourcetype=opd:full)
- Quick Scan (sourcetype=opd:quick)
- Version Scan (sourcetype=opd:versions)

A separate app called 'Hurricane Labs Open Port Detection' can be installed on your Search Head from which you can utilize
additional saved searches and dashboards along with possible Shodan integration.


## SPLUNK VERSION SUPPORT
7.0, 6.6


## INSTALLATION
1. Make sure TA-opd is installed on a Heavy Forwarder and is sending data to sourcetype=opd.


## RELEASE NOTES

### v2.0
- Added option for 'All' protocols (TCP, UDP, ICMP)
- Added label option (e.g. DMZ, Firewall)


## DEV SUPPORT
Contact: splunk@hurricanelabs.com
