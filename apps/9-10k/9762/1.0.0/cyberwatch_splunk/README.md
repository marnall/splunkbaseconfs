# Cyberwatch

Dashboards for the data collected by the **Cyberwatch Add-on**:
vulnerability posture, prioritisation, compliance, estate inventory and
collection health.

This app reads what the add-on writes. It collects nothing, schedules nothing,
and writes nothing back.

## Prerequisite — the Cyberwatch Add-on

**Install and configure the Cyberwatch Add-on first.** This app has no data of
its own: without the add-on its ten dashboards are ten empty pages.

Two things have to be true before the dashboards show anything:

1. the add-on is installed, with an account pointing at your Cyberwatch
   instance;
2. its inputs are **enabled and have run at least once** — **Assets** and
   **Vulnerabilities** at a minimum. An installed add-on that collects nothing
   leaves this app just as empty as no add-on at all.

Add **CVE catalog** if you want the CVE description, CWE, exploit maturity and
EUVD reference: those fields come from a KV store lookup and stay empty until it
has run. The views say so rather than drawing an empty chart.

## Compatibility

| | |
|---|---|
| Splunk Enterprise | 9.1 and above |
| Splunk Cloud Platform | Victoria and Classic |
| Requires | Cyberwatch Add-on 1.0.0 or later |
| Dashboards | Dashboard Studio, light and dark |


## Install

**Install on the search heads, set one macro. That is all.**

The app holds no inputs, no scripts and no index-time settings, so it does not
belong on indexers or forwarders and it needs no restart.

It grants no capability to any role. Reading its dashboards needs access to the
index you gave the add-on's inputs.

**Settings > Advanced search > Search macros > `cyberwatch_index`.**

```spl
index=cyberwatch
```

Change `cyberwatch` to the index the add-on writes to.


## The views

| View | For | Answers |
|---|---|---|
| **Posture** | management | Where do we stand, in five seconds |
| **Priorities** | operations | What to fix first |
| **CVE** | technical | One CVE across the estate |
| **Asset** | technical | One asset, everything known about it |
| **Inventory** | management | The estate by hardware and operating system |
| **Compliance** | operations | How the estate scores against its repositories |
| **Rule** | technical | One compliance rule across the estate |
| **Security issues** | operations | Cyberwatch's own security issues |
| **Network discovery** | operations | What is on the network and unmanaged |
| **Collection health** | technical | Is the data fresh enough to be trusted |

Start at **Posture**. **Collection health** is the one to open when a number
looks wrong: it shows how old each asset's analysis is, which usually explains
it.

## Support

**support@process-it.fr**

## Licence and attribution

Apache License 2.0. Author: Thomas Dussossoy, Process-IT.

Cyberwatch is a trademark of its owner. This app is built by Process-IT for use
with Cyberwatch and is neither produced nor endorsed by Cyberwatch. Its icons
reproduce the Cyberwatch mark, to identify the product this app presents.
