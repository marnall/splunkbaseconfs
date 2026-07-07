DHCP Insight

   Version: 0.0.3

   Date: 14.Mar.2024

   This application parses output of tcpdump and creates following graphs and tables:

     DHCP Type Distribution
     Top MAC Addresses
     Top Hostnames
     Top Client IPs
     Top Offers

  You can create alerts based on suspicious events and analyse them later with Wireshark.

  The DHCP Traffic can be collected simultaneously from many different devices:
    - windows server
    - windows workstation
    - linux server
    - switch mirror port
    - TAP device
    - saved network dump (pcap file)

  This App requires Splunk v6+.

  Use following command to create the required output using tcpdump:

    tcpdump -tttt -ev -pnns0 port 67 or port 68

  to create a ring buffer with tcpdump (change parameters as needed):

    nohup tcpdump -pnns0 -C100 -W100 -w /var/tcpdump/tcpdump.pcap port 67 or port 68 &>>/dev/null &

  E-Mail: splunk@compek.net
