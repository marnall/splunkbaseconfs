Cisco LCS Plug-In for Splunk
Version 1.1.0
============================================================

This add-on collects device inventory, contracts, security alerts, and lifecycle data
from Cisco CX Cloud's Business Critical Services (BCS) API and ingests it into Splunk.
It is intended for Cisco Advanced Services customers who want to monitor and analyze
their network operations from within Splunk.

Data is collected across 31 BCS API endpoints and indexed using cisco:bcs:* sourcetypes
with JSON indexed extraction. Authentication uses OAuth2 client credentials (JWT), with
automatic token refresh both proactively (before expiry) and reactively (on 401 errors
during pagination). Built-in rate limiting enforces 10 calls/sec and 10,000 calls/day
with a UTC midnight reset.


------------------------------------------------------------
Release Notes
------------------------------------------------------------

Version 1.1.0
-------------
- Added "Region" input parameter: select US (Americas) or EMEA (Europe, Middle East &
  Africa) to route API requests to the correct Cisco CX Cloud regional endpoint.
- Added "Security Vulnerable Only" checkbox: when enabled (default), Security Advisories
  and Field Notices are filtered to return Vulnerable and Potentially Vulnerable items
  only, reducing data volume for security-focused use cases.
- Credentials (Client ID and Client Secret) are now stored in a reusable Account
  configuration (Configuration > Account tab) rather than per-input, allowing multiple
  inputs to share the same credentials.
- Implemented automatic JWT refresh: tokens are refreshed proactively when within 5
  minutes of expiration and reactively on any 401 Unauthorized response during
  pagination, eliminating manual intervention for long-running collection runs.
- Input validation now enforces that the Region value is either "us" or "emea".

Version 1.0.0
-------------
- Initial release.
- Modular input collecting data from 31 Cisco BCS API endpoints.
- OAuth2 JWT authentication with retry logic (up to 3 attempts, exponential backoff).
- Paginated data collection via response headers (offset, max, total).
- Built-in rate limiting: 10 calls/sec, 10,000 calls/day (UTC daily reset).
- All 31 cisco:bcs:* sourcetypes defined in props.conf with JSON indexed extraction.


------------------------------------------------------------
Support
------------------------------------------------------------

For issues with the add-on, please refer to the Splunk Community or the project's
GitHub repository.

For issues with Cisco API credentials or access to the Cisco BCS API, contact
Cisco Support directly.
