# tado Heating App for Splunk
Splunk App to collect and report on data from the tado Heating System - see http://www.tado.com for more information.

The author of this Splunk App has no affiliation with tado, other than as a user of the product.

##Installation
Install the package from either: 

	* git https://github.com/nickhills81/tado_heating_for_splunk
	* Splunkbase https://splunkbase.splunk.com/app/3479

###Credentials
When the application is run for the first time you will be prompted to enter your credentials for tado.
These credentials are used to query the tado API in order to fetch the status of your installation and local weather.


##Known Issues
* Not all weather types may be handled correctly - If you spot a weather type which does not render with the correct (or sensible) icon, please let the author know. You can obtain a list of all the weather types you have experience using the query: `'tadoIndex' weather=*|dedup weather|table weather`


### Updates in this release
	* Removed custom index, and updated to utilise main. tadIndex macro is backwards compatible
	* Optimisations for python execution.
	* Setup Screen now allows for selective enabling of inputs 
