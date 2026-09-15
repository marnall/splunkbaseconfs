# Modular input spec for the license state monitor.
#
# ASCII ONLY. Splunk's .spec parser silently SKIPS a spec file containing
# non-ASCII bytes, and the modular input kind is then never registered
# (verified on the live instance 2026-07-26 -- a Korean-commented spec was
# absent from the SpecFiles scan while every ASCII spec was read).
#
# Required together with the [<kind>] stanza in default/inputs.conf.

[inno_observability_license_monitor://<name>]
* License state monitor. Emits periodic license_status events (no phone-home).
* Alert example: sourcetype=inno:license state!="active"
interval = <integer>
* How often, in seconds, to check the license. Default 3600.
