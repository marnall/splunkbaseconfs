FileServ

The FileServ app provides a way to make some files on a Splunk server accessible to a
group of users. This may be more convenient than sharing out part of the file system or
exporting the files by some other means. The app lets users see a filtered list of files from
each of the specified directories and download whichever files they want.

The original reason for creating this app was to gain convenient access to the directory
where outputcsv files are stored. The outputcsv command allows files with more that
10000 rows to be created, but the files are placed directly on the server in
$SPLUNK_HOME/var/run/splunk. By adding this directory to the config file, such files
are easily accessed.

The config file fileserv.conf is used to specify which directories can be accessed. For
each directory that is specified, a description and a file mask can be entered. The
description is what is displayed rather than the actual path, and the file mask is a regular
expression used to limit the accessible files.

Installation
--------------
	1. Install the app in the usual way. Either unpack the tar ball into the
	$SPLUNK_HOME/etc/apps subdirectory, or install it from the Manage Apps
	screen.

	2. Create the $SPLUNK_HOME/etc/apps/FileServ/local folder.

	3. Create a file in that folder called fileserv.conf, or copy the sample from the default
	folder.

	4. Edit the fileserv.conf file in the local folder and create a new stanza similar to the
	following:
	[dir:mycsv]
	path = /opt/splunk/var/run/splunk
	description = Folder that all the outputcsv files go
	matchstr = .*\.csv$
	The stanza name must begin with “dir:”. Path and description are required, but
	matchstr is optional. Make absolutely sure that the path exists and is not
	accessible by any unauthorized individuals.

	5. Add additional stanzas similar to the one above for any directories that you want
	to make available.

	6. Restart Splunk to read in the new config file.

	7. In the Apps section of the Manager, grant Read access to the FileServ app to roles
	requiring access to the app. Those granted access to the app will have access to all
	available files whether they created them or not, so this access should only be
	granted to trusted individuals.