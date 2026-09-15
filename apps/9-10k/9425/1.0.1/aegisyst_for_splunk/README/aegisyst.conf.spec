# Spec for aegisyst.conf. Referenced by AppInspect + Splunk's manager UI.

[aegisyst]
api_key = <string>
* Long-lived Aegisyst API key (prefix: sk_aegisyst_...). Mint one at
  https://aegisyst.com/settings/keys and paste the raw value here.
* Required.
* No default.

hec_url = <url>
* HTTP Event Collector endpoint on this Splunk deployment. Reserved for
  future alert-forwarding features; not used by the puller today.
* Default: https://localhost:8088

aegisyst_api_url = <url>
* Base URL of the Aegisyst API. Change only for private / self-hosted
  Aegisyst instances.
* Default: https://aegisyst.com
