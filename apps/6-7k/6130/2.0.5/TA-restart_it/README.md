# TA-restart_it

A Splunk add-on that exposes a custom SPL command, `restartinput`, for
restarting a Splunk input or scripted input via the REST API. Designed to be
paired with a saved search on a schedule so an input can be restarted on a
cadence without command-line access or external scripting.

## Why

Written to work around another add-on whose input needed periodic restarts.
Rather than a cron job invoking `splunk` CLI on the indexer, a scheduled SPL
search can just run `| restartinput ...`.

## Requirements

- Splunk Enterprise 9.3.x (uses `python.required = 3.9`).
- The invoking user needs the `admin_all_objects` and `rest_apps_management`
  role capabilities. These are privileged — scope the search to admin
  accounts.

## Install

Install like any Splunk add-on:

- Splunkbase: upload the packaged `.spl` / `.tgz` via
  **Apps → Manage Apps → Install app from file**.
- Manual: extract into `$SPLUNK_HOME/etc/apps/TA-restart_it` and restart
  Splunk.

## Usage

```
| restartinput app=<app> type=<type> input=<input>
| restartinput app=<app> type=script script=<script_name>
| restartinput app=<app> type=modular-input input=<stanza_name>
```

### Choosing arguments

`type=` takes a Splunk *input kind* — not the literal word "input". Match
the kind to how the input is declared in `inputs.conf`:

| inputs.conf stanza                  | command arguments                                       |
| ----------------------------------- | ------------------------------------------------------- |
| `[monitor:///var/log/foo.log]`      | `type=monitor input=/var/log/foo.log`                   |
| `[tcp://9997]`, `[udp://514]`, etc. | `type=tcp input=9997`, `type=udp input=514`             |
| `[script://./bin/myScript.sh]`      | `type=script script=myScript.sh`                        |
| `[itc_activity://my_input]`         | `type=modular-input input=my_input`                     |
| `[itc_activity://my_input]`         | `type=itc_activity input=my_input` (equivalent, faster) |

Use `type=modular-input` when you don't want to look up the modular input's
kind — the command will scan every kind on the server for a matching
stanza name. Pass the specific kind (e.g. `type=itc_activity`) for a
direct lookup. To enumerate kinds and stanza names on your instance:

```
| rest /servicesNS/-/-/data/inputs/all
```

If you pass a `type=` that isn't a real input kind, you'll get a
`KeyError`-style tuple in the result row (the underlying REST call 404s).
See [`README.txt`](./README.txt) for the canonical list of restartable
input types.

## Logging

Restart activity is logged to `$SPLUNK_HOME/var/log/splunk/restart_it.log` at
`INFO` level by default. Adjust the level from the add-on's configuration
page.
