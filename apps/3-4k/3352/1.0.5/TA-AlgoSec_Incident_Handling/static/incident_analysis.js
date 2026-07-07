require([
    "splunkjs/mvc/searchmanager/ready!",
    "splunkjs/ready!",
    "splunkjs/mvc/simplexml/ready!"
], function(mvc, SearchManager) {



	var mysearch = splunkjs.mvc.Components.get("AffectedApplications");
    // Access the "default" token model
	var tokens = splunkjs.mvc.Components.get("default");

	tokens.set("Impacted Business Applications", "Waiting For Search To Be Run");
	tokens.set("Criticality", "");
	tokens.set("ABFDetails", "");

    // Change the value of a token $mytoken$


	mysearch.on('search:start', function(properties) {
        // Print just the event count from the search job
        tokens.set("Impacted Business Applications", "Search Started");
        tokens.set("Criticality", "");
        tokens.set("ABFDetails", "");

    });

    mysearch.on('search:progress', function(properties) {
        // Print just the event count from the search job
        tokens.set("Impacted Business Applications", "Search is Running...");
        tokens.set("Criticality", "");
        tokens.set("ABFDetails", "");

    });





});
