# Installation

Requirements: Splunk Enterprise 9.x/10.x with KV Store enabled. Search
heads only — NOT supported on universal forwarders, indexers, or heavy
forwarders. No internet access, cloud service, LLM, live agent, or MCP
connection is required.

## Standalone
1. Copy `federal_ai_agent_assurance/` into `$SPLUNK_HOME/etc/apps/`
   (or install the packaged artifact via Splunk Web > Manage Apps >
   Install app from file).
2. CLI alternative: `$SPLUNK_HOME/bin/splunk install app
   federal_ai_agent_assurance-1.0.0.tar.gz`
3. Restart Splunk (required: REST handler + KV collections).
4. Assign roles (see below), open the app; Administration and Health
   verifies the endpoint, collections, and your capabilities without any
   external call.

## Search-head cluster
Deploy through the SHC deployer: place the app under
`$SPLUNK_HOME/etc/shcluster/apps/` on the deployer and run
`splunk apply shcluster-bundle`. All mutable state is in replicated KV
Store collections; nothing is written to app-local files at runtime.

## Capability assignment
Map users or SAML groups to `faaa_developer`, `faaa_reviewer`,
`faaa_authorizing_official`, or `faaa_admin`, or grant individual `faaa_*`
capabilities. Separation of duties is enforced by identity, not just
capability: granting every capability to one person still cannot
self-review/self-authorize.

## First-use validation
Administration and Health -> confirm all collections "ok" -> optionally
"Load labeled sample data" -> run the sample release through the workflow.
