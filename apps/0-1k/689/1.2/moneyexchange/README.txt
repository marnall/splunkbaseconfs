Money Exchange in Splunk 6
by Howard Chin
December, 2014
hchin@splunk.com


Overview
========
Money Exchange is an useful tool to provide history chart and quotes on various currencies. To obtain scheduled or historical exchange rate for eight countries currency pair base on your currency choices by either select country area from the map or drop-down manual. The app is basically through custom scripted inputs comprising of a bunch of Python scripts. It can run on *Nix and Windows respectively. 


System Requirement
==================
Hardware requirement: 
Two Dual Core 2.79 GHz processors & 2GB RAM above

Recommended System/platform as followed:
1) Splunk 6.1.x and 6.2.x
2) Windows IE 7 and above
3) Mozilla Firefox
4) Google Chrome


Installation & Start
====================
Windows:
1) Install either Splunk 6.1.x or 6.2.x
2) Uncompress moneyexchange.tgz to $SPLUNK_HOME\etc\apps
3) Restart Splunk
4) Login Splunk Web
5) Lunch MoneyExchange app

Linux:
1) Install either Splunk 6.1.x or 6.2.x
2) Uncompress moneyexchange.tgz to $SPLUNK_HOME/etc/apps
3) Restart Splunk
4) Login Splunk Web
5) Lunch MoneyExchange app


Data input introduction
=======================
Currency pair data is download and input to Splunk indexer by Python scripts


Troubleshooting
===============
1) check your network environment, including firewall setup
2) check Splunk server's service, hostname and port
3) See the Splunk logs for any warnings or errors under $SPLUNK_HOME\var\log\splunk


Known issues
============
No historical rates data until the app installed and start


Other References:
=================
Splunk online documentation is located at:
http://www.splunk.com/base/Documentation
