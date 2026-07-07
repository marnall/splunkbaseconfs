# TA-ftppull

NOTE: This is the non-cloud version of TA-ftppull. For installation in Splunk Cloud, use version 1.4.3c.

The FTP Pull Add-on for Splunk adds a modular input for downloading and indexing
files from one or more FTP servers.

Support:
- Splunk 9.1, 9.0, 8.2, 8.1, 8.0, 7.3

Installation/Configuration:
1. Install this app to a forwarder (or your all-in-one search head)
2. Navigate to Settings->Data Inputs->FTP Input to configure new inputs. 
Explanations of each input option are as follows:

* username - FTP username
* password - FTP password
* hostname - FTP hostname
* path - Directory containing file(s)
* filename - Filename. Supports wildcards
* override - If set to true, every event from this input will have the "host" 
    field set as the FTP server hostname.
* disable_wildcards - If set to true, filename will be interpreted literally.
    This option is useful for some legacy systems. 
* force_tls - If set to true, TLS will be used on FTP connections

Support:
    Support for this app is provided through e-mail during weekday business 
    hours (US, Eastern Time).
    Please send your questions/concerns to splunk-app@hurricanelabs.com.

