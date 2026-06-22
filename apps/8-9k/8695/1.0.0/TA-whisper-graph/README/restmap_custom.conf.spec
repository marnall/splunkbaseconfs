# @placement search-head
#
# Custom REST endpoint mappings for Whisper Security TA.
#
# Defines the test connectivity REST endpoint used to validate
# API key and connectivity during configuration.
#

[admin:whisper_test_connectivity]
match = <string> URL path pattern for the REST endpoint.
members = <string> Comma-separated list of endpoint members.

[admin_external:whisper_test_connectivity]
handlertype = <string> Handler type (python).
handlerfile = <string> Python script filename that handles requests.
handleractions = <string> Comma-separated list of supported REST actions.
python.version = <string> Python interpreter version (python3).
python.required = <string> Comma-separated supported Python versions.
