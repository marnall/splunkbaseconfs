Directly access a remote Splunk from a Windows PowerShell session.  This PowerShell Cmdlet takes a search string as input and
returns the search results as XML.  It can be invoked from a Windows Powershell and directed at any remote Splunk Search Head
or Indexer.

PowerShell is an advanced command line shell (CLI) for Windows SAs or developers.  Including Splunk into the PowerShell ecosystem
means Splunk tasks and sessions can be scripted and automated or just provide a more convenient way of using Splunk and
searching log files.  Sometimes a web interface is not the most convenient UI.

As a bonus, the same search Cmdlet is implemented three different ways: pure PowerShell, C# and F#.  The C# or F# versions
can be useful if someone wants to extend or enhance the Cmdlet in interesting ways.

Examples:

ps> import-module .\searchsplunk
ps> $results = search-splunk "sourcetype=syslog Error" -port 8089 -host MySearchHead.com
ps> $xml = [XML]$results
ps> $xml.SelectNodes("/results/result/*")
ps> $xml

------------------

ps> add-type -path .\splunksearch.cs -OutputAssembly out.dll
ps> import-module .\out.dll
ps> $out = search-splunk "sourcetype=syslog error warn"
ps> $out

------------------
#
# Use the Option parameter to set the REST form variables such as max_count, earliest_time or timeout
# The REST API is documented here: http://www.splunk.com/base/Documentation/latest/Developer/RESTSearch

ps> $results = search-splunk "error" -Option "&max_count=20"

