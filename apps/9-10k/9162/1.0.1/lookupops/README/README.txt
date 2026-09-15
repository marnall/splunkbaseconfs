Federal AI LookupOps 1.0.0

Air-gap-first governance and AI-assisted review for Splunk lookup changes.
Inventory, validate, semantically diff, review, approve, publish with
verification, and roll back CSV and KV Store lookups — entirely inside
Splunk Enterprise. No external web app, database, cloud service, CDN,
telemetry, or runtime download. The optional AI Review Engine calls only a
customer-approved, behind-the-firewall LLM endpoint, server-side, with TLS
verification always enforced and zero authority over the workflow.

INSTALL
  1. Copy this app directory to $SPLUNK_HOME/etc/apps/lookupops and
     restart Splunk (required for the REST handler and collections).
  2. Map users or SAML groups to the shipped roles (lookupops_user,
     lookupops_reviewer, lookupops_publisher, lookupops_admin) or add the
     lookupops_* capabilities to your own roles.
  3. Open the app; the Setup view verifies the endpoint, KV Store, and
     your capabilities.

REQUIREMENTS
  Splunk Enterprise 9.x with KV Store enabled. Python 3 (bundled with
  Splunk). Install on search heads only.

UPGRADE / UNINSTALL
  default/ holds only shipped defaults; all customer data lives in KV
  Store and survives upgrades. Uninstall details and retained-data notes:
  COMPATIBILITY.md in the source distribution.

SUPPORT
  LC@federal.ai | www.federal.ai

Federal AI builds mission-focused AI and analytics for secure,
disconnected environments. We help air-gapped teams turn complex
operational data into trusted decisions without adding cloud dependencies
or unnecessary infrastructure. Supporting air-gapped missions since 2017.
