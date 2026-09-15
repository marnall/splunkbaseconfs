QuantumGenie Add-on for Splunk (v1, in development)
=====================================================

Status: pre-Splunkbase-submission development skeleton. Not yet packaged,
not yet run against a real Splunk instance.

What this is
-------------
A Splunk modular input that pulls CBOM / cryptographic discovery records
from a QuantumGenie workspace into Splunk on a polling interval. This is an
Add-on (data collection/normalization), not a full App -- no dashboards or
custom views are included in v1. See docs/notes/Splunk App.md in the main
quantumgenie-web repo for the full architecture discussion.

Direction: QuantumGenie -> Splunk only, in v1. No write-back.

How it authenticates
---------------------
Each customer generates an "Integration API token" from inside their own
QuantumGenie workspace (Integration API Tokens settings page -- backend for
this exists as of this skeleton; the settings-page UI itself is still
pending). That token is entered into this Add-on's Splunk input
configuration (quantumgenie_url + api_token) and sent as:

    Authorization: Bearer <token>

against:

    GET /api/external/v1/cbom

This is a separate authentication path from QuantumGenie's own browser
session-cookie auth -- see src/middleware/external-api-auth.middleware.js
in the main repo. No existing session-authenticated routes were modified
to build this.

AppInspect notes
------------------
Ran locally via `splunk-appinspect inspect ... --mode precert`. Passing with
0 errors/failures as of this check. One deliberate choice: `python.required`
in default/inputs.conf is set to 3.9, matching what this add-on has actually
been tested against (the local Splunk 10.4.2 dev instance ships Python 3.9).
AppInspect's own forward-compatibility check suggests 3.13 instead, since
future Splunk versions are moving to bundle that -- but claiming 3.13
compatibility without having tested against it would be a guess, not a
verified fact. Revisit this once actually tested against a Splunk version
running Python 3.13.

What's NOT done yet
--------------------
- Not yet tested against a real running Splunk Enterprise instance (a local
  trial or Developer License should be used for this -- see the notes doc).
- No appIcon.png in static/ yet.
- No CIM (Common Information Model) field mapping yet -- props.conf /
  transforms.conf for sourcetypes quantumgenie:resource,
  quantumgenie:relationship, quantumgenie:certificate are not written.
- Not packaged as .tar.gz yet.
- Not run through Splunk AppInspect yet.
- Only the CBOM/relationship-explorer data source is wired up (reusing
  relationship-explorer.service.js). Certificates/findings-specific
  endpoints beyond that snapshot are not yet broken out separately.

Directory layout
------------------
default/app.conf         App metadata.
bin/quantumgenie_input.py  The modular input script (scheme, validation, run loop).
metadata/default.meta    Default permissions.
README/inputs.conf.spec  Defines the input's configurable fields for Splunk Web.
static/appIcon.png       Placeholder -- needs an actual icon before packaging.
