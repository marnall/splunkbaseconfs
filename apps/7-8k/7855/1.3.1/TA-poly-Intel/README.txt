# PolySwarm Malware Threat Intelligence App for Splunk

## Overview
Leverage PolySwarm’s advanced malware intelligence marketplace to acquire superior, timely insights. Minimize extraneous data to efficiently identify, analyze, and mitigate critical threats.
The PolySwarm Malware Intelligence application automates the enrichment of Splunk events with crowdsourced malware threat intelligence data.
## Compatibility Matrix

* Unix OS
* Splunk version: 9.0.x  or higher
* Python version: Python3

## Installation

The PolySwarm Malware Intelligence app can be installed through the UI, as shown below:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-poly-Intel` installation file.
4. Click on `Upload`.
5. Restart Splunk.

## Configuration

Getting started - 

Step 1: Get your API Key 
	The Customer can get their API key from https://polyswarm.network  and then navigate to Settings/API Keys

Step 2: Setup Page 
	Set up your API Key using the App Setup page. This will securely store your API or the integration key in Splunk password storage. 

Step 3: Data input
	Use Malware Family and/or your Industry/Sector Tags to collect the Latest Malware Intelligence. You can schedule an auto update using ‘more settings’ in the data input
	
	How to Configure Data Input: 
	Setting -> Data Input -> Select Get PolySwarm Malware Intelligence->New Data Input
	
	Create  a New Input: 
	Name: <Select the data input name> 
	i.Enter the number of days for your query (default: 1 day / 24 hours): <Optional Field> 
	ii. List up to three Malware Families (e.g. redline,godfather,ryuk): <Optional Field>
	Iii. List up to three Malware Intelligence Tags (e.g.sector:healthcare,sector:government,ransomware):<Optional Field>
	iv. Enter the minimum PolyScore (malware score) [0 (benign) - 1 (malicious)] (default value 0.75):<Optional Field>
	v. Limit the number of hashes/results to download per execution/job (default value 100): <Optional Field>
	vi.  More Setting -> Interval -> Enter is Second  86400 for 1 day 
		This must be set to the same a number of days as set in your query to get data constantly.  E.g..  if the “Enter the number of days for your query” is set to 1 day, then the Interval must be set to 1 day also. 
	vii.  More Setting -> Source type ->  Set sourcetype - Automatic  (default) 
	viii More Setting -> Host - host -> $decideOnStartup (default)
	iX More Setting ->  Index -> Index -> default

Step 4: Dashboard
	PolySwarm Malware Intelligence - This dashboard contains the top 10 Malware families, Malware Type, Tags, and OS observed.  The data used is based on the data input defined.  

Step 5: Built-in Commands
	Below are the built-in commands for the PolySwarm Malware Intelligence App

	ptipolytest 
		Description:  Will test the API key storage/retrieval and connection to the PolySwarm Malware intelligence Platform.
		Usage: | ptiapitest
		Output: Display your api key, teamname, userid and accounttype. 

	ptiaccountdetails  
		Description: Provide the API key details and usage information for the stored API key
		Usage: | ptiaccountdetails
		Output - API key information and usage data

	ptilistmalwarefamily 
		Description: List all the available Malware families on the PolySwarm Malware Intelligence Platform.
		Usage: | ptilistmalwarefamily
		Output - List of Malware families.
	
	ptilisttags
		Description - List all the available Malware families on the PolySwarm Malware Intelligence Platform.
		Usage: | ptilisttags
		Output - List of all the tags.

	pti
		Usage: pti <command options>=<value> 
		Description: Get the latest malware Intelligence from PolySwarm Malware Threat Intelligence

		command options:
			get_hash_data
				syntax = get_hash_data=<string> 
				Description: Get malware intelligence for a specific hash or a list of hashes. Support MD5, SHA-1 and SHA-256.
				Example: 
				For hashes already in your events: 
				Search <your search> | rename sha256 as hashdata|table hashdata |pti get_hash_data=hashdata
				For hashes not in your events: 
				| makeresults | eval hashdata = "da163b60d27303d8bbf98348ef1dbfef9e33effcdb3af650e12324f0318fb2c0" | pti get_hash_data=hashdata

			get_iocs_by_hash
				syntax = get_iocs_by_hash=<string> 
				Description: Get the IOC intelligence (IP, Domain, ttp, url)  for a specific hash or a list of hashes. Support MD5, SHA-1 and SHA-256.
				Example: 
				For hashes already in your events: 
				Search <your search> | rename sha256 as hashdata|table hashdata |pti get_iocs_by_hash=hashdata
				For hashes not in your events: 
				| makeresults 
				| eval hashdata = "da163b60d27303d8bbf98348ef1dbfef9e33effcdb3af650e12324f0318fb2c0" 
				| pti get_iocs_by_hash=hashdata 

			get_hash_by_ip
				syntax = get_hash_by_ip=<string> 
				Description: Get Malware hashes that have the specific IPs observed or extracted during the Sandbox process.
				Example: 
				For ip address already in your events: 
				Search <your search> | rename dstip as checkip |table hashdata |pti get_hash_by_ip=hashdata
				For ip address not in your events: 
					| makeresults | eval hashdata = "96.16.241.23" | pti get_hash_by_ip=hashdata

			get_hash_by_domain
				syntax = get_hash_by_domain=<string> 
				Description: Get Malware hashes that have the specific domain observed or extracted during the Sandbox process.
				Example: 
				For a domain address already in your events: 
				Search <your search> | rename dsturl  as checkdomain |table hashdata 
				|pti get_hash_by_domain=checkdomain

				For domains not in your events: 
				| makeresults | eval hashdata = "pki" | pti get_hash_by_domain=hashdata

			get_hash_by_ttp
				syntax = get_hash_by_ttp=<string> 
				Description: Get Malware hashes that have the specific field ttp observed or extracted during the Sandbox process.
				Example: 
				For ttp’s already in your events: 
				Search <your search> | rename event.ttps  as ttps |table ttps |pti get_hash_by_ttp=ttps
				For ttp’s address not in your events: 
				| makeresults | eval ttps = "T1055" | pti get_hash_by_ttp=ttps

			get_hash_by_tags
				syntax = get_hash_by_tags=<string> 
				Description: Get malware intelligence and a list of hashes based on the tags.  Tags can be based on industry or malware family, or malware type. You can get all the supported tags using the command |ptilisttags
				Example: 
				| makeresults | eval tags="sector:healthcare,sector: financial" | pti get_hash_by_tags=tags

			get_hash_by_malware_family
				syntax = get_hash_by_malware_family=<string> 
				Description: Get malware intelligence and a list of hashes based on the specified Malware Families. You can get all the supported malware families using the command | ptilistmalwarefamily
				Example: 
				| makeresults | eval family="redline,godfather,ryuk" | pti get_hash_by_malware_family=family



