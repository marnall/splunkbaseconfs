[darkstrata_indicators://<name>]
account = Select the DarkStrata account to use
confidence_threshold = Minimum STIX confidence score (0-100). Only indicators with confidence >= this value will be collected. Maps to DarkStrata threat score: 20=Info, 40=Low, 60=Medium, 80=High, 100=Critical (Default: 0)
hash_emails = Hash email addresses using SHA-256 for privacy compliance
index = (Default: default)
interval = Collection interval in seconds. Minimum recommended: 300 (5 minutes) (Default: 300)

[darkstrata_alerts://<name>]
account = Select the DarkStrata account to use
confidence_threshold = Minimum STIX confidence score (0-100). Only indicators with confidence >= this value will be collected. (Default: 0)
detail = Level of detail to include in alert reports (Default: full)
hash_emails = Hash email addresses using SHA-256 for privacy compliance
include_identities = Include STIX Identity objects for each compromised credential (Default: true)
index = (Default: default)
interval = Collection interval in seconds. Minimum recommended: 300 (5 minutes) (Default: 300)
