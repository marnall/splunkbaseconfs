Menlo Security HEAT Analyzer

HEAT attacks are a class of cyber threats targeting web browsers as the
attack vector and employs techniques to evade detection by multiple layers
in current security stacks including firewalls, Secure Web Gateways,
sandbox analysis, URL Reputation, and phishing detection. HEAT attacks are
used to deliver malware or to compromise credentials, which in many cases
leads to ransomware attacks

The Menlo Security HEAT Analyzer Splunk App analyzes log data to identify
HEAT attacks that evade URL reputation tools.  These attacks are called
Legacy URL Reputation Evasion (LURE) attacks.


After installing the app, enter the OEM ID, Device ID and UID in the
setup page to enable communications between the app and the Menlo platform.

The Menlo Security HEAT Analyzer dashboard analyzes event in the selected index(es) by looking for the ‘dest’ and ‘category’ fields.  The ‘dest’ field is expected to contain the domain of interest and the ‘category’ field contains the previous classification for the domain.

The dashboard fitters out domains that were previously classified as malicious and then checks the remaining domains using Menlo HEAT.
