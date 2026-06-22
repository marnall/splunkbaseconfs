# Enrollment Configuration Specification
# File permissions MUST be 0600 (owner read/write only)
#
# This file is used for zero-touch agent enrollment via Deployment Server.
# Place your enrollment token in local/enrollment.conf on the Deployment Server.
# See docs/SECURE_ENROLLMENT_PLAN.md for the full enrollment architecture.

[enrollment]
token = <string>
# Required. Enrollment token from the Deslicer AI portal.
# Format: dsle_enroll_<signed-JWT>
# Tokens are time-limited (default 30 days) and host-count limited.
# Revocable from the portal at any time.
# This token can ONLY enroll new hosts; it cannot access or ingest data.

observer_api_url = <string>
# Required. Your Deslicer Observer URL.
# Get it from deslicer.ai > Settings > Integrations > Splunk
# Format: https://your-tenant.dap.deslicer.ai
# Each Deslicer tenant has a unique Observer URL.
