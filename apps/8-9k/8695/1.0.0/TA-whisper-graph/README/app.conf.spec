#
# App configuration for Whisper Security TA.
#
# Defines install settings, UI properties, launcher metadata,
# package identity, diagnostics, and reload triggers.
#

[install]
is_configured = <bool> Whether the app has been configured. Default: 0.
state = <string> App state (enabled or disabled).
build = <integer> Build number.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.

[ui]
is_visible = <bool> Whether the app is visible in the Splunk UI.
label = <string> Display name shown in the Splunk UI.
docs_section_override = <string> Documentation section override for Splunk Docs.
setup_view = <string> Name of the setup view (configuration).
supported_themes = <string> Comma-separated list of supported UI themes.

[launcher]
author = <string> Author name displayed on Splunkbase.
version = <string> Semantic version of the app.
description = <string> Brief description of the app.

[package]
id = <string> Unique app identifier for Splunkbase.
check_for_updates = <bool> Whether to check Splunkbase for updates. Default: 0.

[diag]
extension_script = <string> Script to run during splunk diag for supportability.

[triggers]
reload.restmap_custom = <string> Reload trigger for restmap_custom.conf.
reload.web_custom = <string> Reload trigger for web_custom.conf.
