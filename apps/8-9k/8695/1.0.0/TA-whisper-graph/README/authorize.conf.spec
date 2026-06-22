# @placement search-head
#
# Role definitions for Whisper Security TA.
#
# Defines the whisper_user role that grants access to Whisper
# search commands and knowledge objects without requiring admin privileges.
#

[role_whisper_user]
importRoles = <string> Comma-separated list of roles to inherit from.
srchIndexesAllowed = <string> Semicolon-separated list of indexes this role can search.
srchIndexesDefault = <string> Default index for searches by this role.
