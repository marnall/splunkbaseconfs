[api]
base_url = <string>
*AlphaSOC Analytics Engine base URL. Used by all API-calling components
*(findings modular input, search command, account status validation).
*Override only when pointing at a non-production AE (e.g. a staging
*deployment or a local dev instance).
*Validation rules enforced by the Settings UI:
*  - Must use http:// or https://.
*  - Must include a hostname; must NOT include credentials, a query
*    string, or a URL fragment.
*  - Plain http:// is accepted only for loopback hosts
*    (localhost / 127.0.0.1) since the API key is sent in the
*    Authorization header. HTTPS is required everywhere else.
*Default: https://api.alphasoc.net

[findings]
index = <string>
*Splunk index where AlphaSOC findings are stored. Two roles:
*  1. Default target index for the `a4s_findings` modular input when
*     its own `index` setting is unset.
*  2. Source index for the `alphasoc` search command (via the
*     `alphasoc_findings` macro).
*Editing this value through the Settings UI automatically rewrites the
*`alphasoc_findings` macro in macros.conf to keep the search command in
*sync, i.e.: definition = index="<value>" sourcetype="alphasoc:finding:ocsf".
*Default: main
