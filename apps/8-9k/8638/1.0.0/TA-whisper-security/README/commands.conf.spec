# @placement search-head
#
# Custom search command definitions for Whisper Security TA.
#
# All commands use SCP v2 protocol (chunked=true) and require
# the whisper_user, admin, or sc_admin role.
#

[whisperlookup]
filename = <string> Python script filename for the lookup command.
chunked = <bool> Always true for SCP v2 protocol.
streaming = <bool> Whether the command processes events in streaming mode.
run_in_preview = <bool> Whether to execute during search preview.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.

[whisperquery]
filename = <string> Python script filename for the query command.
chunked = <bool> Always true for SCP v2 protocol.
generating = <bool> Whether the command generates events from scratch.
run_in_preview = <bool> Whether to execute during search preview.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.

[whisperschema]
filename = <string> Python script filename for the schema command.
chunked = <bool> Always true for SCP v2 protocol.
generating = <bool> Whether the command generates events from scratch.
run_in_preview = <bool> Whether to execute during search preview.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.

[whisperflush]
filename = <string> Python script filename for the flush command.
chunked = <bool> Always true for SCP v2 protocol.
generating = <bool> Whether the command generates events from scratch.
run_in_preview = <bool> Whether to execute during search preview.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.

[whisperevict]
filename = <string> Python script filename for the evict command.
chunked = <bool> Always true for SCP v2 protocol.
generating = <bool> Whether the command generates events from scratch.
run_in_preview = <bool> Whether to execute during search preview.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.
