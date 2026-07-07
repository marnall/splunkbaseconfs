# IPv6 Search Add-On For Splunk
## Overview
This custom search add-on allows a Splunk user to search for data against an IPv6 range.  This wi

## Fields
- field : The field name with the ipv6 addresses, such as src_ip
- ipv6 : A valid ipv6 range such as faf9::/16
## Example Search
yoursearch | ipv6search field=src_ip ipv6="faf9::/16"

