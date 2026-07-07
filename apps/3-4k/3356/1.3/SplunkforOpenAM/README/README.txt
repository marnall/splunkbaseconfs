####################################################################
############### Welcome to the Splunk for OpenAM App ###############
####################################################################

Please follow these steps to install and configure Splunk for OpenAM.

############### Before we begin ###############

- This App has been developped on Splunk 6.4.3 with OpenAM v12 installed on 2.6+ kernel Linux 64-bit servers.

- To delete this page from Splunk for OpenAM App :
	- Edit $_SPLUNK_HOME/etc/apps/SplunkforOpenAM/default/data/ui/nav/default.xml file
	- Delete the line "<view name="Readme"/>"
	- Restart Splunkweb
	
- IMPORTANT : This App expects OpenAM logs to be sent from a directory ending with "/openam/log" (ex : "/home/user/openam/openam/log").
  Otherwise configuration should be adapted in :
	- inputs.conf file on Splunk Universal Forwarders
	- props.conf file of SplunkforOpenAM App on Search Heads
	- props.conf and transforms.conf files on indexers

	
	
############### Splunk Configuration ############### 

############# Prerequisites ############# 

- Splunk is fully installed on a standalone or distributed environment
- TCP input has been configured on indexer(s) to receive data on a specific port (ex : TCP port 9997)
- Search Head(s) has been configured to search on indexer(s)

############# Index and sourcetypes configuration #############

1. Create an index to receive OpenAM logs on Splunk indexers, as described in Splunk Documentation (http://docs.splunk.com/Documentation/Splunk/6.4.3/Indexer/Configureindexstorage), or use default main index.

IMPORTANT : if a specific index is used, please add this index to be searched by default (as described in Splunk Documentation (http://docs.splunk.com/Documentation/Splunk/6.4.3/Security/Addandeditroles)) or modify search requests on dashboards to use this index.

2. Create or modify props.conf and transforms.conf files on indexers with the following configuration :

	props.conf :

		[source::.../openam/log/*]
		SHOULD_LINEMERGE = false
		TRUNCATE = 100000
		TRANSFORMS-nullq = null-leadingHash
		TRANSFORMS-sourcetype = override-sourcetype

	transforms.conf :

		[null-leadingHash]
		REGEX = ^\#.*
		DEST_KEY = queue
		FORMAT = nullQueue

		[override-sourcetype]
		DEST_KEY = MetaData:Sourcetype
		SOURCE_KEY = MetaData:Source
		REGEX = .*/openam/log/(\w+)(\.\w+)?
		FORMAT = sourcetype::$1
		WRITE_META = true

3. Restart Splunk service

############### OpenAM Configuration ###############

############# Prerequisites #############

- OpenAM servers must be able to communicate with Splunk indexer(s) on the TCP port configured to receive logs
- OpenAM servers should be configured to save logs in a directory ending with "/openam/log" (otherwise, configuration should be adapted on indexers , search heads and universal forwarders)
- Splunk Universal Forwarder adapted to OpenAM servers' Operating System has been downloaded from Splunk Website (https://www.splunk.com/en_us/download/universal-forwarder.html)


############# Splunk Universal Forwarder installation #############

Install Splunk Universal Forwarder on OpenAM servers as described in Splunk Documentation : https://docs.splunk.com/Documentation/Forwarder/6.4.3/Forwarder/Installtheuniversalforwardersoftware


############# Splunk Universal Forwarder configuration #############

1. Configure data inputs and outputs on Splunk Universal Forwarder to forward OpenAM logs to Splunk indexers.

	For example, the following files allow Splunk Universal Forwarder to monitor /home/user/openam/openam/log directory and send files to indexer1.example.com and indexer2.example.com on TCP port 9997 to an index named "openam" :

	$SPLUNK_HOME/etc/system/local/inputs.conf :

		[monitor:///home/user/openam/openam/log]
		crcSalt = <SOURCE>
		index = openam

		
	$SPLUNK_HOME/etc/system/local/outputs.conf :

		[tcpout]
		defaultGroup = default-autolb-group

		[tcpout:default-autolb-group]
		disabled = false
		server = indexer1.example.com:9997,indexer2.example.com:9997
		compressed = true
		useACK = true

		[tcpout-server://indexer1.example.com:9997]
		[tcpout-server://indexer2.example.com:9997]

	For more details about configuring Splunk Universal Forwarder, see Splunk Documentation (http://docs.splunk.com/Documentation/Forwarder/6.4.3/Forwarder/Configuretheuniversalforwarder)

2. Start Splunk Universal Forwarder as described in Splunk Documentation (http://docs.splunk.com/Documentation/Forwarder/6.4.3/Forwarder/Configuretheuniversalforwarder#Restart_the_universal_forwarder) 

3. Check logs on Search Head(s) by searching in the index configured to receive openam logs.
