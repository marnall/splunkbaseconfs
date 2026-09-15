# O365 & Entra ID Security

Unified security visualization app for **Microsoft 365 (Office 365 Management Activity)**
and **Microsoft Entra ID (Azure AD via Event Hub)**: sign-in security, directory/audit
changes, data & collaboration, apps & AI, and a global threat geo view.

## Data sources

| Platform | Sourcetype(s) | Notes |
|---|---|---|
| Microsoft 365 | `o365:management:activity` | Office 365 Management Activity API via the Splunk Add-on for Microsoft Office 365 |
| Microsoft Entra ID | `azure:monitor:aad`, `mscs:azure:eventhub` | Azure AD diagnostic logs (SignInLogs + AuditLogs) via Event Hub / MSCS add-on. Both sourcetypes are matched so the app works whether or not the Event Hub data has been retyped. |

## Index configuration

Out of the box the app searches all indexes (`index=*`) and keys everything off the
vendor sourcetypes above, so it works without any tuning. For performance, point it at
your real indexes by overriding two macros in `local/macros.conf`:

```
[o365_index]
definition = index=<your_m365_index>

[entra_index]
definition = index=<your_entra_index>
```

This app is **self-contained**: it ships its own `props.conf` field normalization that maps the
nested Entra `properties.*` JSON and the mixed O365 `ResultStatus` values into a clean, shared
vocabulary (`user`, `src_ip`, `signin_status`, `mfa`, `error_code`, `failure_reason`, `city`,
`country`, `lat`/`lon`, `os`, `device_compliant`, `risk_level`, `audit_action`, `audit_initiator`,
`audit_target`, …). It does **not** depend on any other Azure/O365 app being installed.

## Dashboards (tabs)

1. **Executive Overview** — combined KPIs, activity-by-platform trend, sign-in outcome, MFA
   coverage, global activity map + country choropleth, top workloads/operations, top failed users.
2. **Identity & Sign-in Security (Entra)** — success/failure, failure rate, account lockouts,
   legacy auth, failure-reason breakdown, MFA / conditional access / client-app mix, sign-in
   geomap, top failed sources, applications, device OS & compliance, risky/flagged sign-ins.
3. **Directory & Audit Changes (Entra)** — user/group/device lifecycle, password resets,
   security-info (MFA) registration, change-over-time, top actors, user lifecycle & device tables.
4. **Data & Collaboration (M365)** — OneDrive/SharePoint file activity, **anonymous & external
   sharing exposure**, downloads, busiest users & files, anonymous-link access by source IP/country.
5. **Apps & AI (M365)** — Copilot AI adoption, Power BI, Power Platform, Forms, Teams, Exchange,
   Defender alerts.
6. **Threat & Geo** — cross-platform brute-force / **password-spray** (one IP → many users),
   malicious-IP sign-ins, **possible impossible-travel**, failed-login geography, most-targeted users.

## Macros

- `` `o365_index` `` / `` `entra_index` `` — index selection (default `index=*`; override in `local`)
- `` `o365` `` — `` `o365_index` sourcetype=o365:management:activity ``
- `` `aad` `` — `` `entra_index` (sourcetype="azure:monitor:aad" OR sourcetype="mscs:azure:eventhub") ``
- `` `aad_signin` `` / `` `aad_audit` `` — AAD sign-in / audit subsets
- `` `o365_signin` `` — O365 AzureActiveDirectory workload
- `` `m365` `` — both platforms combined (overview/geo)

## Notes / caveats

- **Sign-in overlap**: Entra `SignInLogs` and O365 `UserLoggedIn` (AzureActiveDirectory workload)
  both record interactive sign-ins. This app uses the **Entra Event Hub feed as the primary sign-in
  source** (richer: risk, MFA, conditional access, device, geo) and uses O365 mainly for its
  workload strength (OneDrive/SharePoint/Copilot/PowerBI/Exchange/Teams). The Threat tab counts O365
  `UserLoginFailed` separately so both perspectives are visible.
- Geomaps use `iplocation` on the source IP for combined panels and native `geoCoordinates`
  (lat/lon) for the Entra-only sign-in map.
- Entra Event Hub currently streams interactive `SignInLogs` + `AuditLogs`. If
  `NonInteractiveUserSignInLogs` / `ServicePrincipalSignInLogs` are added to the diagnostic setting,
  the identity panels will automatically include them.

## Version

2.0.0
