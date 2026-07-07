About
-----

This TA enables a direct network input on Windows.

Possible use cases
------------------
- DNS Insight https://splunkbase.splunk.com/app/1827/
- DHCP Insight https://splunkbase.splunk.com/app/1837/

Installation
------------
- install Wireshark (you can disable all components except tshark)
- install TA-tshark on UF and configure forwarding
- modifiy inputs.conf and bin/tcpdump.path if needed. The provided file is configured to capture port 53 (DNS) on first interface and defines the input as "tshark:port53" sourcetype.
- restart UF

Disclamer
---------
Running tshark/dumpcap permanently is a security risk. All what you do with this add-on is on your own risk.

Contact
-------
splunk@compek.net

