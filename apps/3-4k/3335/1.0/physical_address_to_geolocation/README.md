The Physical Address to Geolocation App obtains the geolocation for any number of given physical addresses.  Once you have this information, you will be able to perform a wide array of evaluations against your data.  For instance, you can calculate how close together two mailing addresses are.

To prove out that this can be done in Splunk, we are using a large data set of addresses from the National Center for Educational Statistics:

                http://nces.ed.gov/ccd/pubschuniv.asp

This is a complete listing of all public elementary and secondary schools in the country from 2014 - 2015.


Changes to Splunk:
This App will install a two indexes:

	addresses
	Will be loaded with a base of address information.  You can put your data here.

	geolocation
	Stores the output from the scripted API query, including status.


Getting started:

Create the geolocation_lookup KV store with this search against your address data, *** OVER ALL TIME ***:

	index="addresses" | eval cust_lat="DNE" | eval cust_lon="DNE" | eval location_type="DNE" | eval in_reconciliation="no" | rename NCESSCH AS cust_id, SCHNAM AS cust_name, LSTREE AS cust_street, LCITY AS cust_city, LSTATE AS cust_state, LZIP AS cust_zip | table cust_id cust_name cust_street cust_city cust_state cust_zip cust_lat cust_lon location_type in_reconciliation | outputlookup geolocation_lookup


You can validate your KV Store with this search:

	| inputlookup geolocation_lookup


If you needs to delete a KV Store and start over, run this command from the CLI:

	curl -k -u admin:changeme -X DELETE https://localhost:8089/servicesNS/nobody/physical_address_to_geolocation/storage/collections/data/reconcile


Configuration:
You will need to update the address_to_lat_lon.pl script located in the bin directory.  Read through the script to understand what it is doing and how to obtain a Google API key.

After that, you will need to copy the script to $SPLUNK_HOME/bin/scripts/ dir.  


How it works:

There are two KV stores:

	geolocation_lookup - stores all address information.  Unknown values are populated with DNE (does not exist).

	reconcile_lookup - stores information for all addresses that are returned by the API, when the number of results is greater than one.

A search is scheduled every 15 minutes to check the geolocation_lookup for missing information (DNE).  When that condition is met, it triggers the script that runs an API query to obtain the geolocation information.  The results of the API query determine what happens to that data.  


Known Issues:
I am still working out the best way to delete items from the reconcile_lookup after reconciliation.  The only way to delete a KV store record is to use the API.  This means that I will most likely have to write a custom command that calls the API to achieve this properly.  


Installation:
First install this App on your Search Head(s).  Next, migrate the index configuration to the indexing tier and restart Splunk.


Dashboards:
Physical Address to Geolocation - Displays all of the addresses that have Lat/Lon set in the Geolocation KV Store.
Geolocation KV Status - Shows the progress and status of the Geolocation KV Store.
Reconcile KV Status - Shows the progress and status of the Reconcile KV Store.
Reconcile Records - Used to reconcile records that have more than one address returned from the API.
Script Status - Analysis of the script output.


Contributing Authors:
James Donn

