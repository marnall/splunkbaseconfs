# Separation of Duties

Strict Federal baseline (default): the release creator/submitter cannot
independently review, accept risk, or authorize the same release; the
independent reviewer cannot accept risk or authorize it; a waiver
requester cannot approve the same waiver. Identity comes from the Splunk
session only — client-supplied identities are ignored, and recording the
same material decision under two client-claimed identities is therefore
impossible through this app. Splunk admin status does not bypass any of
this, and no emergency bypass exists.

Deployments with fewer officials may explicitly set
`allow_reviewer_as_authorizer` (Settings). The choice and the identities
involved are recorded in every evidence package.
