# FACCT TI Splunk Integration. 

### v0.2.0
Pre-release version for early access.

### v0.8.2
Add all the collection from API.

#### v1.0.0
Provides basic jsoned TI&A items.  

#### v1.0.1
Darkweb and Breached DB collections items added. 

### v1.0.2
Add search

### v1.1.0
Global update include refactor end optimization.
1. Add global search in real time 
2. Add views into dashboard
3. Refactor code


### v1.1.5
Added the ability to choose save images from collections apt/threat, hi/threat.

### v1.2.0
Added new endpoint:
1. "compromised/bank_card_group": "Compromised::Group_Card",
2. "compromised/masked_card": "Compromised::Masked Card",
3. "compromised/reaper": "Compromised::Darkweb",
4. "compromised/access": "Compromised::Access",
5. "compromised/discord": "Compromised::Discord",
6. "compromised/messenger": "Compromised::Messenger",
7. "ioc/common": "IOC::Common",
8. "attacks/phishing_group": "Attacks::Phishing Kit",
9. "osi/git_repository": "OSI::Git Repository",
10. "suspicious_ip/scanner": "Suspicious IP::Scanner",
11. "suspicious_ip/vpn": "Suspicious IP::VPN",
12. "malware/config": "Malware::Config",
13. "malware/signature": "Malware::Signature",
14. "malware/malware": "Malware::Malware",
15. "malware/yara": "Malware::yara",

Remove old endpoint:
1. "bp/phishing": "BP::Phishing",
2. "bp/phishing_kit": "BP::Phishing Kit",
3. "osi/git_leak": "OSI::Git Leak",
4. "malware/targeted_malware": "Malware::Targeted Malware"

Update Global search command:
1. Refactor struct of command | faccttisearch global_search='' -> | facctsearch search=''
2. Enlarge mount of data, add WhoIS information, add more attribution

Add Graph search command:
| facctsearh search=''
This command provide you data about IP's and domain

### v1.2.0
Added more WhoIs information and attribution

### v1.4.0
Refactored search logic
Removed deprecated collections
Refactored Attribution logic