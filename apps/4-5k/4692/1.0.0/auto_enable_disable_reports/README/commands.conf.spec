# Version 1.0.0
#
# This file contains possible attribute/value pairs for creating search
# commands for any custom search scripts created.
# 
# You must restart Splunk to enable configurations.

[disablesearch]
* Custom command to disable or enable a search
* The stanza name invokes the command in the search language

filename = <string>
* Optionally specify the program to be executed when the search command is used.
* Splunk looks for the given filename in the app's bin directory.
* The filename attribute can not reference any file outside of the app's bin directory.
* If the filename ends in ".py", Splunk's python interpreter is used
  to invoke the external script.
* If chunked = true, Splunk looks for the given filename in
  $SPLUNK_HOME/etc/apps/MY_APP/<PLATFORM>/bin before searching
  $SPLUNK_HOME/etc/apps/MY_APP/bin, where <PLATFORM> is one of
  "linux_x86_64", "linux_x86", "windows_x86_64", "windows_x86",
  "darwin_x86_64" (depending on the platform on which Splunk is
  running on).
* If chunked = true and if a path pointer file (*.path) is specified,
  the contents of the file are read and the result is used as the
  command to be run. Environment variables in the path pointer
  file are substituted. Path pointer files can be used to reference
  system binaries (e.g. /usr/bin/python).

local = [true|false]
* If true, specifies that the command should be run on the search head only
* Defaults to false

generating = [true|false]
* Specify whether your command generates new events. If no events are passed to
  the command, will it generate events?
* Defaults to false.

supports_rawargs = [true|false]
* Specifies whether the command supports raw arguments being passed to it or if
  it prefers parsed arguments (where quotes are stripped).
* If unspecified, the default is false

passauth = [true|false]
* If set to true, splunkd passes several authentication-related facts
  at the start of input, as part of the header (see enableheader).
* The following headers are sent
  * authString: psuedo-xml string that resembles
      <auth><userId>username</userId><username>username</username><authToken>auth_token</authToken></auth>
    where the username is passed twice, and the authToken may be used
    to contact splunkd during the script run.
  * sessionKey: the session key again.
  * owner: the user portion of the search context
  * namespace: the app portion of the search context
* Requires enableheader = true; if enableheader = false, this flag will
  be treated as false as well.
* Defaults to false.
* If chunked = true, this attribute is ignored. An authentication
  token is always passed to commands using the chunked custom search
  command protocol.

[updateschedule]
* Custom command to disable or enable a search
* The stanza name invokes the command in the search language

filename = <string>
* Optionally specify the program to be executed when the search command is used.
* Splunk looks for the given filename in the app's bin directory.
* The filename attribute can not reference any file outside of the app's bin directory.
* If the filename ends in ".py", Splunk's python interpreter is used
  to invoke the external script.
* If chunked = true, Splunk looks for the given filename in
  $SPLUNK_HOME/etc/apps/MY_APP/<PLATFORM>/bin before searching
  $SPLUNK_HOME/etc/apps/MY_APP/bin, where <PLATFORM> is one of
  "linux_x86_64", "linux_x86", "windows_x86_64", "windows_x86",
  "darwin_x86_64" (depending on the platform on which Splunk is
  running on).
* If chunked = true and if a path pointer file (*.path) is specified,
  the contents of the file are read and the result is used as the
  command to be run. Environment variables in the path pointer
  file are substituted. Path pointer files can be used to reference
  system binaries (e.g. /usr/bin/python).

local = [true|false]
* If true, specifies that the command should be run on the search head only
* Defaults to false

generating = [true|false]
* Specify whether your command generates new events. If no events are passed to
  the command, will it generate events?
* Defaults to false.

supports_rawargs = [true|false]
* Specifies whether the command supports raw arguments being passed to it or if
  it prefers parsed arguments (where quotes are stripped).
* If unspecified, the default is false

passauth = [true|false]
* If set to true, splunkd passes several authentication-related facts
  at the start of input, as part of the header (see enableheader).
* The following headers are sent
  * authString: psuedo-xml string that resembles
      <auth><userId>username</userId><username>username</username><authToken>auth_token</authToken></auth>
    where the username is passed twice, and the authToken may be used
    to contact splunkd during the script run.
  * sessionKey: the session key again.
  * owner: the user portion of the search context
  * namespace: the app portion of the search context
* Requires enableheader = true; if enableheader = false, this flag will
  be treated as false as well.
* Defaults to false.
* If chunked = true, this attribute is ignored. An authentication
  token is always passed to commands using the chunked custom search
  command protocol.