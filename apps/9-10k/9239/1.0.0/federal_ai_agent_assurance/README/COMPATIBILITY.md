# Compatibility

| Splunk target | Basis | Status |
|---|---|---|
| 9.1 – 9.4 | Designed + static analysis (python3 handler, Simple XML 1.1, KV Store, persistconn — same mechanisms as the Splunkbase-approved LookupOps app) | UNTESTED in this build environment |
| 10.x | Designed + static analysis (python3-only, stdlib-only, dashboards v1.1) | UNTESTED in this build environment |
| 8.x and earlier | — | NOT SUPPORTED (python3-only handler, dashboards 1.1) |
| Universal forwarder / indexer | — | NOT SUPPORTED (search-head-only app) |

Python: code targets 3.7+ syntax; actually executed on CPython 3.10.12
during this build. 3.9/3.13 and Splunk-bundled interpreters were not
available; marked untested. `python.version = python3` is declared in
restmap.conf (the same configuration proven by the approved sibling app);
btool verification requires a live instance and is listed as a manual
step.

"Designed compatibility" and "static compatibility" above are analysis,
not test claims. No installed-and-tested compatibility is claimed for any
Splunk version in this build. See the build COMPATIBILITY_MATRIX.md.
