// Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
/* global Splunk */
let APP = "cisco_cdr";
require(["jquery"], function($) {
    let uri = document.location.toString();

    // make sure we don't run the rest of this code on normal simpleXML dashboards.
    // this has to ONLY run on the weird "fake" homepage.
    if (uri.indexOf(APP + "/home_redirect") != -1) {

        // take away the "home" title and everything asap. If we're lucky the user won't even see it.
        $(".dashboard").hide();

        let splunkMajorVersion = parseInt(Splunk.util.getConfigValue("VERSION_LABEL").split(".")[0], 10);

        if (splunkMajorVersion < 8) {
            $(".dashboard").show();
            $("#splunkTooOld").show();
            return;
        }
        $.ajax({
            type: "GET",
            dataType: "json",
            url: Splunk.util.make_url("/splunkd/__raw/services/apps/local/canary"),
            data: {"output_mode": "json"},
            async: true,
            success: function() {
                // go to the "real" homepage
                document.location = Splunk.util.make_url("/splunkd/__raw/sv_view", APP, "home");
            },
            error: function() {
                // there aint no canary on this system. Display the hidden content.
                $(".dashboard").show();
                $("#canaryNotInstalled").show();
            }
        });
    }
    // special cased logic just for the "edit" mode in the Simple XML.
    else if (uri.endsWith("/edit")) {

        // just a little bit of evil.
        // Because Splunk didn't actually remove the Advanced XML framework but just crippled it,
        // we can't let Splunk think we have advanced XML pages, cause it'll try to load them.
        // specifically we can't use <view> tags in default.xml
        // this means we have to use <a> tags with explicit URIs.
        // because of ROOT_ENDPOINT we can't use absolute URIs, so we have to ../../ to the right place
        // which is fine because splunk's paths are always /<root_endpoint>/<locale>/app/<app>/<view>
        // except.... this isn't always true - the counterexample is simpleXML Edit mode.
        // so just in SimpleXML Edit mode, we sneak in and... ahem... modify the href's.
        $(document).click(function(evt) {
            let t = $(evt.target);

            //console.error("we are on  a simple xml view and it is in edit mode.")
            if (t.prop("tagName").toLowerCase() == "a") {

                let href = t.attr("href");

                if (href.indexOf("../../splunkd/__raw/" + APP + "_shunt") == 0) {
                    href = "../" + href;
                    t.attr("href", href);
                    evt.preventDefault();
                    document.location = href;
                    return false;
                }
                // turn off all clicks for easier testing.
                //console.error(href);
                //evt.preventDefault();
                //return false;
            }
        });
    }
});


