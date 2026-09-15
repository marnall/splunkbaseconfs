[cyberhaven_update_status]
param.incident_id = <string> The Cyberhaven incident ID (the "id" field from the originating cyberhaven:incidents event, recovered from the linked notable event) to update on the Cyberhaven platform.
param.status = <string> The status value to set on the Cyberhaven incident (e.g., Closed). Sent to the Cyberhaven API in lowercase.
param.close_reason = <string> The Cyberhaven close_reason value, derived from the notable's disposition field. Constrained by the Cyberhaven Incidents API to one of: valid, invalid_user_exempt, invalid_data_mislabled, invalid_other.
param.close_note = <string> Free-text close_note sent alongside close_reason, formatted as "Closed by Splunk SIEM Integration: <disposition label>", e.g. "Closed by Splunk SIEM Integration: True Positive - Suspicious Activity". Mirrors the disposition-to-close_reason mapping.

[cyberhaven_update_owner]
param.incident_id = <string> The Cyberhaven incident ID (the "id" field from the originating cyberhaven:incidents event, recovered from the linked notable event) to update on the Cyberhaven platform.
param.owner = <string> The Splunk ES notable event owner's resolved real name (owner_realname, from user_realnames_lookup), sent as assigned_to to the Cyberhaven Incidents API.
