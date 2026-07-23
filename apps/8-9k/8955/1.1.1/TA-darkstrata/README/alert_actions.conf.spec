# DarkStrata Adaptive Response Actions Specification
# This file documents the parameters for DarkStrata alert actions

# ============================================================================
# Acknowledge Alert Action
# ============================================================================
[darkstrata_acknowledge_alert]

param.account = <string>
* Required. The name of the DarkStrata account configuration to use.
* Must match an account configured in the TA-darkstrata Configuration page.

param.alert_id = <string>
* Required. The DarkStrata alert ID to acknowledge.
* Can be extracted from notable events using the alert_id field.
* Format: UUID (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ============================================================================
# Close Alert Action
# ============================================================================
[darkstrata_close_alert]

param.account = <string>
* Required. The name of the DarkStrata account configuration to use.
* Must match an account configured in the TA-darkstrata Configuration page.

param.alert_id = <string>
* Required. The DarkStrata alert ID to close.
* Can be extracted from notable events using the alert_id field.
* Format: UUID (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ============================================================================
# Reopen Alert Action
# ============================================================================
[darkstrata_reopen_alert]

param.account = <string>
* Required. The name of the DarkStrata account configuration to use.
* Must match an account configured in the TA-darkstrata Configuration page.

param.alert_id = <string>
* Required. The DarkStrata alert ID to reopen.
* Can be extracted from notable events using the alert_id field.
* Format: UUID (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ============================================================================
# Get Alert Details Action (Enrichment)
# ============================================================================
[darkstrata_get_alert_details]

param.account = <string>
* Required. The name of the DarkStrata account configuration to use.
* Must match an account configured in the TA-darkstrata Configuration page.

param.alert_id = <string>
* Required. The DarkStrata alert ID to retrieve.
* Can be extracted from notable events using the alert_id field.
* Format: UUID (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
