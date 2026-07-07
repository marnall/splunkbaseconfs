INFOTOOLS

What is/are infotools you ask???

This app is a collection of custom commands that let you see information from the search head that may normally require access to a command shell or file system.

In version 1.3.0 there are 12 custom commands:

| lookupinfo - see the location size and modtime of lookups (has alias lookupinfo2)

| bundleinfo - see what inside the latest search bundle

| userinfo - lists all files in the etc/users directory with size and modtime

| appinfo - lists all files in the etc/app directory with size and modtime

| btoolinfo - yet another btool output

| artifactinfo - view or search the info.csv file in search artifacts

| pinginfo - run a ping from your search head to measure latency or availability

| pinginfo2 - run a ping command from your search head (python only for Splunk Cloud compatibility)

| sslinfo - run the openssl s_client to view certificate details

| varinfo - see the size and modtimes of files in the splunk/var directory

| cliinfo - run the splunk cli commands: status, list, show, display, help

| specinfo - view the details of the .conf.spec files

Each of these commands is a generating command (must be first command in the pipeline) and return results about the file objects.

What is the use case for infotools?

Glad you asked...

In Splunk Cloud and with many on-premise deployments most users do not have access to the file system.
It can be very useful to be able to see details about some specific Splunk files to help with troubleshooting.

Splunk Cloud note: the btoolinfo and cliinfo commands will not run in Splunk Cloud due to the app jail feature that prevents those command from being run except by the splunk user.  It also appears that pinginfo is now 
blocked in Splunk Cloud by restricting permission to the OS ping command.


For example:

One of the most common problems in many environments is large lookups file affecting bundle replication
the restapi commands for lookups do not return information about the file size if the lookup is not defined in transforms.conf, so you need access to the file system to see this information

In a search head cluster, large lookups that are frequently updated can impact performance since the entire file is replicated to all members
since lookupinfo provides the file size and modtime, you can also see if a lookup has been recently updated


lookupinfo
==========
For support, please email sjohnson@splunk.com

Version 1.3.0

usage:

| lookupinfo

lookupinfo is a custom search command that will return information about the files contained in lookups directory for all apps on the search head where it is run
lookupinfo is a generating command and must be the first command in the pipeline
lookupinfo has no arguments
lookupinfo requires python3 to run
lookupinfo returns the following results:

app - the name of the app folder
name - the name of a file in the lookup folder
size - the size in bytes of the file
mtime - the modtime of the file in epoch format

lookupinfo returns ALL files found in the lookups folder, mostly this will be .csv files but also other files such as .gz, .kmz and the occasional README

Note: There can be another lookupinfo command on a search head (Enterprise Security for one), so there is an alias for this lookupinfo: lookupinfo2


bundleinfo
==========
For support, please email sjohnson@splunk.com

Version 1.3.0

usage:

| bundleinfo

bundleinfo is a custom search command that will return information about all the files contained in the most current search bundle (.bundle) on the search head where it is run
bundleinfo is a generating command and must be the first command in the pipeline
bundleinfo has no arguments
bundleinfo requires python3 to run
bundleinfo returns the following results:

bundlename - the full path and name of the bundle file
file - the name of a file in the bundle
size - the size in bytes of the file
mtime - the modtime of the file in epoch format


userinfo
==========
For support, please email sjohnson@splunk.com

Version 1.3.0

usage:

| userinfo

userinfo is a custom search command that will return information about all the user folders and files on the search head where it is run
userinfo is a generating command and must be the first command in the pipeline
userinfo has no arguments
userinfo requires python3 to run
userinfo returns the following results:

user - the user name (foldername) from the etc/users directory
app - the name of the app folder
fileobject - the path and name of a file(s) below the app
size - the size in bytes of the file
mtime - the modtime of the file in epoch format

appinfo
==========
For support, please email sjohnson@splunk.com

Version 1.3.0

usage:

| appinfo (app=appname)

appinfo is a custom search command that will return information about all the app folders and files on the search head where it is run
appinfo is a generating command and must be the first command in the pipeline
appinfo has an optional argument: app which is a app folder name.  This can also be a wildcard: */local will return only local folders in apps
appinfo requires python3 to run
appinfo returns the following results:

file - the path and name of a file(s) below the app
size - the size in bytes of the file
mtime - the modtime of the file in epoch format

btoolinfo
==========
For support, please email sjohnson@splunk.com

Version 1.3.0

usage:

| btoolinfo conf="conf file name"

example:

| btoolinfo conf="props"

btoolinfo will run a btool command with the --debug option for conf files on the search head where it is run
btoolinfo is a generating command and must be the first command in the pipeline
btoolinfo has an arguement confname= that should be the name of a valid .conf file - invalid names will return no results
btoolinfo requires python3 to run
btoolinfo returns the following results:

confpath - the full path the .conf file for the property
stanza - the name of the stanza with square brackets included
property - the name of the property
value - the value of the property

Note: btoolinfo is blocked from running on Splunk Cloud due to the app jail feature.


artifactinfo
==========
For support, please email sjohnson@splunk.com

| artifactinfo <sid, search, regex>=<option_value>

example:

| artifactinfo sid=1679956099.1578
| artifactinfo search="really bad error"
| artifactinfo regex="\w+Searches"

artifactinfo is a custom search command that will return the contents of an info.csv file from a search artifact on the search head where it is run
artifactinfo is a generating command and must be the first command in the pipeline
artifactinfo requires 1 of 3 arguments: sid, search, regex
sid = search id of the artifact
search = a search string (case sensitive) to find in the info.csv file of any artifact
regex = a regex expression to use to search the info.csv file of any search artifact

artifactinfo requires python3 to run
artifactinfo returns the contents of the search artifact info.csv file



pinginfo
==========
For support, please email sjohnson@splunk.com

| pinginfo address="ip address or name" (count=n)

example:

| pinginfo address="google.com" count=5

pinginfo is a custom search command that will run the OS ping command to the ip address or hostname specified
pinginfo is a generating command and must be the first command in the pipeline
ping info requires a host or ip address and optionally a count (max count is 10, default count is 3)
pinginfo requires python3 to run

pinginfo returns a field: pingdata that is the output of the OS ping command that was run

Note: Splunk Cloud now appears to block access to the OS ping command

sslinfo
==========
For support, please email sjohnson@splunk.com

| sslinfo hostport="host:port" (timeout=n)

example:

| sslinfo hostport=google.com:443" timeout=10

sslinfo is a custom search command that will run the openssl sclient command to return info about ssl certificate found at the address and port specified
sslinfo is a generating command and must be the first command in the pipeline
sslinfo requires a host or ip address and port be specified and optionally a timeout value in seconds for the command (default 5) maximum of 30
sslinfo requires python3 to run

sslinfo will return a field: data that is the output of the openssl s_client -connect command

varinfo
==========
For support, please email sjohnson@splunk.com


| varinfo (<subdir>=<subdirectory under $SPLUNK_HOME/var>)

example:

| varinfo subdir="run/splunk/csv"

varinfo is a custom search command that will generates a list of files under $SPLUNK_HOME/var
varinfo is a generating command and must be the first command in the pipeline
varinfo has an optional argument: subdir that can be any valid subdirectory under $SPLUNK_HOME/var - if not specified all files are listed (may be a lot of files)
varinfo will return the following fields: file (including full path), size (bytes), mtime (epoch format)

Note: upward recursion is not allowed

cliinfo
==========
For support, please email sjohnson@splunk.com

| cliinfo clicmd=<status, list, show, display, help command and options>

example:

| cliinfo clicmd="show kvstore-status"

cliinfo is a custom search command that will generate the output of certain display only splunk cli commands if you have the proper capability (list_settings) or role to run them (admin, sc_admin)
cliinfo is a generating command and must be the first command in the pipeline
cliinfo returns a field: cmdout that is the stdout from the command that was run

Note: if you try to run a command not listed you will get the message "not allowed" in the cmdout field

Note: the cliinfo command is blocked from running on Splunk Cloud by the app jail feature.

specinfo
==========
For support, please email sjohnson@splunk.com

| specinfo spec=<spec file name>

example:

| specinfo spec=server

specinfo is a custom search command that will display the contents of a spec file from $SPLUNK_HOME/etc/system/README
specinfo is a generating command and must be the first command in the pipeline
specinfo returns a field: contents that is a complete listing of the .spec file requested

Note:  a bad spec file name will return: .spec file not found
