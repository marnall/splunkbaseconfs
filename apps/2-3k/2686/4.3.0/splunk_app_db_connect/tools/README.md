# Splunk DB Connect - Tools

This directory contains utility tools for interacting with the **Splunk DB Connect API**.
These scripts extend core functionality by automating common maintenance routines that are currently
performed manually.

## Requirements

- **Python**: 3.9 or higher
- **Splunk Enterprise**: 9.0 or higher
- **Splunk DB Connect**: 4.3.0 or higher

## Tools

Users will be prompted to select a tool upon execution.
Regardless of the tool selected, the following connection details are required:

- **Host**: Splunk instance hostname or IP.
- **Management Port**: Splunk management port (default 8089).
- **Credentials**: Username and Password for the Splunk instance.
- **DB Connect Port**: Port assigned to the Splunk DB Connect (Task Server).

### 1. Input Copier

Automates the cloning of inputs from one database connection to another.
**Required parameters during execution:**

- **Source Connection**: The name of the connection to copy from.
- **Destination Connection**: The name of the connection to copy to.

## Usage

Navigate to the `tools` directory within the Splunk DB Connect instance and execute the main script:

```shell
python tools.py
```

## Contributing

Users are encouraged to extend these tools and share new use cases with the community.

## Support

These tools are supported by Splunk in their original, unmodified form only. Any Customer
modifications, extensions, or custom logic are not supported.
