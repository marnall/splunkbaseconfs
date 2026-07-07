Installation:
* NOTE: This will NOT function on a Universal Forwarder

1. Copy the TA-Memreader folder to $[SPLUNK_HOME]/etc/apps
2. Add a stanza in $[SPLUNK_HOME]/etc/apps/TA-MemReader/local/memreader.conf for each memory address you'd like to read.
	* there is a [targetmem] stanza that you are free to use in /local/memreader.conf
3. Either run the script by hand using splunk's python or by setting up a scripted input / modular input.
	* if you use the targetmem stanza, you can add a /local/inputs.conf that enables [script://.\bin\MemLogReader.py memreader.conf targetmem] stanza
	
Script Usage:
	MemLogReader.py <name of .conf> <name of stanza>
	
if you want to test out by hand, before enabling a scripted input, you can test by doing the following:
	$[SPLUNK_HOME]/bin/splunk cmd python $[SPLUNK_HOME]/etc/apps/TA-Memreader/bin/MemLogReader.py memreader.conf targetmem
