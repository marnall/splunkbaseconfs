# Specification for the alert actions this app defines.
#
# Splunk reads this file to validate a customer's local/alert_actions.conf and
# the app inspector reads it to check that every action the package ships is
# declared. A parameter the action reads and does not declare here is one no
# operator can discover.
#
# Credential values are never declared here. The API key lives in encrypted
# credential storage under the realm bin/ps_client.py names, never in a .conf
# file, so no stanza in this specification will ever carry a key, token or
# password setting.

[polyswarm_detonate]

* PolySwarm Detonate. Submits a URL from a search result to PolySwarm sandbox
  detonation and records each task in the ps_sandbox_tasks KV store collection,
  which is what the Sandbox Tasks dashboard shows and what the task poller
  follows.
* Runs bin/action_detonate.py with --execute and the JSON alert payload on
  standard input.
* METERED. One detonation books a virtual machine and runs a browser in it. An
  Enterprise plan includes 30 detonations a month, where the same plan's API
  request allowance is measured in thousands.
* Attaching this action to a saved search is the opt-in. No correlation search
  in this package uses it.
* The community each detonation is scoped to is resolved exactly as it is for
  the polyswarmdetonate command: the setting on the app's setup page if there
  is one, else the most private community the account is entitled to, else the
  platform default. See README/polyswarm.conf.spec.
* The provider and the VM are the command's defaults, triage and
  windows11-21h2-x64, and both are validated against the providers PolySwarm
  lists for this key before anything is spent.

param.field = <string>
* The result field holding the URL to detonate.
* A row whose field is absent or empty is skipped. So is a value with no
  http:// or https:// scheme, and one carrying whitespace, which is not a
  single URL.
* Duplicate URLs within one firing are detonated once.
* Default: url.

param.max_detonations = <integer>
* How many matching rows one firing may detonate.
* Rows above this number are not detonated, and the alert's own status reports
  how many were left.
* Must be at least 1. Remove the action from the search rather than setting it
  to zero.
* Cannot exceed 5, and a larger configured value is reduced to it rather than
  refused. That limit is in code, at MAX_DETONATIONS_HARD_CAP in
  bin/action_detonate.py.
* Default: 1.

param._cam = <json>
* The common action model declaration, which is what registers this action as
  an adaptive response action in Splunk Enterprise Security. Read by Enterprise
  Security and never by this app.
* NOT A SETTING TO EDIT. It is metadata about what the action does, not a
  choice about how it runs, and the action's configuration form neither shows
  it nor writes it. The shipped value is in default/alert_actions.conf with a
  line of reasoning for every key in it.
* Its keys and their recommended values are Splunk's, defined in Appendix A of
  Splunk_SA_CIM/README/alert_actions.conf.spec and in the cam_categories,
  cam_tasks and cam_subjects lookups shipped in that same package.
* What the shipped value declares: category Information Gathering, task scan,
  subject network and process.sandbox, the app's own vendor, product and
  version, ad hoc invocation supported, cloud supported, and a drilldown to the
  app's Sandbox Tasks view.
* On a search head without Enterprise Security this setting does nothing at
  all. The action behaves exactly as it did before it was added.
* Optional. Removing it leaves a working Splunk alert action that Enterprise
  Security will not offer as an adaptive response.
