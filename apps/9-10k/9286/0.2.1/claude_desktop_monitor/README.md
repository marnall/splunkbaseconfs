# claude_desktop_monitor

## Summary
This app monitors Claude Desktop by collecting local application logs, MCP server logs, session transcripts, and Cowork virtual machine logs. It applies field extractions at index time and includes dashboards for operational analysis.

## Short description
This app monitors Claude Desktop by collecting local application logs, MCP server logs, session transcripts, and Cowork virtual machine logs.

## Details
This app monitors Claude Desktop by collecting local logs.

This App provides inputs and source type definitions for ingesting the following logs, along with predefined dashboards for analyzing them.

- Logs to be ingested
  - main.log
  - mcp*.log
  - coworkd.log
  - cowork_vm_*.log
  - claude.ai-web.log
  - ssh.log
  - unknown-window.log

- Dashboards
  - analytics
  - troubleshooting
  - MCP Server

## Installation
This App combines visualization functionality and data ingestion functionality.
In other words, Add-on functionality is included within this App.
For this reason, please install this App on all of your Search Heads, Indexers, and Forwarders.

- If you are using Splunk Enterprise
Install this App on all Search Heads, Indexers, and Forwarders.
Install a Forwarder on the machine where Claude Desktop is running.
After installation, create the claude_desktop_monitor/local directory and configure inputs.conf.
By default, the dashboards search across all indexes (`index=*`), as defined by the `claude_index` search macro. To improve search performance, narrow the scope of `claude_index` as needed.
(Go to Settings - Advanced search - Search macros, select the `claude_index` macro, and edit its Definition.)

- If you are using Splunk Cloud
Install this App on Splunk Cloud, the Intermediate Forwarder, and the Forwarder.
Install a Forwarder on the machine where Claude Desktop is running.
After installation, create the claude_desktop_monitor/local directory and configure inputs.conf.
By default, the dashboards search across all indexes (`index=*`), as defined by the `claude_index` search macro. To improve search performance, narrow the scope of `claude_index` as needed.
(Go to Settings - Advanced search - Search macros, select the `claude_index` macro, and edit its Definition.)


- Sample entries for $SPLUNK_HOME/etc/apps/claude_desktop_monitor/local/inputs.conf
  - If Claude Desktop's log path is C:\Users\*\AppData\Roaming\Claude\logs (Windows) or /Users/*/Library/Logs/Claude (Mac):
    The monitor stanza and sourcetype are already defined in default/inputs.conf, so setting `disabled = 0` is enough to enable monitoring. Specify the destination index as needed.
---
[monitor://C:\Users\*\AppData\Roaming\Claude\logs\main.log]
disabled = 0
index = claude
:
---


  - If Claude Desktop's log path is anywhere other than C:\Users\*\AppData\Roaming\Claude\logs (Windows) or /Users/*/Library/Logs/Claude (Mac):
    You need to define a new monitor stanza in local/inputs.conf with `disabled = 0`, `sourcetype`, and (optionally) `index`.
---
[monitor://C:\Users\*\AppData\Local\Claude-3p\logs\main.log]
disabled = 0
sourcetype = claude:desktop:main
index = claude
---


## Troubleshooting
Q1. I can't find Claude Desktop's logs on my machine. Where are they located?
A1. Claude Desktop's default log storage directories are as follows.
   - On Windows:
     - $APPDATA\Claude\logs ($APPDATA=C:\Users\<User>\AppData\Roaming)

However, if it was installed via MSIX, the location may instead be the one below.
In this case, please manually define the monitor stanza in inputs.conf.
   - On Windows (MSIX):
     - $LOCALAPPDATA\Packages\Claude_<Hash>\LocalCache\Roaming\Claude\logs ($LOCALAPPDATA=C:\Users\<User>\AppData\Local)

Please also refer to the following:
https://github.com/anthropics/claude-code/issues/25579

   - On Mac:
     - /Users/<User>/Library/Logs/Claude

If you need authoritative information, please refer to Claude Desktop's documentation or contact Anthropic.

Q2. Can this be used with Claude Desktop on 3P (Bedrock / Vertex AI etc)?
A2. Yes. However, when using Claude Desktop on 3P, the output paths for logs and configuration files differ. It will work if you configure inputs.conf manually.
   - On Windows
     - $LOCALAPPDATA\Claude-3p\logs (or $LOCALAPPDATA\Packages\Claude_<Hash>\LocalCache\Roaming\Claude-3p\logs)

   - On Mac
     - /Users/<User>/Library/Logs/Claude-3p

Please also refer to the following:
https://claude.com/docs/third-party/claude-desktop/data-storage

Q3. Are the bearer tokens contained in the logs forwarded to Splunk as-is?
A3. No. Bearer tokens contained in mcp*.log are masked to the string "***REDACTED***" via SEDCMD before being forwarded. However, since this may not be complete in cases such as when the log output format changes, we apologize for the inconvenience but ask that you also verify on your own that they are properly masked, just to be safe.


## Categories
* Artificial Intelligence
* Utilities
