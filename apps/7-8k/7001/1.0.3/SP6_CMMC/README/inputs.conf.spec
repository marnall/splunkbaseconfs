[evidence_checks://<name>]
*Generates sp6_audit events showing the uploaded evidence status for all controls.
index=sp6_audit

[evidence_mod_time_checks://<name>]
*Generates sp6_audit events showing the latest mod time for all uploaded evidence.
index=sp6_audit

[review_overdue_checks://<name>]
*Generates a sp6_audit event for a control if the control review is overdue.
index=sp6_audit

[toggle_control_status_checks://<name>]
*Toggles a control's status based on the statuses of the control's objectives.
index=sp6_audit
