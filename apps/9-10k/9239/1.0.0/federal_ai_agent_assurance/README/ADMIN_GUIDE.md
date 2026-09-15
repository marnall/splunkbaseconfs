# Administrator Guide

1. Install + restart (INSTALL.md); confirm Health all-green.
2. Assign roles/capabilities; decide the SoD posture (strict default vs.
   allow_reviewer_as_authorizer) — the choice is recorded in evidence.
3. Optionally load labeled sample data (Administration) to train users;
   archive the demo agent afterward.
4. Policies: clone baseline policies to custom versions as needed
   (faaa_manage_policies); built-ins stay immutable.
5. Optional AI: set provider/endpoint/model, store the credential
   (Settings -> credential; it goes to the Splunk secure store), then
   enable. TLS verification is always on.
6. Operations: watch Overview for expiring/drifted authorizations; use
   maintenance sweep (automatic on Overview load); export evidence
   bundles for records; verify audit chains periodically (Evidence view).
7. Backup: KV Store backup covers all app state; evidence bundles provide
   per-release portable records. Upgrades preserve KV data; default/ only
   ships defaults.
8. Self-test (faaa_selftest) writes and removes namespaced probe records
   and reports every action.
