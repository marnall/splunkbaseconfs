# Security Policy

## Supported Versions

The following versions of **Zero Trust Compliance & IMS for Splunk** are currently receiving security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

We take the security of our DoD Zero Trust Compliance Platform seriously. If you identify a security vulnerability or compliance flaw, please follow these guidelines:

1. **Do NOT open a public GitHub issue** for sensitive vulnerabilities.
2. Email your vulnerability details and reproduction proof-of-concept to the security maintainers at **security@suhlabs.com**.
3. Include the following details in your report:
   - Type of vulnerability (e.g., RBAC bypass, CAC signature spoofing, path traversal, injection).
   - Component affected (`bin/`, `appserver/static/`, REST endpoint, or XML dashboard).
   - Steps to reproduce or Proof-of-Concept payload.
   - Potential impact on DoD Zero Trust posture or eMASS certification.

### Response Timeline
- **Initial Response:** Within 24 hours.
- **Triage & Remediation Plan:** Within 72 hours.
- **Patch Release:** Delivered in an emergency maintenance release tag with associated Splunk AppInspect validation.
