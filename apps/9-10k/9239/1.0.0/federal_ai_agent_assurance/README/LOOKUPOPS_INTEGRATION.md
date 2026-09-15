# LookupOps Integration (optional, read-only)

Agent Assurance works fully without Federal AI LookupOps. When both are
deployed: export a LookupOps JSON evidence report and import it via
Evidence -> dependencies (or POST /services/faaa/dependencies/
import-lookupops). The link retains lookup id, LookupOps evidence id,
approved content hash, policy version, publication time, import
provenance, report root hash, and a materiality rule.

When a later verified lookup hash differs (report-change endpoint), every
affected release receives deterministic drift evidence; material/critical
dependencies mark the authorization for reassessment (critical may
auto-suspend if configured). Old and new evidence links are preserved.

The integration never reads LookupOps KV collections or private files and
never writes LookupOps state. Narrative: LookupOps governs what the agent
depends on; Agent Assurance governs what the agent is permitted to do
with it.
