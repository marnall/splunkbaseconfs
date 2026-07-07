 require([
    "splunkjs/mvc",
    "splunkjs/mvc/simplexml/ready!"
 ], function(mvc) {
     var tokens = mvc.Components.get("default");
     tokens.set("Location", "*");
     tokens.set("User", "*");
     tokens.set("Application", "*");
     tokens.set("Device", "*");
     tokens.set("Drilldown_source", "*");
 });
