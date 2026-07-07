ITMIP Neo4j Commands for Splunk version 2.2.2
This "Neo4j Commands" app is meant as a front end to:
- a Neo4j graph database

It offers the following the following functionality:
- The app is visible as "Neo4j Commands"
- within that app you can configure accounts. You should ALWAYS define an entry called "neo4j" that acts as a default. And of course specify the details for the Neo4j connection.
  For the protocol select bolt as the https is for the current version not working.
  The name of the account can be used with the search commands part of this app. But always specify a default called "neo4j".
- Three new search commands:
        gsearch: used to search the graph database as a reporting command which can take splunk search results as input. E.g.: "|gsearch query="MATCH (a) RETURN DISTINCT labels(a)" account='neo4j'". When account is not specified it fallsback to the default "neo4j".
        gsearchgen: used to search the graph database as a generating command. E.g.: "|gsearch query="MATCH (a) RETURN DISTINCT labels(a)" account='neo4j'". When account is not specified it fallsback to the default "neo4j".

Installation:
Install app on individual Search Head or Search Head cluster through Search Head deployer.

Python version
This release is only compatible with Python 3.

That Neo4j graph database should be filled with items that can be used within Splunk.
One of the products/services that can be bought as well is a complete Neo4j graph database that is connected to your ServiceNow Instance
in order to have an accurate:
- CMDB data into the graphdb
- CMDB relations into the graphdb
- Incidents
- Problems
- Changes
- ServiceNow Users and their (ITIL, config) groups.
- everthing is updated in real-time.

Without Neo4j graph database backend this app is not useful.

Release history:
2.2.2 Build in a check for Services not having a "services_depends_on"  field (Some services found in SAP Content Pack)
      When selecting ouput=itsi it no longers query the ITSI Services and Entities anymore.
2.2.0 gpath command working with the Neo4j HTTP API
2.1.1 Small defect on the https side resolved
      Working on getting the gpath command based on ITSI API calls.
2.0.1 Removed Neo4j bolt python drivers
      Communication is now based on the Neo4j HTTP(s) API
      Version is build with the latest Splunk Add-on Builder version 4.0.0
      Splunk Cloud ready.
      gpath command is not yet available in this release.
1.0.2 gsearch is now a real reporting command and takes input from Splunk to search for in Neo4j
      Cleaned up the searchbnf
      gpath command has now selectable label field parameter.
1.0.1 Modified the app.conf file and added app.manifest.
      Updated spluklib from 1.6.11 to 1.6.15
      Made it working for both python 2 as 3
1.0.0 Initial Splunkbase releaseDate
