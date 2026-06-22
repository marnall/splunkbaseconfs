# @placement search-head
#
# Alert action definitions for Whisper Security TA.
#
# Defines the "Enrich with Whisper" adaptive response action
# for Enterprise Security integration.
#

[whisper_enrich]
label = <string> Display name for the alert action.
description = <string> Description shown in the alert action selector.
icon_path = <string> Path to the icon displayed in the UI.
is_custom = <bool> Whether this is a custom alert action.
disabled = <bool> Whether the alert action is disabled.
payload_format = <string> Format of the payload (json).
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.
