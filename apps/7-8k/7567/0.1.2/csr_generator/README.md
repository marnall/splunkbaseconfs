# CSR Generator for Splunk

![](appserver/static/images/banner.png)

## Overview

**CSR Generator** is a Splunk app that allows users to generate a Certificate Signing Request (CSR) and a private key directly from a simple dashboard UI inside Splunk. 

The app leverages the OpenSSL binary bundled with Splunk (`splunk cmd openssl`) and is fully compatible with **Windows and Linux environments**.



## Release History

| Date       | Version | Notes                                                                 |
|------------|---------|-----------------------------------------------------------------------|
| 2024-10-04 | 0.0.1   | Initial release                                                       |
| 2024-10-12 | 0.0.2   | Added `subjectAltName` support, improved input handling, bug fixes    |
| 2025-05-21 | 0.1.0   | Major UI/UX redesign, improved CSR engine, full Windows/Linux support |
| 2025-06-18 | 0.1.1   | Minor fixes                                                           |
| 2025-11-05 | 0.1.2   | Locked command execution to search heads to satisfy cloud vetting     |

---

## Dashboard

![](appserver/static/images/view.png)

---

## Syntax

```spl
| gencsr common_name=<string> country=<string> state=<string> locality=<string> organization=<string> organizationalunit=<string> password=<string> subjectaltname=<string>
```

---

## Example

```spl
| gencsr common_name="example.com" country="US" state="CA" locality="San Francisco" organization="Example Inc." organizationalunit="IT" password="securepassword" subjectaltname="www.example.com,mail.example.com"
```

---

## Features

- Generates CSRs using OpenSSL standards.
- Full cross-platform support (Windows and Linux).
- Customizable fields: Common Name (CN), Country (C), State (ST), Locality (L), Organization (O), Organizational Unit (OU), and SubjectAltName (SAN).
- Secure in-memory handling of key and CSR (temp files are securely deleted).
- Outputs CSR and private key directly to the Splunk UI for easy copy/paste.
- User-friendly dashboard UI with real-time validation and dynamic SAN input.
- Integrated with Splunk SPL as a custom `GeneratingCommand`.

---

## New in Version 0.1.2

- Enforced search head-only execution for the custom search command to satisfy the updated Splunk Cloud vetting policy.
---

## New in Version 0.1.0

- UI rebuilt using modular SimpleXML layout with custom JS/CSS separation and explicit grid logic.
- Decoupled rendering logic from command execution to improve maintainability and cross-browser behavior.
- Replaced STDIN key handling with file-based input to ensure openssl works reliably on both Windows and Linux.
- Output normalization: removed injected OpenSSL stderr content and ensured raw PEM output for both CSR and private key.
- Refactored dashboard styling using scoped selectors and isolation-friendly CSS to avoid conflict with Splunk base styles.
- Optimized DOM structure for better performance and rendering inside Splunk’s Web Framework under constrained environments.

---

## Credits

- Inspired by **MS**

---

## Links

- Feel free to contribute or Fork via [https://github.com/aleeric/CSR-Generator-for-Splunk](https://github.com/aleeric/CSR-Generator-for-Splunk)

- Rate App on Splunkbase via https://splunkbase.splunk.com/app/7567
