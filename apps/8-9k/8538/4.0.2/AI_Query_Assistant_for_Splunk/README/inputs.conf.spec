[mcp_license_heartbeat://default]
* RST License Server daily phone-home. Reads the locally-stored license,
* verifies remote state (revoke/expiry), and refreshes the cached signed
* token so an offline-grace boundary is never silently crossed.
*
* Splunk's modular-input introspection requires a README/inputs.conf.spec
* file in the app for the scheme to be picked up at startup. The single
* arg defined here is decorative — the heartbeat takes no per-instance
* tunables; everything (URL, app_id, offline_grace_days) lives in
* default/mcp.conf [license_server].
* No params required
param1 =
