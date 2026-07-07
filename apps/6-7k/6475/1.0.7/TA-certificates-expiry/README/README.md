Certificates Expiry Add-on for Splunk
=====================================

* **Author:** Gary Croker

### Description ###

This Certificates Expiry Add-on for Splunk allows a Splunk® Enterprise
or Splunk Cloud administrator to collect data from hostnames or FQDN. The add-on
collects the certificate but records minimal detail from the certificate. 
The Add-on is built with Splunk AOB (Add-on Builder) and minimalist viewpoint.
Aim is collect appropriate field data to raise alerts to appropriate teams or administrators that 
a certificate is approaching expiration and requires renewal. Use it to monitor certificates
for splunk forwarders and indexers for eg. indexer01:9996 
As of version 0.0.8 the mode is changed to single instance. This allows large scale inputs, author has test up to 5000 inputs, forwarder now uses far less resources.

The fields collected by the add-on are:

* date - date and time the input runs - now includes microseconds
* fqdn - the hostname or FQDN hosting the certificate
* inputstanza_name - the short name in input.conf after [fqdn_for_certificate://<name>]
* port - the port of the hostname or FQDN hosting the certificate
* issuer - the organizationName in issuer 
* commonName - the commonName in issuer
* use_proxy - if proxy was used
* notAfter - date in notAfter from certificate
* notBefore - date in netBefore from certificate
* expiredays - the number of days until expiry
* cipher - the name of the cipher being used
* protocol - the version of the SSL protocol that defines its use
* secret_bits - the number of secret bits being used 

OCSP fields are also added in this version. SAN is presented as multivalue list - or value "None found" if SAN is empty
Additional Fields: (from v1.0.7)
* expiry_status – A human-readable status derived from expiredays (e.g. OK, CAUTION, CRITICAL) used for alerting thresholds
* expiry_bucket – Grouped expiry classification (e.g. 30_Days, 60_Days) for easier reporting and dashboards
* fingerprint_sha256 – SHA-256 hash of the certificate, useful for uniquely identifying and tracking certificate changes or replacements
* serialNumber – Certificate serial number assigned by the issuing CA; helpful for revocation checks and audit correlation
* extended_key_usage – Defines allowed purposes of the certificate (e.g. Server Authentication, Client Authentication)
* subjectAltName (SAN) – Multi-value list of alternative hostnames covered by the certificate (critical for modern TLS validation)
* caIssuers – URL(s) to download the issuing CA certificate chain
* crlDistributionPoints – URL(s) where Certificate Revocation Lists (CRLs) can be retrieved
* OCSP – Online Certificate Status Protocol endpoints used for real-time revocation checking
* peer_ip – The resolved IP address the connection was made to (useful for DNS vs actual endpoint verification)
* tcp_connect_time_ms – Time taken to establish the TCP connection
* tls_handshake_time_ms – Time taken to complete the TLS handshake
* total_connection_time_ms – End-to-end connection time (TCP + TLS), useful for performance monitoring
* version – X.509 certificate version (typically v3 for modern certificates)

example event (v0.0.2)
date=01/06/2022 11:42:45 fqdn=splunk.com port=443 expiredays=181 issuer="DigiCert Inc" commonName="DigiCert TLS RSA SHA256 2020 CA1" use_proxy=True notAfter="Nov 29 23:59:59 2022 GMT" notBefore="Nov 29 00:00:00 2021 GMT"

example event (v0.0.3 - v1.0.0)
{"time": "08/07/2023 09:11:38.590998", "OCSP": ["http://ocsp.digicert.com"], "basicConstraints": -1, "caIssuers": ["http://cacerts.digicert.com/DigiCertTLSRSASHA2562020CA1-1.crt"], "cipher": "ECDHE-RSA-AES256-GCM-SHA384", "commonName": "DigiCert TLS RSA SHA256 2020 CA1", "crlDistributionPoints": ["http://crl3.digicert.com/DigiCertTLSRSASHA2562020CA1-4.crl", "http://crl4.digicert.com/DigiCertTLSRSASHA2562020CA1-4.crl"], "ex_flags": 263, "expiredays": 144, "extendedKeyUsage": 3, "fqdn": "splunk.com", "issuer": "DigiCert Inc", "notAfter": "Nov 28 23:59:59 2023 GMT", "notBefore": "Nov 21 00:00:00 2022 GMT", "organizationName": "DigiCert Inc", "port": "443", "protocol": "TLSv1.2", "secret_bits": "256", "serialNumber": "06DDC4517820547D85012AB1379067F7", "subjectAltName": ["splunk.com", "alias.splunk.com", "banner.splunk.com", "base.splunk.com", "blogs.splunk.com", "carabiner.splunk.com", "communities.splunk.com", "community.splunk.com", "company.splunk.com", "conf.splunk.com", "de-de.splunk.com", "de.splunk.com", "demo.splunk.com", "dev.splunk.com", "developers.splunk.com", "docs.splunk.com", "documentation.splunk.com", "download.splunk.com", "education.splunk.com", "embargo.splunk.com", "en-us.splunk.com", "en.splunk.com", "es-es.splunk.com", "es.splunk.com", "fr-fr.splunk.com", "fr.splunk.com", "it-it.splunk.com", "it.splunk.com", "ja-jp.splunk.com", "ja.splunk.com", "ko-kr.splunk.com", "ko.splunk.com", "legacyapi.splunk.com", "login.splunk.com", "partners.splunk.com", "piton.splunk.com", "preview.splunk.com", "product.splunk.com", "pt-pt.splunk.com", "pt.splunk.com", "quickdraw.splunk.com", "ru-ru.splunk.com", "ru.splunk.com", "services.splunk.com", "solutions.splunk.com", "splunklive.com", "store.splunk.com", "support.splunk.com", "usergroups.splunk.com", "web.splunk.com", "webmservices.splunk.com", "wiki.splunk.com", "www.splunk.com", "www.splunklive.com", "zh-cn.splunk.com", "zh-hans.splunk.com", "zh-hant.splunk.com", "zh-hk.splunk.com", "zh-mo.splunk.com", "zh-my.splunk.com", "zh-sg.splunk.com", "zh-tw.splunk.com"], "use_proxy": "True", "version": 3}

### Documentation ###
No components are required on Searchhead or Searchhead Clusters
Install this TA on a HF (Heavy Forwarder) and configure inputs using a proxy or not

Single instance mode:
From Version 0.0.8 the code in this TA is restructured to use single instance mod input. Using single instance modular input is lighter on resources of forwarder and iteration of inputs rather than more processes per input. This also means no intervals on individual inputs in inputs.conf but rather a single interval in inputs.conf which defaults to 1 day (24 Hours). Of course you can override this with local/inputs.conf if you require more or less frequent data.
If upgrading interval will exist in inputs.conf, consider removing interval = <period> as it is no longer used

Macro:
adjust `certificate_expiry_indexes` to point to your index containing certificate data collect by this TA

Proxy:
The proxy implementation is limited at this time, http transparent proxy only. No authentication to the proxy is performed in this version.

Debug log level:
Can be used if set

Interval (now global setting):
defaults to 24h or 86400 seconds which is probably enough data for raising alerts

Internal Index info:
use the internal index for retrieval of information on inputs 

Internal Index
    
    index=_internal  sourcetype="tacertificatesexpiry:log"
    
Example Search 
    
    sourcetype=ssl_cert | stats last(issuer) as Issuer last(commonName) as commonName last(expiredays) as "Days Left" by fqdn | rename fqdn as "Domain / Hostname"

Example Alert search
    
    sourcetype=ssl_cert | stats last(issuer) as Issuer last(commonName) as commonName last(expiredays) as "Days Left"  by fqdn | rename fqdn as "Domain / Hostname" | where tonumber('Days Left') < 30
    
### Libraries Included ###
none

### Patch history notes ###
12th June 2023: Wallid Nazzal - found inputs bug - with high numbers of inputs setup - file not found bug - changed temp file to use uuid.
22nd June 2023: Kevin Buckley - request for the Cipher, SSL details to be added as more useful data. Moved toward OCSP and json data structures.
18th November 2023: v0.0.4 - splunk appinspect - check_for_addon_builder_version + check_python_sdk_version - outdated version of the Splunk SDK for Python (1.6.16).  Upgrade to 1.7.3 or later.
21st November 2023: v0.0.5 - splunk appinspect - update Splunk SDK for Python (1.7.4).
4th September 2024: v0.0.8 - Steffen Griebel - reported hit inputs.conf limitations on forwarder for around 300 inputs - I decided to restructure TA for single instance mode and iterate over inputs. Many users could have thousands of endpoints, this change does this. Added a little more debug info. Code fix ups.
12th September 2024: v1.0.0 - splunk - check_version_is_valid_semver + update Splunk SDK for Python (2.0.2).
2nd February 2025: v1.0.1 - fix bug for empty SAN - update Splunk SDK for Python (2.1.0).
17th April 2025: v1.0.2 - Tyler Montney - found splunk 9.4.0 SSLv3 and ssl.wrap_socket() - introduce use of SSL context for max compatability in script - appinspect - local.meta failed
17th April 2025: v1.0.3 - version bumped - resubmit to splunkbase
4th October 2025: v1.0.4 - check for splunk 10.0.1 issues, make error logging a little clearer with keypair values and exceptions. Reduce default interval to run twice a day
10th October 2025: v1.0.5 - Mustafa Demir - request to add EKU, these are added in a search friendly way and they are sorted to always come out same way. Client before Server etc
11th October 2025: v1.0.6 - bump version, UCC checks, make it clear in release notes that this build requires 9.3 splunk and python 3.9 or higher
5th May 2026: v1.0.7 - convert TA to UCC. Add basic dashboards to assist users, macro `certificate_expiry_indexes` for dashboards, added more fields to support dashboards.
