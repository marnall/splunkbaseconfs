# Ping Search Command for Splunk

## Overview

This Splunk app provides a custom streaming search command called `ping`, which performs ICMP ping checks to hosts or IP addresses in your events. It supports both Linux/macOS and Windows environments and returns the status of each ping attempt.

---

## Features

- Cross-platform support (Linux, macOS, Windows)
- Per-event ping checks using values from a specified field
- Output classification:
  - `success`: Ping succeeded
  - `unreachable`: Host responded but dropped packets
  - `timeout`: No response within the timeout window
  - `invalid_host`: Invalid or unresolvable hostname
  - `error`: Other failure during execution
  - `missing target`: Field value not present in the event

---

## Requirements

- Splunk Enterprise 8.0 or later
- Python 3.7+ (Python 3 runtime must be enabled in Splunk)
- ICMP access from the Splunk host to ping targets

---

## Installation

1. Copy or install the app into `$SPLUNK_HOME/etc/apps/ping_command`.
2. Restart Splunk or reload the app using the REST API:

```bash
curl -k -u admin:changeme https://localhost:8089/services/apps/local/ping_command/_reload -X POST

