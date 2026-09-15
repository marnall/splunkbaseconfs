# Support and compatibility

**Author:** Eric Cobbs
**Required dependency:** Splunk Enterprise Security 8.x

> Cyber Defense Command Center requires Splunk Enterprise Security. It is not a standalone security application.

## Supported baseline

- Splunk Enterprise 9.2 or later, or a compatible Splunk Cloud Platform deployment
- **Splunk Enterprise Security 8.x (required)**
- Splunk Common Information Model

## Optional enhancements

Network Diagram Viz, Event Timeline Viz, and Heat Map Viz can be installed separately. The shipped dashboards do not require them.

## Configuration notes

- All scheduled detections, assurance assessments, notifiers, inventory refreshes, and lab searches ship disabled and require administrator review before enablement.
- Review every search against local index, macro, field, and retention conventions.
- The `notable` macro and `risk` index must be available to the viewer for ES panels.
- Restrict REST-backed detection inventory panels to roles with appropriate capabilities.
- Add only organization-approved enrichment domains to the dashboard trusted-domain list.
- External pivots must remain read-only and open in a new browser tab.
- Confirm `index=summary` retention and role access before enabling detection-engineering assessments.
- Keep the optional critical engineering issue finding disabled until routing, ownership, and suppression are approved.

## Security reports

For general support and non-sensitive defects, use [GitHub Issues](https://github.com/Ericcobbs1/cyber-defense-command-center/issues). Do not include credentials, tokens, proprietary searches, or production event data.

Suspected vulnerabilities must be reported privately through the repository's GitHub Security Advisory workflow after private vulnerability reporting is enabled. A response SLA must be finalized before Splunkbase publication.
