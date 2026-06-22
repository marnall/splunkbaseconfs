Form Viz - Splunk Custom Visualization
=======================================

Version: 2.1.0

Form Viz renders SPL results as dynamic, interactive forms and stores
submissions in KV Store. Each submission captures the Splunk session
user, the form name, and the field order, alongside the question and
answer.

Requirements
------------
- Splunk Enterprise 9.x or 10.x (Cloud compatible)
- KV Store enabled

Input Schema
------------
SPL should return:
- question (required)
- type (required)
- options (required for dropdown/radio/checkbox; description text for description rows; SPL string for spl_display rows)
- order (optional, numeric)
- description (optional markdown helper text shown under the question
  label and above the input; description_above accepted as a legacy alias)

Supported Field Types
---------------------
- freetext      Text input
- dropdown      Select / dropdown menu
- radio         Radio button group
- checkbox      Multi-select checkbox group; saved as comma-joined values
- number        Number input
- date          Date input
- spl           Multi-line SPL input (monospace) with a Format button; tidied on blur
- description   Informational text block (no input), supports inline markdown
- markdown      Standalone markdown block (no input)
- spl_display   Read-only SPL block (no input), auto-formatted to one command per pipe

Panel Settings
--------------
Set in the visualization formatter:
- Form Name              Tag written to KV Store (default: form_viz_form)
- Output Lookup          KV Store collection (default: form_responses)
- Display Orders         Optional order filter, e.g. 1,2,3 or 1-5 or 5-9
- Capture User           Record $env:user$ on submit (default: Yes)
- Form Name Token        Dashboard token name (default: form_name)
- Output Lookup Token    Dashboard token name (default: form_output_lookup)

Dashboards can include type=form_name and type=form_kv_output rows to set
stable form metadata from SPL. Panel settings override them when Splunk
supplies a non-default formatter value.

Storage Model
-------------
KV Store records written per question:
- _time          Unix epoch
- timestamp      Human-readable timestamp
- submission_id  Unique id for this answer row, including its question order
- user           Splunk session user (from $env:user$)
- form_name      Form name from panel settings
- order          Field order value from the lookup
- question       Question label
- answer         User response

Identifying unique responses:
- form_name is NOT unique on its own; the same form can be submitted many
  times by many users.
- submission_id identifies one answer row and includes that row's question
  order. Use timestamp + user + form_name to group rows from one submit.
- Each KV Store record also has a unique _key (add `| eval k=_key`).

How submission_id is calculated:
- Generated in the browser when the user clicks Submit Form.
- Format:
  <milliseconds-since-epoch>-<form-name>-<question-order>-<splunk-user-or-anon>
- Example:
  1780291234567-triage_form-7-yuri
- The timestamp uses Date.getTime() from the user's browser.
- The form portion is the resolved form name.
- The question-order portion is the order value for that specific answered
  question, or noorder when the answered row has no numeric order value.
- The user portion uses the Splunk $env:user$ token when Capture User is
  enabled; otherwise it uses anon.
- Text parts are normalized to lowercase safe characters.
- It groups one submission batch; it is not a cryptographic identifier.

Query examples:
- | inputlookup form_responses | search form_name="triage_form"
- | inputlookup form_responses | sort -_time +order | table timestamp, submission_id, user, form_name, order, question, answer
- Latest submission per form+user:
  | inputlookup form_responses | stats max(_time) AS t latest(submission_id) AS submission_id BY form_name user
- Count distinct submissions per form:
  | inputlookup form_responses | stats dc(submission_id) AS submissions BY form_name

Ordering
--------
- If order exists and is numeric, fields render in ascending order
- Equal order values keep original SPL row order
- Rows without numeric order render after ordered rows
- Display Orders can render only part of a larger form definition, such as
  1,2,3 or 1-5 or 5-9. When set, rows without numeric order are hidden.

Dashboard Tokens
----------------
On submit, Form Viz sets:
- form_response: JSON of responses plus _form_name and _form_output_lookup
- form_name (configurable): current form name value
- form_output_lookup (configurable): current output lookup value

Known Limitations
-----------------
- Duplicate question labels cause token payload key collisions
- The target KV Store collection must exist and be writable
- For outputlookup updates of CSV lookups, keep the visualization and
  lookup in the same app context

Release Notes
-------------
v2.1.0
- Added Display Orders panel setting for rendering selected order
  numbers/ranges from a larger form definition.
- submission_id now uses <epoch-ms>-<form-name>-<question-order>-<user>.
- Submitted records include the question order whenever the answered row has
  one.
