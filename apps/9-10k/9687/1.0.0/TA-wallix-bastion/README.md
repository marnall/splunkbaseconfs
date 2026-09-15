# WALLIX Bastion Add-on for Splunk (`TA-wallix-bastion`)

Technology Add-on that parses, normalizes and CIM-maps **WALLIX Bastion**
Privileged Access Management syslog events.

| | |
|---|---|
| Version | 1.0.0 |
| Vendor product | WALLIX Bastion 6.x – 12.x |
| Splunk | Enterprise ≥ 8.2, Splunk Cloud |
| Splunk CIM | 5.3.x (Authentication, Change, Network Traffic, Endpoint) |
| Index-time operations | **yes** — sourcetype routing (see *Install the add-on*) |
| Scripts / binaries | **none** — search-time knowledge objects only |
| License | Apache-2.0 |

---

## 1. What it does

WALLIX Bastion emits one mixed syslog stream containing seven log families.
The add-on splits it into one sourcetype per family, extracts the fields, and
maps them onto the Splunk Common Information Model.

Two things vary independently, and all four combinations are handled: the
**envelope** is either RFC 5424 (`<14>1 2024-06-26T22:37:26+01:00 host app pid
- -`) or RFC 3164 / BSD, with or without a priority (`<14>Aug 28 12:26:45 host
sshproxy[13656]:`); the **payload** uses either double quotes (`key="value"`)
or the legacy `WAB(CORE)` single quotes (`key='value'`). Production appliances
commonly pair a BSD envelope with a double-quoted payload.

```
                          ┌─ [wabaudit] ──────────► wallix:bastion:audit      → Change
                          ├─ [wabauth] / WAB(CORE) ► wallix:bastion:auth       → Authentication
  Bastion syslog ─────────┼─ [SSH|RDP Session] ───► wallix:bastion:session    → Authentication
  (wallix:bastion)        │                                                      Network Traffic
                          │                                                      Endpoint/Processes
                          ├─ [sshproxy|rdpproxy] ─► wallix:bastion:proxy      → Network Traffic
                          ├─ [Vault Activity] ────► wallix:bastion:vault      → Change (credential)
                          ├─ [sessionintegrity] ──► wallix:bastion:integrity  → (vendor + eventtypes)
                          └─ pam_unix / sudo ─────► wallix:bastion:system     → (vendor + eventtypes)
```

---

---

## 2. Choose how you collect

WALLIX Bastion only speaks syslog. Four ways to get that stream into Splunk;
they are alternatives, not steps. Pick one now - it decides where the add-on
has to be installed, in section 3. The detail of each is in section 4.

| | Method | Use it when |
|---|---|---|
| **a** | Splunk Connect for Syslog (SC4S) | Default choice. Buffers to disk, posts to HEC on the indexers. |
| **b** | Direct TCP input on a heavy forwarder | Small estate, no SC4S. No disk buffer: a restart loses what was in flight. |
| **c** | Syslog relay writing files + universal forwarder | You want the files themselves as a replay buffer. |
| **d** | Relay converting syslog to HEC | Splunk Cloud with no on-prem heavy forwarder. |

---

## 3. Install the add-on

### Where it goes

Find your collection method in the left column. The rows are alternatives, not
a checklist.

| Collection method (from section 2) | Install the add-on on |
|---|---|
| **a.** SC4S | indexers + search heads |
| **b.** TCP input on a heavy forwarder | heavy forwarder + search heads |
| **c.** Syslog relay + universal forwarder reading files | universal forwarder + indexers + search heads |
| **d.** Relay to HEC | indexers + search heads |

Search head clustering: deploy through the deployer, as usual.

### If a universal forwarder is in the path

Only method **c**. The UF assigns the sourcetype and index from `inputs.conf`,
then forwards the stream unparsed, so the add-on is needed on the UF *and* on
the indexers.

`EVENT_BREAKER_ENABLE = true` in this add-on's `props.conf` is what makes that
safe. A UF ignores `LINE_BREAKER`, and when it rotates to the next indexer it
will cut the stream mid-event unless an event breaker tells it where the
boundaries are. The symptom is truncated and merged events that look like a
regex bug and are not one.

There is no universal forwarder in the SC4S path. SC4S posts to HEC on the
indexers directly.

### If you only install it on the search head

Search-time extractions are declared on the parent `wallix:bastion` sourcetype
as well as on each routed one, so you still get fields. You lose the per-family
sourcetype split and the CIM mapping that hangs off it. Useful for a quick
look, not a deployment.

### How to install it

**Splunk Enterprise, from Splunkbase.** *Apps > Find More Apps*, search
`WALLIX Bastion Add-on`, *Install*. Or download the archive and use
*Apps > Manage Apps > Install app from file*.

**Splunk Enterprise, by hand.** Unpack the archive into
`$SPLUNK_HOME/etc/apps/` so that `TA-wallix-bastion/default/` exists, keeping
the directory name `TA-wallix-bastion`.

Restart Splunk on every instance where you installed it. The sourcetype
routing is index-time and does not take effect until the parsing tier has
restarted.

**Search head cluster.** Place it in the deployer's `etc/shcluster/apps/` and
push with `splunk apply shcluster-bundle`. Do not copy it onto the members by
hand.

**Splunk Cloud.** Install from the Splunkbase tab in Splunk Web.

**Your own settings go in `local/`.** Anything you put in `default/` is
replaced on the next upgrade.

---

## 4. Getting the data in

### On the Bastion — syslog, and only syslog

**System → SIEM Integration** → add the collector address and port, then pick
the syslog format. Both formats are supported by this add-on.

Prefer **TCP**. RDP clipboard and process events routinely exceed 1400 bytes and
UDP will truncate or drop them, which looks exactly like a parsing bug.

### On the Splunk side

### Pick one !!!

**a. Splunk Connect for Syslog (SC4S) — recommended.**
SC4S ships a WALLIX Bastion source. Override its sourcetype so it lands here:

```bash
# /opt/sc4s/env_file - a dedicated port makes the vendor assignment
# deterministic. SC4S's built-in WALLIX filter otherwise matches on
# host('^wasb'), and silently misses appliances named anything else.
SC4S_LISTEN_WALLIX_BASTION_TCP_PORT=2242
```

```csv
# /opt/sc4s/local/context/splunk_metadata.csv - without the sourcetype line
# the data arrives as WB:syslog, the legacy sourcetype, and the index-time
# routing never runs.
wallix_bastion,index,wallix_bastion
wallix_bastion,sourcetype,wallix:bastion
```

If you need sc4s full runbook, including HEC on the indexers, check link below: 
`SC4S-DEPLOYMENT-podman.md`: https://github.com/traoreamara/Splunk/blob/f51bdfa7834ca284023d679f21dcc31e62605f10/Splunkbase/WALLIX/sc4s-wallix-podman-deployment.md
or
`SC4S-DEPLOYMENT-docker.md`: https://github.com/traoreamara/Splunk/blob/f51bdfa7834ca284023d679f21dcc31e62605f10/Splunkbase/WALLIX/sc4s-wallix-docker-deployment.md
.

**b. Direct TCP input.** Create the stanza yourself in `local/inputs.conf`. A
**heavy forwarder** is required for the index-time routing to run before the
event reaches the indexer. Simple, but Splunk's own raw TCP input is the least
resilient of the options — it has no disk buffer, so a restart loses whatever
was in flight.

```ini
[tcp://2242]
sourcetype = wallix:bastion
index = wallix_bastion
connection_host = ip
```

No `inputs.conf` is shipped: an input belongs to your deployment, not to the
add-on. Create it in `local/`. UDP truncates or drops anything past ~1400
bytes — most RDP clipboard and process events — so use `[udp://514]` only if
the Bastion cannot do TCP.

**c. Syslog relay writing files.** syslog-ng or rsyslog on a collector host
writes one file per Bastion; a universal forwarder monitors them. The files
give you a replay buffer the other options do not.

```ini
[monitor:///var/log/wallix/*.log]
sourcetype = wallix:bastion
index = wallix_bastion
host_segment = 4
crcSalt = <SOURCE>
```

**d. Relay converting syslog to HEC.** Only relevant on **Splunk Cloud**, where
you cannot open a raw TCP port on the stack and have no on-prem heavy forwarder.
SC4S, Cribl or Vector terminates the Bastion's syslog and forwards over HTTPS to
a HEC token configured with `sourcetype = wallix:bastion`,
`index = wallix_bastion`. The Bastion is not aware any of this is happening.
The token is yours to create and to keep out of the add-on.

```
Bastion ──syslog/TCP──▶ SC4S / Cribl / Vector ──HTTPS──▶ HEC ──▶ Splunk Cloud
```

### Create the index first

```ini
# indexes.conf on the indexers (or Splunk Cloud > Settings > Indexes)
[wallix_bastion]
homePath   = $SPLUNK_DB/wallix_bastion/db
coldPath   = $SPLUNK_DB/wallix_bastion/colddb
thawedPath = $SPLUNK_DB/wallix_bastion/thaweddb
```

No `indexes.conf` is shipped: the index belongs to your deployment. If you use
a different name, override the `wallix_bastion_index` macro in
`local/macros.conf`.

### Then add that index to the CIM scope

Required, and easy to miss: `Splunk_SA_CIM` scopes each data model to a list of
indexes, one macro per model, set independently. A model whose macro does not
list your index stays empty however correct the tags are.

```spl
| rest /services/admin/macros | search title="cim_*_indexes"
| table title, definition
```

`()` means unrestricted, nothing to do. Any macro that names indexes must
include yours - at minimum `cim_Authentication_indexes`,
`cim_Change_indexes`, `cim_Network_Traffic_indexes` and `cim_Endpoint_indexes`,
the four models this add-on populates:

```ini
# Splunk_SA_CIM/local/macros.conf, or Settings > Advanced search > Search macros
[cim_Authentication_indexes]
definition = (index=your_existing_indexes OR index=wallix_bastion)
```

---

## 5. Verify

In this order. The first one that comes back wrong names the layer at fault.

**Events are arriving**

```spl
index=wallix_bastion | stats count by sourcetype, host
```

Nothing at all is collection: the Bastion, the network path, or the input.

**The routing ran**

```spl
index=wallix_bastion | stats count by sourcetype
```

Everything sitting on the bare `wallix:bastion` means the routing never ran:
the add-on is missing from the parsing tier, or that tier was not restarted.

**The fields are there**

```spl
index=wallix_bastion sourcetype=wallix:bastion:session
| table _time, user, src, dest, wallix_service, wallix_type, action | head 20
```

**The data models are populated**

```spl
| tstats count from datamodel=Authentication
  where Authentication.authentication_service="wallix:bastion"
  by Authentication.action
```

Fields present but the model empty is almost always the CIM index scope - see
*Then add that index to the CIM scope* in section 4.

---

## 6. Fields and CIM mapping

Vendor fields are prefixed `wallix_`, keeping the WALLIX key name verbatim after
the prefix (`action="add"` → `wallix_action=add`). CIM fields are computed on
top of them.

| Data model | Sourcetypes | Tags |
|---|---|---|
| Authentication | `:auth`, `:session` | `authentication`, `privileged`, `default` |
| Change | `:audit`, `:vault` | `change`, `account` |
| Network Traffic | `:proxy`, `:session` | `network`, `communicate`, `session`, `start`, `end` |
| Endpoint / Processes | `:session` (`NEW_PROCESS`, `COMPLETED_PROCESS`) | `process`, `report`, `endpoint` |

WALLIX writes durations as `H:MM:SS`; the add-on converts them to seconds in
the CIM `duration` field and keeps the original in `wallix_duration`.

`vendor_product` is set on every event, but it is **not** a field of the CIM
Authentication data model. There, `authentication_service` is the handle on
WALLIX events - it is `wallix:bastion` on both `:auth` and `:session`. The
directory that answered the authentication is kept in `wallix_auth_domain` and
mapped to `src_nt_domain`. Change, Network Traffic and Endpoint do carry
`vendor_product`.

A data model that stays empty while the raw search returns events is almost
always the CIM index scope - see *Then add that index to the CIM scope* in
section 4.

In an estate with several appliances, `wallix_syslog_host` carries the name the
emitting Bastion put in its own syslog header. Splunk's `host` may say
something else entirely - the relay's address, or the collector's - depending
on how the stream reaches you.

### Security-relevant eventtypes (no CIM tag — for correlation searches)

```
wallix_bastion_session_integrity_failure   a session recording failed its integrity check
wallix_bastion_forbidden_pattern           PATTERN_FOUND / KILL_PATTERN_DETECTED
wallix_bastion_clipboard_exfiltration      clipboard copied OUT of a target
wallix_bastion_file_transfer               SFTP / RDP drive redirection
wallix_bastion_keystrokes                  KBD_INPUT
```

---

## 7. Search macros

```
`wallix_bastion`            all events
`wallix_bastion_auth`       primary authentication
`wallix_bastion_audit`      administration audit trail
`wallix_bastion_sessions`   privileged session activity
`wallix_bastion_vault`      credential checkout / checkin
`wallix_bastion_index`      index selector — override this one in local/
```

Examples:

```spl
| tstats count from datamodel=Authentication
  where Authentication.authentication_service="wallix:bastion"
        Authentication.action=failure
  by Authentication.user, Authentication.src

`wallix_bastion_sessions` wallix_type=CB_COPYING_PASTING_DATA_FROM_REMOTE_SESSION*
| stats count by src_user, user, dest, wallix_service

`wallix_bastion_audit` wallix_action=delete wallix_object_type=User
| table _time, user, src, object, object_attrs
```
---

## 8. Coming from `TA-WALLIX_Bastion` 1.0.x

Every `WB_*` field of the archived WALLIX add-on is provided as a `FIELDALIAS`,
and the legacy `WB:syslog` sourcetype is still recognised, so both add-ons can
run side by side. To get the CIM mapping, re-point your inputs to
`sourcetype = wallix:bastion`.

---

## 9. Companion app

`SA-wallix-advanced-monitoring` builds on this add-on: four Dashboard Studio
views over privileged access, session content, the administration audit trail
and the security signals, plus nine detections that ship unscheduled, so you
can run each one by hand and judge its threshold before enabling it. Like this
one it is pure configuration - no Python, no binaries.

---

## 10. Reporting a parsing problem

WALLIX emits seven log families across two envelope formats and two payload
dialects, and an appliance only sends what its SIEM Integration is configured
to send. If a family in your estate parses badly, these three searches say
what is wrong without exposing a single field value - which matters, because a
Bastion stream carries account names, targets, and for RDP and SSH sessions the
keystrokes and clipboard contents themselves.

**Which families arrive, and what fails to route:**

```spl
index=wallix_bastion | stats count by sourcetype
```

Anything left on the bare `wallix:bastion` is a family the routing does not
recognise.

**The message tags present, which is what the routing keys on:**

```spl
index=wallix_bastion
| rex "\[(?<message_tag>[A-Za-z][A-Za-z0-9 _-]{0,62})\]\s"
| stats count by message_tag
```

**The shape of an unrouted event, with every value removed:**

```spl
index=wallix_bastion sourcetype="wallix:bastion"
| eval shape=_raw
| rex mode=sed field=shape "s/=\"[^\"]*\"/=<...>/g s/='[^']*'/=<...>/g s/\b(\d{1,3}\.){3}\d{1,3}\b/<ip>/g"
| stats count by shape | head 10
```

The three outputs together identify the gap. They hold tags, sourcetypes,
counts and redacted skeletons - no values. Send those, never the events.

---

## 11. Support

Report problems through the Q&A tab of this add-on's Splunkbase page, with the
three outputs from section 10 attached. This add-on is community-maintained and
is not affiliated with or endorsed by WALLIX.
