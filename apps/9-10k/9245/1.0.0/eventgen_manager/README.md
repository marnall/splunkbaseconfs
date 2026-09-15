# Eventgen Manager

Configure, preview, and control [SA-Eventgen](https://splunkbase.splunk.com/app/1924)
from the browser instead of hand-editing `eventgen.conf`.

Eventgen is the standard way to put realistic data into Splunk for demos,
testing, detection development, and load work. Its configuration is powerful
and entirely file-based: a stanza per sample file, regular-expression tokens,
JSON rate curves, and a dozen output modes. This app puts a guided editor in
front of all of it, and shows you the events a configuration will produce
before a single one reaches an index.

---

## What it gives you

**A guided editor for every setting.** Interval, count, rate curves, output
mode, tokens, Jinja templates. Fields appear only when they apply, so choosing
HTTP Event Collector shows collector endpoints and hides the spool directory.
Every field is labelled with the setting it writes, so what you learn here
transfers straight to `eventgen.conf`.

**A live preview.** The centrepiece. As you edit, the preview pane renders the
events your configuration would generate, with every substituted value
highlighted. It runs entirely read-only — nothing is indexed, nothing is sent
anywhere — so you can get a regular expression right in seconds instead of
enabling a generator and searching for what came out.

**Rate curves you can see.** Hour-of-day and day-of-week rates are edited as
values per bucket rather than as a wall of JSON.

**Sample file management.** Upload, write, review, and delete the sample files
that configurations generate from, without shell access to the server.

**Generator control and health checks.** One page tells you whether
SA-Eventgen is installed, whether the modular input is running, and whether
anything is actually configured — with the fix one click away.

**Throughput monitoring.** Measured events per second against configured
events per second, projected volume per day, bottlenecks, and errors, read
from eventgen's own metrics in `_internal`.

---

## Requirements

- Splunk Enterprise 9.0 or later, or Splunk Cloud
- **SA-Eventgen** installed on the same instance. Install it from Splunkbase.
  Eventgen Manager writes configuration that SA-Eventgen reads; without it,
  configurations are stored correctly but nothing generates.
- The `admin` or `sc_admin` role to create or change configurations. Users
  with `list_inputs` can view them.

### Generation needs Linux or macOS

SA-Eventgen ships its generator as a compiled binary under platform
directories, and version 8.2.1 provides `linux_x86_64` and `darwin_x86_64`
only. There is no Windows build, and none for arm64.

On a Splunk instance outside those platforms, Splunk never registers the
`modinput_eventgen` scheme, so no events can be generated no matter how
things are configured. This is a property of SA-Eventgen, not of this app.
Generator control detects the situation and names it rather than guessing.

Everything else still works on any platform. Configurations and sample files
are read and written normally, and the preview is pure Python running
in-process, so you can build and verify configurations on a Windows instance
and run them on a Linux or macOS one.

---

## Installing

1. Install SA-Eventgen if it is not already present.
2. Install this app, either from Splunkbase or by extracting the package into
   `$SPLUNK_HOME/etc/apps/`.
3. Restart Splunk.
4. Open **Eventgen Manager** from the app menu.

---

## Quick start

Four starter configurations ship with the app — web access logs, Linux
authentication logs, structured application logs, and firewall traffic —
along with the sample files they generate from. All four arrive turned off.

1. Go to **Generator control** and confirm SA-Eventgen is installed and the
   modular input is running. If it is stopped, start it there.
2. Go to **Configurations**, pick a starter, and press **Clone**. Working on a
   clone means an app upgrade cannot overwrite your changes.
3. In the editor, watch the preview pane while you change the interval, the
   count, or a token. Adjust until the events look like what you need.
4. Tick **Generate events with this configuration** and save.
5. Search `index=main sourcetype=access_combined` (or whichever sourcetype the
   configuration writes) after one interval has passed.
6. Watch **Throughput** to confirm the measured rate matches what you asked
   for.

---

## How it stores things

| What | Where |
| --- | --- |
| Configurations you create or edit | `etc/apps/eventgen_manager/local/eventgen.conf` |
| Sample files | `etc/apps/eventgen_manager/samples/` |
| Starter configurations | `etc/apps/eventgen_manager/default/eventgen.conf` |
| Generator settings | `etc/apps/SA-Eventgen/local/inputs.conf` |

Configuration is read and written through Splunk's own
`configs/conf-eventgen` endpoint, so permissions, conf-layer precedence, and
search head cluster replication behave exactly as they do for any other
Splunk configuration.

The editor never discards settings it does not recognise. If you have added a
key by hand that this app has no field for, it is listed on the Sample tab as
preserved and written back untouched when you save.

Configurations belonging to other apps are listed read-only. Use **Clone** to
copy one into a location you can edit.

### Reinstalling the app resets the starter configurations

The starter configurations ship switched off in `default/`, and turning one on
writes `disabled = false` to `local/eventgen.conf`. Deleting the app directory
during a reinstall removes `local/` along with it, so the starters revert to
off and stop producing events. Extracting a new version over the existing
directory keeps `local/` intact.

Cloning a starter before changing it avoids this entirely: a clone exists only
in `local/`, with no `default` layer beneath it to fall back to.

### Keeping custom samples across upgrades

Sample files live in `samples/` inside the app, which is where eventgen looks
by default and what keeps stanzas portable between instances. Configurations
themselves are safe across upgrades because they are written to `local/`, but
that convention does not extend to the samples folder.

If a sample file matters to you, either keep a copy outside Splunk, or point
the configuration at a directory of your own using the **Sample directory**
field on the Basics tab. An absolute path there is never touched by an app
upgrade.

### The Rated replacement type is broken in SA-Eventgen 8.2.1

`rated` is documented in SA-Eventgen's own `eventgen.conf.spec`, but its 8.2.1
generator rejects the value and substitutes nothing, logging `No random token
type detected for replacement`. A numeric field left empty is merely untidy in
a plain-text event; in a JSON event it produces `"latency_ms":` with no value,
which is invalid JSON, so a sourcetype carrying `INDEXED_EXTRACTIONS = json`
discards the whole event. Nothing reaches the index and the generator reports
success regardless.

The starter configurations therefore use **Random** where **Rated** would be
the natural choice, and the editor says so beside the setting. Event *counts*
still follow the hour-of-day and day-of-week curves; only per-token rating is
affected. The preview implements `rated` faithfully, so a configuration using
it looks correct there and still produces blanks once it runs.

---

## Notes on the preview

The preview reimplements eventgen's token replacement so it can run without
starting a generator. It covers static, timestamp, replay timestamp, random,
rated, file, multi-value file, and counter replacements, along with event
breaking, CSV samples, rate curves, count jitter, and timezones.

Three things are approximations, and the interface says so where it matters:

- Rate curves scale the reported event count rather than the wall-clock pace.
- Replay-timestamp offsets are derived from the events shown, not from a full
  pass over the sample file.
- Custom `generator` and `rater` plugins are not executed. A stanza using one
  previews as the built-in behaviour.

For anything else, what the preview shows is what eventgen produces.

---

## Troubleshooting

**Configurations are enabled but no events appear.** Check **Generator
control**. The most common causes are that the SA-Eventgen modular input is
disabled — it ships that way and has to be started once — or that the
instance is running an operating system SA-Eventgen has no generator for.
The status list distinguishes the two.

**Configurations are enabled but eventgen writes no logs at all.** Check
whether the modular input is genuinely running, rather than trusting the page:

    | rest /servicesNS/-/-/data/inputs/modinput_eventgen
    | table title, disabled

A `disabled` value of 1 means the generator is off, and eventgen will not log
anything at all until it is on.

**Generator control says SA-Eventgen cannot run on this platform.** The app
is installed, but the copy on this instance carries generator binaries only
for the platforms it lists. See "Generation needs Linux or macOS" above.

**Events appear with the wrong timestamps.** The `earliest` and `latest`
settings decide the window timestamps land in. Setting both to `now` stamps
events at generation time. Check the `timezone` setting if offsets look wrong.

**A token does not replace anything.** The preview warns about tokens that
match nothing in the sample. Remember that a pattern with a capture group
replaces only the contents of the first group, and that tokens run in order,
so a later token sees the output of the earlier ones.

**Permission errors when saving.** Creating and changing configurations needs
the `admin` or `sc_admin` role.

**Nothing to see on the Throughput page.** Those panels read
`index=_internal source=*/var/log/splunk/eventgen_metrics.log`. Confirm the
generator has been running for at least one interval and that your role can
search `_internal`.

---

## Binary File Declaration

This app contains no binary executables. Everything shipped is Python source,
JavaScript, CSS, XML, PNG icons, and plain-text sample data.

## A note on the sample data

Every address in the bundled sample files comes from the ranges RFC 5737 and
RFC 2606 reserve for documentation — `192.0.2.0/24`, `198.51.100.0/24`,
`203.0.113.0/24`, and `example.com`. Nothing in them refers to a real host,
network, or person.

---

## Release notes

### 1.0.0

First release.

- Guided editor covering the full `eventgen.conf` setting surface, with
  fields shown conditionally by generation mode and output mode
- Live event preview with per-value highlighting, running read-only
- Token editor with ordering, and index renumbering so eventgen never sees a
  gap in the sequence
- Bucket editors for hour-of-day and day-of-week rate curves
- Sample file upload, editing, and deletion
- Generator control with health checks and one-click remediation
- Pausing or starting a configuration takes effect immediately. The generator
  reads `eventgen.conf` only when it launches, so the app restarts the
  modular input after a change rather than leaving the new setting to be
  picked up whenever someone next restarts it by hand
- Throughput dashboard measuring what actually reached an index, filterable
  by sample and time, comparing measured against configured rates
- Four starter configurations and six sample files, shipped turned off
- Platform detection, so an instance that cannot run SA-Eventgen is told so
  plainly instead of being told the app is missing
---

## Licence

Apache License 2.0. See `LICENSE`.

Eventgen and Splunk are trademarks of Splunk LLC. This app is an independent
interface for the SA-Eventgen add-on and is not produced or endorsed by
Splunk LLC.
