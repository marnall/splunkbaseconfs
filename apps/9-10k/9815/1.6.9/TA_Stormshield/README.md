# TA_Stormshield

Splunk add-on providing event breaking, field extraction and CIM mapping for
Stormshield firewall syslog data.

## Installation

This add-on ships **without `inputs.conf`**. It only provides sourcetype
classification, field extraction and CIM knowledge objects for the
`stormshield` base sourcetype — it does not assume a specific listening
port, host, or destination index. Create your own `local/inputs.conf` on the
receiving instance (typically a heavy forwarder or indexer) once installed,
for example:

```ini
[tcp://9517]
disabled = 0
index = <your_index>
sourcetype = stormshield
```

Point your Stormshield firewall's syslog output (raw/plain, TCP) at that
port. The add-on takes over from there: it reclassifies each event into the
appropriate `stormshield:<logtype>` sourcetype (`filter`, `connection`,
`web`, `auth`, `system`, `plugin`, `ids`, `server`, `dhcp`, `vpn`, `monitor`)
and applies the corresponding field extraction and CIM mapping.

On the firewall, set the syslog profile to **LEGACY_LONG**, not LEGACY:
LEGACY caps each message at 1024 characters and can truncate a WELF event
mid-field, which breaks parsing on fields read far into the line (e.g.
`stormshield:server`'s `msg` extraction). RFC5424 also works with this
add-on as-is — its header sits in front of the same WELF payload and does
not interfere with parsing.

## Supported sourcetypes

Field extraction and CIM mapping: `stormshield:filter`, `stormshield:connection`,
`stormshield:web`, `stormshield:auth`, `stormshield:system`, `stormshield:plugin`,
`stormshield:ids`, `stormshield:server`, `stormshield:dhcp`, `stormshield:vpn`,
`stormshield:ftp`, `stormshield:pop3`, `stormshield:smtp`, `stormshield:ssl`,
`stormshield:xvpn`, `stormshield:pvm` (CIM Vulnerabilities — `cve`/`cvss` stay
empty, Stormshield's Vulnerability Manager doesn't expose them),
`stormshield:sandboxing` (field extraction only, not CIM-tagged — no
`action` or malware category field exists on this sourcetype).

Sourcetype classification only (no field mapping yet): `stormshield:monitor`,
`stormshield:ipsecstat`, `stormshield:filterstat`, `stormshield:routing`,
`stormshield:dmrouting`, `stormshield:routerstat`.

**`ftp`, `pop3`, `smtp`, `ssl`, `xvpn`, `pvm` and `sandboxing` are untested** —
built from Stormshield's official field reference, not from observed events.
Validate against real traffic before relying on them.

## Compatibility

Splunk Enterprise 10.x.
