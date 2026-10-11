# Specification for polyswarm.conf.
#
# Every stanza and setting the app reads is documented here, so that Splunk's
# configuration validation and the app inspector can check a customer's
# local/polyswarm.conf against it. A setting the app reads but does not declare
# in this file is a setting no operator can discover.
#
# Credential values are never declared here. The API key lives in encrypted
# credential storage, not in a .conf file, so no stanza in this specification
# will ever carry a key, token, or password setting.

[settings]

community = <string>
* The PolySwarm community that sandbox detonations are scoped to.
* A non-blank value is sent as given, and nothing overrides it. The app makes
  no request to check it.
* Blank is a meaningful value and it is the default. It means the app resolves
  the community itself: it reads the entitled communities from your account and
  scopes the detonation to the most private one, which is any community other
  than the public one. That answer is cached for one hour.
* If your account is entitled to the public community only, blank sends the
  platform default and PolySwarm resolves the community your account belongs
  to. That is also what happens if the account lookup is unavailable, and the
  command reports it as a warning rather than failing the detonation.
* The task row in the ps_sandbox_tasks collection records the community each
  detonation actually ran in, whichever of those applied.
* This value scopes a detonation submit. It is not sent on the sandbox task
  status poll, which is a read by task id, and it is not sent on enrichment or
  the account endpoints, which take no community.
* Written by the app's setup page through splunkd's configs/conf-polyswarm
  endpoint, which lands it in local/polyswarm.conf.
* Default: empty.
