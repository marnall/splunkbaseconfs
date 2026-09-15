# Splunkbase AppInspect Compliance Notes

## Logging
- bifrost_logs.py uses Python's logging module writing to
  $SPLUNK_HOME/var/log/splunk/ta_llmgateway.log (RotatingFileHandler).
- No operational messages are written to stderr. Only Splunk-bound events go to stdout.

## Bundled third-party library
- psycopg2-binary 2.9.12 is bundled to support the optional PostgreSQL backend
  without requiring pip on the Splunk host, as two platform-specific builds:
  bin/windows_x86_64/lib/psycopg2 (cp39 win_amd64) and
  bin/linux_x86_64/lib/psycopg2 (cp39 manylinux2014_x86_64). bifrost_logs.py
  selects the matching one at runtime via platform.system().
- Pure data-access library; no outbound network calls beyond the configured DB.
- Source: https://pypi.org/project/psycopg2-binary/

## Custom REST handler
- bin/setup_handler.py uses splunk.admin.MConfigHandler (Splunk SDK), no hardcoded
  paths. App home resolved via make_splunkhome_path.

## Scripted input
- bin/bifrost_logs.py uses only the Splunk-bundled sqlite3 for the default backend.
- Reads a local database file path supplied by the administrator via the setup page.
- No outbound network connections in the SQLite path.

## Network behaviour
- SQLite backend: local file reads only.
- PostgreSQL backend: connects only to the admin-configured PG host.
- LiteLLM (README/custom_callbacks.py) runs OUTSIDE Splunk on the LiteLLM host and
  pushes to Splunk HEC. It is reference material, not executed by Splunk.

## Reference callback SSL note
- README/custom_callbacks.py disables TLS verification for self-signed Splunk certs
  via a clearly commented line. Production deployments should remove that line and
  use a trusted certificate. This file is documentation only and is never run by
  Splunk itself.
