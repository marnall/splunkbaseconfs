## VirusTotal App for Splunk

**VirusTotal App for Splunk** is a lightweight Splunk App that allows you to enrich your security events with file reputation data retrieved from [VirusTotal](https://www.virustotal.com/), using the **existing IOC Reputation API**.

This app provides a custom search command that accepts **file hashes** (MD5, SHA-1, or SHA-256), **IP addresses**, **URLs**, and **domains**, and queries the corresponding VirusTotal endpoints to retrieve relevant threat intelligence data — all without submitting new files or URLs for analysis.


### Key Features

- Provides a custom SPL command (`vt`) that is easy to integrate into searches  
- Supports enrichment of multiple IOCs types: **file hashes**, **IP addresses**, **URLs**, and **domains**  
- Compatible with file hash formats: **MD5**, **SHA-1**, and **SHA-256**  
- Automatically selects and queries the appropriate VirusTotal API endpoint based on the indicator type  
- Enrich data with stats, categorizations, tags, detection details by antivirus engines, and much more
- Designed to work efficiently within automated alert enrichment pipelines  
- Includes a user-friendly UI for configuring the VirusTotal API key  
- Lightweight by design — no dashboards, saved searches, or additional objects  
- Fully compatible with **Splunk Enterprise** and **Splunk Cloud**


### Why Choose This App?

While there are other Splunk apps and add-ons that integrate with VirusTotal, many of them include dashboards, saved searches, or additional components that may not be required for all environments.

**This app is intentionally lightweight and minimalistic.**  
It focuses solely on providing a custom search command (`vt`) to interact with the VirusTotal API for file, url, domain and ip reputation checks, without introducing:

- No dashboards  
- No knowledge objects  
- No inputs or scheduled tasks  
- No unnecessary UI components  

This makes it ideal for security teams who:

- Prefer to build their own dashboards or alerts  
- Need API-based enrichment integrated directly into SPL queries  
- Value minimal dependencies and transparency in behavior


### Use Cases

- **Forensic Analysis**: Verify if a file hash, IP address, URL, or domain has been reported as malicious by security vendors.  
- **Alert Enrichment**: Add contextual threat intelligence to security events containing IOCs (Indicators of Compromise).  
- **Threat Hunting**: Investigate suspicious entities such as external connections, downloads, or domains seen in your environment.  
- **Automation of Decisions**: Enrich events automatically and take actions based on reputation (e.g., block an IP, quarantine a file, escalate an alert).  


### Requirements

- Valid VirusTotal API key (free or commercial)
- HTTPS connectivity from the Splunk environment to the VirusTotal API endpoint


### Example Usages

**Example 1:** Enrich events with VirusTotal reputation based on hash event field
```
index=security_logs sourcetype=malware_alerts
| vt hash=file_hash_sha256
| where last_analysis_stats_malicious > 5
```

**Example 2:** Query manually for a specific hash without any input events
```
| makeresults
| vt hash="178ba564b39bd07577e974a9b677dfd86ffa1f1d0299dfd958eb883c5ef6c3e1"
| where last_analysis_stats_malicious > 5
```