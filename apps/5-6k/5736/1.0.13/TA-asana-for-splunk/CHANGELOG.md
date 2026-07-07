# Changelog

## [1.0.13] - 2026-05-07

### Fixed
- Added `python.required = 3.13` to the `[asana]` modular input stanza in `inputs.conf` to resolve `check_modular_inputs_python_required` AppInspect failure and maintain Splunk Cloud Platform compatibility. (`true` is deprecated as of Splunk 10.2.)
- Added `python.required = 3.13` to both `[admin_external:TA_asana_for_splunk_settings]` and `[admin_external:TA_asana_for_splunk_asana]` stanzas in `restmap.conf` to resolve `check_admin_external_restmap_conf_python_required` AppInspect failure. (`true` is deprecated as of Splunk 10.2.)

### Reviewed
- Reviewed custom Mako template (`appserver/templates/base.html`) for Python 3.13 compatibility (required for Splunk 10.2). No custom Python code blocks found — template only uses standard Splunk-provided helpers (`make_url`, `json_decode`, `cherrypy.request`). No changes required.

---

## [1.0.12] and earlier

No changelog recorded.
