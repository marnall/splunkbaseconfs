// Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
/* global $, sprintf, _, localAppStaticUrlPrefix */
/**
 * If your use of this app is through the Sideview Trial Internal Use License
 * Agreement, or through the Sideview Term Internal Use License Agreement or
 * through the Sideview Perpetual Internal Use License Agreement, then as per
 * the relevant agreement any modification of this file or modified copies
 * made of this file constitutes a violation of that agreement.
 */

let AUTOPAUSE_AT_N_SECONDS = 10;



// legacy handling for 7.3, and in case folks somehow accidentally stray into a legacy Advanced XML URL.
if (!window.isCanary) {
    let currentView;
    try {
        currentView = Splunk.util.getCurrentView();
        //console.error("behold the undead horror that is the advanced XML!")
        // the advanced XML wasn't killed.  It was instead buried alive. Entombed, immured within
        // the forgotten "_admin" view, in most manager pages.
        // On moonless nights you can hear its silent screams. oh wait no that's just my mouse.
    }
    catch(e) {
        try {
            currentView = $("body").attr("s:view");
        }
        catch(e) {}
    }


    if (currentView=="_admin") {
        if ($("#Message_0_0_0").length>0) {
            /** a weird hack.  Advanced XML is still used to load some manager pages. Even in 8.X and 9.X
             * and the advanced XML has incorrect ideas about what is legal/illegal in canary view config.
             * so if we let it, it would spit out a bunch of confusing errors in manager.
             * Since nothing the advanced XML error messaging system has to say about the world is worth
             * reading, we just kill the, er, messenger.
             */
            $("#Message_0_0_0").hide();
        }
    }
    // some other random advanced XML URL.  Get. Out.
    else {
        let APP = "cisco_cdr";
        // lets try and go to app/cisco_cdr,  let the home_redirect.xml view take things from there.
        let url_segments = document.location.pathname.split("/");
        for (let i=url_segments.length-1; i>url_segments.length-3; i--) {
            let segment = url_segments[i];
            if (segment==APP) {
                url_segments.splice(i+1, url_segments.length-1);
                document.location = url_segments.join("/");
            }
        }
    }
}
// Otherwise we are running in Canary UI.
else {
    define(
        [
            "jquery",
            "sideview",
            "context",
            "api/splunk/SplunkSearch",
            localAppStaticUrlPrefix + "lib/check_status.js",
            localAppStaticUrlPrefix + "lib/extractor.js",
            localAppStaticUrlPrefix + "lib/custom_behaviors/set_custom_tokens.js",
            "time_range",
            "modules/Button/Button",
            "modules/Link/Link",
            "modules/Redirector/Redirector",

        ],
        defineCustomBehaviors
    );
}

/**
 * It is goofy to put at the top but hey now the indentation isn't awful.
 */
function defineCustomBehaviors($, Sideview, Context, SplunkSearch, appChecker, extractor, customTokens, TimeRange, Button, Link, Redirector) {

    // TODO - if we make the CheckboxPulldown module return an extra key that is "all possible values"
    // then this and the usage of it, can be eliminated.
    let CALL_TYPE_VALUES = ["incoming","outgoing","internal","tandem"];



    appChecker.check();

    function currentlyWithin(viewArray) {
        if (typeof(Sideview.currentlyWithin) != "undefined") {
            return Sideview.currentlyWithin(viewArray);
        } else {
            if (viewArray.indexOf("home") != -1) {
                viewArray.push("home_alternate");
                viewArray.push("home_old");
            }
            let currentView = Sideview.getCurrentView();
            return (viewArray.indexOf(currentView) != -1);
        }
    }

    /**
     * Modifying this module to respond directly to hashChange events,
     * and to ignore context changes (which would trigger normal html re-render from context.)
     */
    Sideview.declareCustomBehavior("displaySavedReportName", function(html) {
        let updateHeader = function() {
            let urlDict = Sideview.getURLDict();
            let savedSearchName = urlDict["search.name"];
            let c = html.getContext();
            // URLLoader passes this down in the context.
            let sharing = (c.get("search.sharing") == "app") ? "shared": false;
            let headerText = savedSearchName;
            if (headerText) {
                headerText = "Saved report - " + headerText;
            }
            if (sharing) {
                headerText = headerText + " (" + sharing + ")";
            }
            $("h2", this.container).text(headerText);
        }.bind(this);

        // onHashChange gets it there much quicker.  BUT the sharing info is only there after
        // URLLoader gets its async data and actually pushes. So we bind to both.;
        html.onContextChange = updateHeader;
        html.onHashChange = updateHeader;
        // called just after onHierarchyLoaded, so run it the first time:
        html.onHashChange();

        // listen directly to all hashchange events.
        // note - only pages with URLLoader can even *load* saved searches so we can actually
        // assume that URLLoader is on this page.
        $(window).bind("hashchange", html.onHashChange.bind(this));
    });

    Sideview.declareCustomBehavior("yourSavedDashboardsTable", function(table) {

        table.displayNoResultsMessage = function(_ignored) {
            let messageText = "You haven't created any dashboards yet, nor have your colleagues shared any.";
            this.resultsContainer.html("");
            let message = $("<p>")
                .addClass("status")
                .addClass("emptyResults")
                .append(messageText);
            this.resultsContainer.append(message);
        };

    });

    Sideview.declareCustomBehavior("yourSavedReportsTable", function(table) {

        table.displayNoResultsMessage = function(_ignored) {
            let messageText = "You haven't saved any reports yet, nor have your colleagues shared any.";
            this.resultsContainer.html("");
            let message = $("<p>")
                .addClass("status")
                .addClass("emptyResults")
                .append(messageText);
            this.resultsContainer.append(message);
        };

    });

    /**************************************
     * Action menu things
     **************************************/



    Sideview.declareCustomBehavior("callsTable", function(table) {

        let methodReference = table.onContextChange.bind(table);
        table.onContextChange = function(context) {

            let modifiers = context.get("modifiers.rawValue") || "";

            if (modifiers.indexOf("highlightEverywhere") != -1) {
                this.setParam("highlightEverywhere", "True");
            }
            else {
                this.setParam("highlightEverywhere", "False");
            }
            return methodReference(context);
        };
        /**
         * Once Canary 1.5.13 has been out for a long time, this can be
         * removed.
         */
        if (typeof(table.getCellFromMouseEvent)!="function") {
            table.getCellFromMouseEvent = function(target) {
                if (target.is("div") && target.hasClass("mv")) {
                    return target;
                }
                else {
                    let cell = (target.is("td")) ? target : $(target.parents().filter("td")[0]);
                    // The modified behavior, that also shipped in Canary 1.5.13, is just
                    // to not check whether the cell has a value in it.
                    if (!cell.hasClass("mvCell")) {
                        return cell;
                    }
                }
                return false;
            }.bind(table);
        }

    });

    Sideview.declareCustomBehavior("actionMenusForDetailViews", function(mod) {
        /* rendering a new set of links */
        mod.onContextChange = function(context) {
            // remove the previous menu items.

            // DONT call this from here!   or it removes the menu items just added by the other
            // customBehavior module(s)
            //$(".conjuredModule",this.container.parent()).remove();

            let fieldPrefix = context.get("click.selectedTableName") + ".fields";
            let dataTypesInRow = context.get(fieldPrefix + ".data_type").split(",");
            let dataTypeDict = context.get("data_type_dict");

            // in rare rare cases the inputlookup data_types search can fail
            // (for example if the user hits a quota limit and then a few minutes later clicks the submit button)
            if (!dataTypeDict) {
                Sideview.broadcastMessage("error", "An unexpected failure has occurred retrieving data types. Some elements may not function correctly. Please try reloading the page.");
            }

            let alreadyRendered = [];
            // it seems like... this is a frankenstein.
            for (let i=0; i<dataTypesInRow.length; i++) {
                let dataType = dataTypesInRow[i];

                if (!dataType) {
                    Sideview.broadcastMessage("error", "row returned has no data_type");
                    return false;
                }
                if (Object.hasOwn(dataTypeDict[dataType], "detail_view")) {

                    let detailView = dataTypeDict[dataType]["detail_view"];

                    // if this call has both CUBE and CUCM,  the cube call_detail_cube view wont work anyway
                    // because the SPL logic will have rewritten call_id to be the CUCM call_id everywhere.
                    // the "dataTypesInRow" stuff is vestigial but it works to look for the CUCM hiddenfields...
                    if (dataType == "cube" && context.get("row.fields.globalCallID_callId")) {
                        dataType = "cucm";
                        detailView = "call_detail";
                    }


                    if (alreadyRendered.indexOf(detailView)!=-1) {
                        continue;
                    }


                    let label = "view call details";
                    if (dataType != "cucm") {
                        label += " (" + dataType + ")";
                    }
                    let container = $("<div>").addClass("Module").addClass("Link").addClass("menuItem").addClass("conjuredModule").insertAfter(this.container);
                    let link = new Link(container, {"label":label,"cssClass":"menuItem"});
                    link.baseContext = this.getContext();
                    link.markPageLoadComplete();

                    let container2 = $("<div>").addClass("Module").addClass("Redirector").addClass("conjuredModule").insertAfter(this.container);

                    let params = {};

                    params["url"] = dataTypeDict[dataType]["detail_view"];

                    let objectIds = dataTypeDict[dataType]["object_ids"].split(" ");
                    for (let j=0; j<objectIds.length; j++) {
                        params["arg." + objectIds[j]] = sprintf("$%s.%s$", fieldPrefix, objectIds[j]);
                    }

                    // it's a little weird to use the $foo$ token system at all.
                    // since these modules are created to serve unique user clicks and therefore
                    // we could just do  context.get("row.fields.detailEarliest") here.
                    // however the $foo$ convention mirrors what hardcoded Redirector modules look
                    // like in the view XML so we're doing it this way.
                    params["arg.earliest"] = "$row.fields.detailEarliest$";
                    params["arg.latest"] = "$row.fields.detailLatest$";

                    params["arg.bc_earliest"] = "$cachedEarliest$";
                    params["arg.bc_latest"] = "$cachedLatest$";
                    params["arg.bc_type"] = "$type.rawValue$";
                    params["arg.bc_number"] = "$number.rawValue$";
                    params["arg.bc_numberType"] = "$numberType.rawValue$";
                    params["arg.bc_searchterms"] = "$searchterms.rawValue$";


                    let redirector = new Redirector(container2, params);
                    link.addChild(redirector);
                    this.addChild(link);

                    alreadyRendered.push(detailView);
                }
            }

            if (alreadyRendered.length > 0) {
                // this is to trigger a re-alignment on the Layer module.
                // it will have positioned itself according to whatever contents it had moments ago
                // this will cause it and its menu items within, to reflow around the selected element correctly.
                this.parent.onContextChange(this.parent.getContext());
            }
        };
    });


    let addNewLink = function(module, label) {
        let container = $("<div>").addClass("Module").addClass("Link").addClass("menuItem").addClass("conjuredModule").insertAfter(module.container);
        let link = new Link(container, {"label":label, "cssClass":"menuItem"});
        link.baseContext = module.getContext();
        link.markPageLoadComplete();
        module.addChild(link);
        return link;
    };

    Sideview.declareCustomBehavior("actionMenusForAlteringFormSelectionsFromChart", function(mod) {
        mod.addNewLink = function(label) {
            return addNewLink(this, label);
        }.bind(mod);

        mod.onContextChange = function(context) {
            // remove the previous menu items.
            $(".conjuredModule",this.container.parent()).remove();
            //undetermined yet which menu item this will get sent up with, if any.
            // however all this code re-runs every time a new menu is rendered.
            let upstreamContext = new Context();
            let searchTerms = [];
            if (context.get("searchterms")) {
                searchTerms = Sideview.getTopLevelSearchTokens(context.get("searchterms"));
            }
            // Canary already handles crazy corner cases like the "OTHER" click and the "NULL" click correctly.
            searchTerms = searchTerms.concat(context.get("chart.searchTerms"));
            // no matter which option is clicked, the searchterms will be the same.
            upstreamContext.set("searchterms", searchTerms.join(" "));

            if (context.get("chart.xField") == "_time") {
                // chart code gives you a range object for the drilldown but you have to plug it in yourself.
                let range = context.get("chart.timeRange");
                upstreamContext.set("shared.timeRange", range);
            }

            let investigateLink = addNewLink(this, "investigate these calls");
            $("a", investigateLink.container).click(function() {
                upstreamContext.set("mode", "calls");
                investigateLink.passContextToParent(upstreamContext);
            });

            let chartLink = addNewLink(this, "chart these calls");
            $("a", chartLink.container).click(function() {
                upstreamContext.set("mode", "chart");
                upstreamContext.set("zField", "");
                investigateLink.passContextToParent(upstreamContext);
            });

        };
    });

    Sideview.declareCustomBehavior("actionMenusForAlteringFormSelections", function(mod) {

        let getCheckboxPulldownSelectedValues = function(select) {
            let opts = [];
            $("option:selected",select).each(function() {
                opts.push($(this).attr("value"));
            });
            return opts;
        };

        mod.addNewLink = function(label) {
            return addNewLink(this,label);
        }.bind(mod);

        mod.buildTimeOptions = function(context, _field, _value) {

            let getCurrentThing = function(d, thing) {
                let start = new Date(d.valueOf());

                switch (thing) {
                    case "day":
                        start.setHours(0);
                        // falls through
                    case "hour":
                        start.setMinutes(0);
                        // falls through
                    case "minute":
                        start.setSeconds(0);
                        break;
                    default:
                        console.error("bad args provided to getCurrentThing");
                }
                let end = new Date(start.valueOf());

                switch (thing) {
                    case "day":
                        end.setDate(end.getDate()+1);
                        break;
                    case "hour":
                        end.setHours(end.getHours()+1);
                        break;
                    case "minute":
                        end.setMinutes(end.getMinutes()+1);
                        break;
                    default:
                        console.error("bad args provided to getCurrentThing");


                }
                // prior to 1.5.13, TimeRange didn't work right with raw Date args.
                let range = new TimeRange(start.valueOf()/1000, end.valueOf()/1000);
                return range;
            };

            // note this key will only exist in Canary 1.5.13 and up.
            let rowTime = context.get("row.fields._time");
            if (rowTime) {
                let rowDate = new Date();
                rowDate.setTime(rowTime*1000);

                // TODO - dont give the option, if you've ALREADY snapped to this day
                //let jobTimeRange = context.getSplunkSearch().job.getTimeRange();

                let thisMinuteRange = getCurrentThing(rowDate, "minute");
                //console.error("minute says " + thisMinuteRange.toConciseString())
                let minuteLink = this.addNewLink("snap time range to this minute");
                $("a", minuteLink.container).click(function() {
                    let upstreamContext = new Context();
                    upstreamContext.set("shared.timeRange.earliest", thisMinuteRange.getEarliestTimeTerms());
                    upstreamContext.set("shared.timeRange.latest", thisMinuteRange.getLatestTimeTerms());
                    minuteLink.passContextToParent(upstreamContext);
                });

                let thisHourRange = getCurrentThing(rowDate, "hour");
                //console.error("hour says " + thisHourRange.toConciseString())
                let hourLink = this.addNewLink("snap time range to this hour");
                $("a", hourLink.container).click(function() {
                    let upstreamContext = new Context();
                    upstreamContext.set("shared.timeRange.earliest", thisHourRange.getEarliestTimeTerms());
                    upstreamContext.set("shared.timeRange.latest", thisHourRange.getLatestTimeTerms());
                    hourLink.passContextToParent(upstreamContext);
                });

                let thisDayRange = getCurrentThing(rowDate, "day");
                //console.error("day says " + thisDayRange.toConciseString());
                let dayLink = this.addNewLink("snap time range to this day");
                $("a", dayLink.container).click(function() {
                    let upstreamContext = new Context();
                    upstreamContext.set("shared.timeRange.earliest", thisDayRange.getEarliestTimeTerms());
                    upstreamContext.set("shared.timeRange.latest", thisDayRange.getLatestTimeTerms());
                    dayLink.passContextToParent(upstreamContext);
                });

            }
        };

        mod.buildDurationOptions = function(context, field, value) {
            let searchterms = context.get("searchterms") || "";
            let durationClickHandler = function(zeroDurationLink, newTerm) {
                let upstreamContext = new Context();
                let searchterms = context.get("searchterms") || "";
                upstreamContext.set("searchterms", [searchterms.trim(), newTerm].join(" "));
                zeroDurationLink.passContextToParent(upstreamContext);
            };
            // if the call duration is somehow more than a day...
            // call: "i'm getting too old for this ...."
            if (value.indexOf("+") != -1) {
                return;
            }

            if (value=="00:00:00") {
                let newTerm = "duration=0";
                let existingTerms = Sideview.getTopLevelSearchTokens(searchterms);

                if (existingTerms.indexOf(newTerm)!=-1) {
                    let removeLink = this.addNewLink("stop searching for zero duration");
                    let newTerms = existingTerms.concat();
                    newTerms.splice(newTerms.indexOf(newTerm), 1);
                    $("a", removeLink.container).click(function() {
                        let upstreamContext = new Context();
                        upstreamContext.set("searchterms", newTerms.join(" "));
                        removeLink.passContextToParent(upstreamContext);
                    });
                }
                else {
                    let excludeZeroDurationLink = this.addNewLink("exclude calls with zero duration");
                    $("a", excludeZeroDurationLink.container).click(function() {
                        durationClickHandler(excludeZeroDurationLink, "NOT duration=0");
                    });

                    let zeroDurationLink = this.addNewLink("search for calls with zero duration");
                    $("a", zeroDurationLink.container).click(function() {
                        durationClickHandler(zeroDurationLink, "duration=0");
                    });
                }
            }
            else {
                // we already made sure this is less than a day so we just split it and do the math.
                let tuple = value.split(":");
                let durationValue = 3600 * parseInt(tuple[0],10) + 60 * parseInt(tuple[1],10) + parseInt(tuple[2],10);
                let pluralized = (durationValue==1) ? "second" : "seconds";
                let link = this.addNewLink(sprintf("search for calls where any call leg lasted %s %s or less", durationValue, pluralized));
                $("a", link.container).click(function(_evt) {
                    durationClickHandler(link, "duration<" + (parseInt(durationValue,10)+1));
                });
            }
        };

        mod.buildClusterAndTypeOptions = function(context, field, value, newTerm) {
            // investigate calls breaks convention for clusterId and doesn't use the field name
            // as the $foo$ token name.
            if (field=="globalCallId_ClusterID") field="clusterId";

            let selectElement = context.get(field + ".element");
            if (field=="clusterId" && $("option",selectElement).length==1) {
                return false;
            }

            let currentSelectedValues = getCheckboxPulldownSelectedValues(selectElement);

            // exclude a CheckboxPulldown value
            if (currentSelectedValues.length > 1) {
                let excludeLink = this.addNewLink("exclude " + newTerm);
                let newSelectedValues = currentSelectedValues.concat();
                newSelectedValues.splice(newSelectedValues.indexOf(value), 1);

                $("a", excludeLink.container).click(function() {
                    let upstreamContext = new Context();
                    upstreamContext.set(field, newSelectedValues);
                    excludeLink.passContextToParent(upstreamContext);
                });
            }

            // add/toggle a CheckboxPulldown value
            let togglingLabel = "search for ";
            // if this is currently the only selected value
            if ((currentSelectedValues.length==1 && currentSelectedValues[0] == value)) {
                togglingLabel = "stop searching for ";
                value = [];
            } else if (currentSelectedValues == "") {
                value = [value];
            }
            let link = this.addNewLink(togglingLabel + " " + newTerm);
            $("a", link.container).click(function() {
                let upstreamContext = new Context();
                upstreamContext.set(field, value);
                link.passContextToParent(upstreamContext);
            });
        }.bind(mod);

        mod.buildPartyNumberOptions = function(context, field, value, _newTerm, _searchTermsHandler) {
             let currentNumbers = context.get("number") || "";
            currentNumbers = currentNumbers.trim();
            let newValue = (currentNumbers == value) ? "" : value;

            let label="show calls to/from " + value;
            if (currentNumbers == value) {
                label = "stop searching for calls to/from " + value;
            }
            else if (currentNumbers!="") {
                label = "show calls to/from " + value + " (instead of " + currentNumbers + ")";
            }

            let link = this.addNewLink(label);
            $("a", link.container).click(function() {
                let upstreamContext = new Context();
                upstreamContext.set("number", newValue);
                // set this to "all" while we're at it.
                upstreamContext.set("numberType","all");
                link.passContextToParent(upstreamContext);
            });
        }.bind(mod);

        mod.buildGenericTermOptions = function(context, field, value, searchterms, newTerm, searchTermsHandler) {
            if (value) {
                let existingTerms = Sideview.getTopLevelSearchTokens(searchterms);

                if (existingTerms.indexOf(newTerm)!=-1) {
                    let removeLink = this.addNewLink("stop searching for "+ newTerm);
                    let newTerms = existingTerms.concat();
                    newTerms.splice(newTerms.indexOf(newTerm), 1);
                    $("a", removeLink.container).click(function() {
                        let upstreamContext = new Context();
                        upstreamContext.set("searchterms", newTerms.join(" "));
                        removeLink.passContextToParent(upstreamContext);
                    });
                }
                else {
                    let excludeLink = this.addNewLink("exclude "+ newTerm);
                    $("a", excludeLink.container).click(function() {
                        searchTermsHandler(excludeLink, "NOT " + newTerm);
                    });

                    let filterLink = this.addNewLink("search for "+ newTerm);
                    $("a", filterLink.container).click(function() {
                        searchTermsHandler(filterLink, newTerm);
                    });
                }
            }
        }.bind(mod);

        mod.buildTopValuesOptions = function(context, field, _value, _searchterms, _newTerm, _searchTermsHandler) {
            let topValuesOverTimeLink = this.addNewLink("graph top values for " + field + " over time");
            $("a", topValuesOverTimeLink.container).click(function() {
                let upstreamContext = new Context();
                upstreamContext.set("mode", "chart");
                upstreamContext.set("stat", "dc");
                upstreamContext.set("yField", "call_id");
                upstreamContext.set("xField", "_time");
                upstreamContext.set("zField", field);
                topValuesLink.passContextToParent(upstreamContext);
            });

            let topValuesLink = this.addNewLink("graph top values for " + field);
            $("a", topValuesLink.container).click(function() {
                let upstreamContext = new Context();
                upstreamContext.set("mode", "chart");
                upstreamContext.set("stat", "dc");
                upstreamContext.set("yField", "call_id");
                upstreamContext.set("xField", field);
                upstreamContext.set("zField", "");
                topValuesLink.passContextToParent(upstreamContext);
            });
        };

        mod.onContextChange = function(context) {
            // remove the previous menu items.
            $(".conjuredModule",this.container.parent()).remove();

            let tableName = context.get("click.selectedTableName");

            let field = context.get(sprintf("%s.cell.field", tableName));
            let value = context.get(sprintf("%s.cell.value", tableName));

            let searchterms = context.get("searchterms.rawValue") || "";
            searchterms = searchterms.trim();
            let newTerm = Sideview.templatize(context,"$name$=\"$value$\"",field, value);

            let searchTermsHandler = function(link, newTermOverride) {
                let upstreamContext = new Context();
                let newTerm = newTermOverride || newTerm;
                let newSearchTerms = [searchterms, newTerm];

                upstreamContext.set("searchterms", newSearchTerms.join(" "));
                link.passContextToParent(upstreamContext);
            };

            if (field=="time") {
                this.buildTimeOptions(context, field, value);
                return;
            }

            this.buildTopValuesOptions(context, field, value, searchterms, newTerm, searchTermsHandler);
            if (field=="duration") {
                this.buildDurationOptions(context, field, value);
                return;
            }
            // The 2 CheckboxPulldown modules.
            if (field=="type" || field=="globalCallId_ClusterID" ) {
                if (value) {
                    this.buildClusterAndTypeOptions(context, field, value, newTerm);
                }
                return;
            }

            // we're done with special cased fields now
            let number = context.get("number");
            // if this number is in the number field, it's silly to give them a link to narrow to it or exclude it.
            if (value && number!=value) {
                this.buildGenericTermOptions(context, field, value, searchterms, newTerm, searchTermsHandler);
            }


            if (extractor.NUMBER_TERMS.includes(field)
                || extractor.NEW_PARTY_TERMS.includes(field)) {
                if (value) {
                    this.buildPartyNumberOptions(context, field, value, newTerm, searchTermsHandler);
                }
            }

            if (!value) {
                let onlyCallsWithValuesLink = this.addNewLink("see only calls with a value for "+ field);
                $("a", onlyCallsWithValuesLink.container).click(function() {
                    searchTermsHandler(onlyCallsWithValuesLink, field + "=*");
                });
            }
        }.bind(mod);
    });


    Sideview.declareCustomBehavior("getActionMenuClasses", function(customBehaviorModule) {

        let getSingleValueType = function(context) {
            // this is always in requiredFields if we're in investigate calls
            // also it's in the hiddenFields param on the table, so it'll always be requested.
            let typeValues = context.get("row.fields.type");
            typeValues = (typeValues) ? typeValues.split(",") : [];

            // NOTE: this was only added in Canary 2.0.4.  If it's not there we just assume the
            //       clicked upon mv item is the first one.
            let mvIndex = context.get("row.cell.mvIndex")  || 0;
            return typeValues[mvIndex] || "internal";
        };
        customBehaviorModule.getModifiedContext = function(context) {
            let field = context.get("row.cell.field");
            let value = context.get("row.cell.value");


            let classes = [];
            let dataType = context.get("row.fields.data_type") || "";


            if (value) {
                // party numbers
                if ((dataType.indexOf("cucm") !=-1 || dataType.indexOf("cube") !=-1) &&
                    (extractor.NUMBER_TERMS.includes(field) || extractor.NEW_PARTY_TERMS.includes(field))) {

                    let typeSingleValue = getSingleValueType(context);

                    // this party is on the origination side.
                    if (extractor.NUMBER_TERMS_ORIG.includes(field) || extractor.NEW_PARTY_TERMS_ORIG.includes(field)) {

                        if (["internal","outgoing"].indexOf(typeSingleValue)!=-1) {
                            classes.push("internalPartyNumbers");
                        }
                        else {
                            classes.push("externalPartyNumbers");
                        }
                    }
                    // this party is on the destination side
                    else if (extractor.NUMBER_TERMS_DEST.includes(field) || extractor.NEW_PARTY_TERMS_DEST.includes(field)) {
                        if (["tandem","outgoing"].indexOf(typeSingleValue)!=-1) {
                            classes.push("externalPartyNumbers");
                        }
                        else {
                            classes.push("internalPartyNumbers");
                        }
                    }
                }
                // at the moment we punt on any MGCP gateways, since we have no clear way to strip the prefix to make
                // the gateway drilldown work, and sending them to device details is confusing.
                if (["origDeviceName", "destDeviceName","deviceName"].includes(field) && (value.indexOf("@")==-1)) {
                    let typeSingleValue = getSingleValueType(context);

                    if (field=="origDeviceName") {
                        if (["internal", "outgoing"].indexOf(typeSingleValue)!=-1) {
                            classes.push("deviceNames");
                        }
                        else {
                            classes.push("gateways");
                        }
                    }
                    if (field=="destDeviceName") {
                        if (["tandem", "outgoing"].indexOf(typeSingleValue)!=-1) {
                            classes.push("gateways");
                        }
                        else {
                            classes.push("deviceNames");
                        }
                    }
                }
                if (["origSite","destSite","site"].includes(field)) {
                    classes.push("sites");
                }
                if (["huntPilotDN"].includes(field)) {
                    classes.push("huntPilotDN");
                }
                if (["orig_gateway","dest_gateway","gateway"].includes(field)) {
                    classes.push("gateways");
                }
            }


            if (dataType.indexOf("cucm") != -1) {
                classes.push("CUCM");
            }
            else if (dataType.indexOf("cube") != -1) {
                classes.push("CUBE");
            }
            else if (dataType.indexOf("teams") != -1) {
                classes.push("Teams");
            }
            else if (dataType.indexOf("oracle_sbc") != -1) {
                classes.push("Oracle SBC");
            }
            // this ends up going down to a Switcher, so we leave it array valued
            context.set("actionMenuClass", classes);
            return context;
        };
    });



    Sideview.declareCustomBehavior("disableNoResultsMessage", function(tableModule) {
        tableModule.displayNoResultsMessage = function(_messageText) {
            this.resultsContainer.html("");
        }.bind(tableModule);
    });

    /**************************************
     * Data Types
     **************************************/
    Sideview.declareCustomBehavior("hideIfOnlyOneOption", function(checkboxPulldownModule) {
        checkboxPulldownModule.onRendered = function() {
            let options = $("option",this.select);
            let reason = "A CheckboxPulldown with only one option is not useful";

            let context = this.getContext();

            let isClusterId = (this.getParam("name")=="clusterId");
            let clusterGroupSubsetSelected = context.get("clusterGroup");

            // if the user has selected a subset of their clustergroups,  then it would
            // confuse them if the cluster pulldown then dissappeared.  EVEN if there is only
            // one cluster in it.
            if (isClusterId && clusterGroupSubsetSelected) {
                this.show(reason);
            }
            // the rest is the general case
            else if (options.length > 1) {
                this.show(reason);
            } else {
                this.hide(reason);
            }
        };

        // next up, a small change so that if all options are ever deselected
        // then instead of submitting nothing,  it sends $name$=*
        let baseMethodReference = checkboxPulldownModule.getStringValue.bind(checkboxPulldownModule);
        checkboxPulldownModule.getStringValue = function(context) {
            let selectedOptions = this.select.val() || [];
            let retVal = baseMethodReference(context);
            let name = this.getParam("name");
            if  (name=="clusterId") name = "globalCallId_ClusterID";
            if (selectedOptions.length == 0) {
                return name + "=*";
            }
            return retVal;
        }.bind(checkboxPulldownModule);

    });

    /**
     * This relies on the fact that upstream from this module, there is a ResultsValueSetter
     * that has pulled down a full set of keys from the data types csv lookup and
     * put those keys into the context as mv calls like "data_type.detail_view" etc.
     */
    Sideview.declareCustomBehavior("outputDataTypeKeys", function(customBehaviorModule) {

        let makeArray = function(val) {
            if (!Array.isArray(val)) {
                return [val];
            }
            return val;
        };
        let baseMethodReference = customBehaviorModule.getModifiedContext.bind(customBehaviorModule);
        customBehaviorModule.getModifiedContext = function(context) {
            context = baseMethodReference(context);

            if (!context.get("data_type.sourcetypes")) {
                let msg = "data_types.csv appears to be missing from $SPLUNK_HOME/etc/apps/cisco_cdr/lookups. Contact Sideview Support.";
                Sideview.broadcastMessage("error", msg);
                throw(msg);
            }

            let data_types = makeArray(context.get("data_type"));
            let labels = makeArray(context.get("data_type.label"));
            let sourcetypes = makeArray(context.get("data_type.sourcetypes"));
            let detail_views = makeArray(context.get("data_type.detail_view"));
            let streaming_extractions = makeArray(context.get("data_type.streaming_extractions"));
            let object_ids = makeArray(context.get("data_type.object_ids"));

            let flattened = [];
            sourcetypes.forEach(function (st, _i) {
                flattened = flattened.concat(st.split(" "));
            });
            context.set("data_type.sourcetypes", "( sourcetype=\"" + flattened.join("\" OR sourcetype=\"") + "\")");
            let data_type_dict = {};


            data_types.forEach(function(data_type, i) {

                data_type_dict[data_type] = {
                    "sourcetypes": sourcetypes[i]
                };
                if (labels[i]) {
                    data_type_dict[data_type]["label"] = labels[i];
                }
                if (detail_views[i]) {
                    data_type_dict[data_type]["detail_view"] = detail_views[i];
                }
                if (streaming_extractions[i]) {
                    data_type_dict[data_type]["streaming_extractions"] = streaming_extractions[i];
                }
                if (object_ids[i]) {
                    data_type_dict[data_type]["object_ids"] = object_ids[i];
                }
            });
            //console.error("we are putting in ")
            //console.error(data_type_dict)
            context.set("data_type_dict", data_type_dict);
            return context;
        };
    });




    /**************************************
     * Create Report / Create Dashboard Panel things.
     **************************************/
    Sideview.declareCustomBehavior("setSerializedContext", function(customBehaviorModule) {

        customBehaviorModule.getSerializedContext = function(context) {
            let contextToSerialize = context.clone();
            // if there's a 'foo.rawValue' key then we copy that back over the foo key
            // (Sideview convention - see SVU docs+examples.)
            $.each(contextToSerialize._root, function(name, _value) {
                if (Object.hasOwn(contextToSerialize._root, name+".rawValue")) {
                    contextToSerialize._root[name] = contextToSerialize._root[name+".rawValue"];
                }
            });
            // now basically any key that ISN'T one of these, we kill.
            let meaningfulKeys = ["number","numberType","data_type","clusterId","searchterms","optionalHeadCommand","type","advancedSearchLanguage","stat","xField","yField","zField","xFieldBins","zFieldBins","sortBy","displayChartAs","mode","charting.chart","charting.chart.stackmode","charting.chart.nullValueMode","charting.chart.showMarkers",
                //additional keys for the extensions view.
                "group","subgroup","name", "huntPilotDN",
                //additional gateway_utilization keys
                "gateway", "splitBy"];
            $.each(contextToSerialize._root, function(name, _value) {
                if (meaningfulKeys.indexOf(name)==-1) {
                    delete contextToSerialize._root[name];
                }
            });
            // Send this downstream.  It'll get picked by the REST module and
            // saved into the savedsearches.conf stanza.
            return Sideview.contextToQueryString(contextToSerialize);
        };
        customBehaviorModule.getModifiedContext = function(context) {
            context.set("serializedContext", this.getSerializedContext(context));
            return context;
        };
    });

    Sideview.declareCustomBehavior("createNewDashboardPanel", function(customBehaviorModule) {


        // NOTE: $ is not url-safe, which would mean you can't use the normal arg methods to deal
        // with urls that have $click.name$ or $click.value$ tokens that you need to end up in the
        // final URL unescaped.
        // I tried it the other way, building the escaped string and it was a NIGHTMARE
        // so this seems less evil...  use a fake constant (ACTUAL_DOLLAR_SIGN) and replace all
        // instances of it with "$" at the end.
        let DS_MARKER = "ACTUAL_DOLLAR_SIGN";
        customBehaviorModule.prettyPrint = function(xml) {
            let formatted = "";
            let reg = /(>)(<)(\/*)/g;
            xml = xml.replace(reg, "$1\n$2$3");
            let pad = 0;
            $.each(xml.split("\n"), function(index, node) {
                let indent = 0;
                if (node.match( /.+<\/\w[^>]*>$/ )) {
                    indent = 0;
                } else if (node.match( /^<\/\w/ )) {
                    if (pad != 0) {
                        pad -= 1;
                    }
                } else if (node.match( /^<\w[^>]*[^/]>.*$/ )) {
                    indent = 1;
                } else {
                    indent = 0;
                }
                let padding = "";
                for (let i = 0; i < pad; i++) {
                    padding += "  ";
                }
                formatted += padding + node + "\n";
                pad += indent;
            });
            return formatted;
        };

        let addNodeWithText = function(xmlDoc, parentNode, nodeName, nodeValue, attName, attValue, cdata=false) {
            let node = xmlDoc.createElement(nodeName);
            let textNode;
            if (cdata) {
                textNode = xmlDoc.createCDATASection(nodeValue);
            } else {
                textNode = xmlDoc.createTextNode(nodeValue);
            }
            node.appendChild(textNode);
            if (attName && attValue) {
                node.setAttribute(attName,attValue);
            }
            parentNode.appendChild(node);
        };

        /**
         * This just adds the special simpleXML parametrized drilldown values
         * $click.value$  and $click.name2$
         * which yes, are horrible.  They date from Splunk 4.1. Ask Nick about who's responsible for them,
         * it's his favorite question.
         */
        customBehaviorModule.addSpecialSimpleXMLDrilldownTokens = function(context) {
            let existingSearchterms = context.get("searchterms");
            let splitByField = context.get("zField");
            let xField = context.get("xField");
            let searchterms = [];
            if (existingSearchterms && existingSearchterms.trim().length>0) {
                searchterms.push(existingSearchterms);
            }
            // if there is an xField defined and it's not a field that has it's own special form element.
            if (xField && ["_time","type","globalCallId_ClusterID"].indexOf(xField) == -1) {
                let newTermValue = sprintf("%sclick.value%s", DS_MARKER, DS_MARKER);
                let newTerm = Sideview.templatize(context,"$name$=\"$value$\"", xField, newTermValue);
                searchterms.push(newTerm);
            }
            // if there is an xField defined and it's not a field that has it's own special form element.
            if (splitByField && ["type","globalCallId_ClusterID"].indexOf(splitByField) == -1) {
                let newTermValue = sprintf("%sclick.name2%s", DS_MARKER, DS_MARKER);
                let newTerm = Sideview.templatize(context,"$name$=\"$value$\"", splitByField, newTermValue);
                searchterms.push(newTerm);
            }
            return searchterms.join(" ").trim();
        };

        customBehaviorModule.getDrilldownURI = function(view) {
            return "splunkd/__raw/sv_view/cisco_cdr/" + view;
        };

        /**
         *  known issues
         *  1) xField or zField equal to "type" or "globalCallId_ClusterID",  it gets added to
         *     searchterms instead of the individual field.
         *
         *  2) If user creates a panel,  then later goes back in and edits the search manually
         *     the drilldown panel will be out of date and possibly broken.
         *     Solution - add the search also as a comment node?   Have a health check check
         *         whether the search still matches the comment node, and if it doesn't, warn user.
         *
         *  3) what about drilldown from other pages.
         *     FAILED IDEA was - just ask the Redirector.   Sounds nice in principle but the
         *     Redirector knows how to translate a) all the crazy Sideview-specific keys coming
         *     off Sideview Table and Chart modules, together with b) the Sideview Redirector
         *     config,   to make a drilldown URL.
         *     At the time we generate the drilldown config we have b (yay), but the (a) stuff
         *     we'll never have.  When the click happens it's later and it follows none of the
         *     improved sideview conventions and it's locked in SimpleXML code.
         *
         */

        customBehaviorModule.getDrilldownNode = function(currentView, xmlDoc, context) {
            let args = {
                "earliest" : sprintf("%searliest%s", DS_MARKER, DS_MARKER),
                "latest" : sprintf("%slatest%s", DS_MARKER, DS_MARKER)
            };

            let drilldownView = false;

            if ((currentView == "calls" && context.get("mode")=="chart") || currentView == "chart" || context.get("drilldownTarget") == "calls") {
                ["number", "numberType", "type", "clusterId", "searchterms", "data_type"].forEach(function(field) {
                    let rawValue = context.get(field);
                        if (rawValue) {
                            args[field] = rawValue;
                        }
                });

                let searchterms = this.addSpecialSimpleXMLDrilldownTokens(context);
                if (searchterms.length > 0) {
                    args["searchterms"] = searchterms;
                }
                let splitByField = context.get("zField");
                let xField = context.get("xField");

                // time drilldowns in table panels in SimpleXML "are not supported" at the moment.
                // insanely it seems to need fiddly <set> calls to make the bucket earliest/latest.
                // even though the chart viz handles this automatically.
                if (xField == "_time" && context.get("displayChartAs") == "Table") return false;

                // numeric group-by fields will get bucketed into ranges, and we dont support
                // drilldown on that at the moment.
                if (xField && (extractor.fieldExists(xField)) && extractor.fieldIsNumeric(xField)) return false;

                // likewise bucketed ranges on split by field
                if (splitByField && (extractor.fieldExists(splitByField)) && extractor.fieldIsNumeric(splitByField)) return false;

                if (xField == "type") {
                    args[xField] = sprintf("%sclick.name%s", DS_MARKER, DS_MARKER);
                }
                if (splitByField == "type") {
                    args[splitByField] = sprintf("%sclick.name2%s", DS_MARKER, DS_MARKER);
                }

                if (xField == "globalCallId_ClusterID") {
                    args["clusterId"] = sprintf("%sclick.name%s", DS_MARKER, DS_MARKER);
                }
                if (splitByField == "globalCallId_ClusterID") {
                    args["clusterId"] = sprintf("%sclick.name2%s", DS_MARKER, DS_MARKER);
                }

                drilldownView = "calls";
            }
            else if (currentView == "calls") {
                args["globalCallID_callId"] = sprintf("%srow.globalCallID_callId%s", DS_MARKER, DS_MARKER);
                args["globalCallID_callManagerId"] = sprintf("%srow.globalCallID_callManagerId%s", DS_MARKER, DS_MARKER);
                args["globalCallId_ClusterID"] = sprintf("%srow.globalCallId_ClusterID%s", DS_MARKER, DS_MARKER);
                drilldownView = "call_detail";
            }
            else if (["extensions", "devices", "sites"].indexOf(currentView)!=-1) {
                let noun = currentView.substring(0, currentView.length - 1);
                // extensions is actually inconsistent, and calls it "number"
                let arg = (noun == "extension") ? "number" : noun;
                args[arg] = sprintf("%srow.%s%s", DS_MARKER, arg, DS_MARKER);
                drilldownView = noun + "_detail";
            }
            else {
                return false;
            }

            let uriStr = "/" + this.getDrilldownURI(drilldownView) + "?" + Sideview.dictToString(args);
                uriStr = uriStr.replace(/ACTUAL_DOLLAR_SIGN/g,"$");

            let drilldownNode = xmlDoc.createElement("drilldown");
            addNodeWithText(xmlDoc, drilldownNode, "link", uriStr, "target", "_blank");
            return drilldownNode;
        };

        /**
         * This is here only so that the automated js tests can mock it.
         */
        customBehaviorModule.getRootRelativeURL = function() {
            let url = document.location.href;
            url = url.replace(document.location.protocol + "//", "");
            url = url.replace(document.location.host, "");
            return url.replace("/" + Sideview.getLocale(), "");
        };
        /**
         * for each of our views, it tries to return the consistent link label like "investigate these calls"
         */
        customBehaviorModule.getFullResultsLinkLabel = function(currentView) {
            if (["calls", "devices", "extensions", "gateways", "groups", "sites"].indexOf(currentView) != -1) {
                return "investigate these " + currentView;
            }
            return "view full results";
        };

        customBehaviorModule.getModifiedContext = function(context) {

            let xmlDoc = document.implementation.createDocument(null, "row");

            let vizNodeTag, chartType;

            switch(this.getParam("arg.visualization")) {

                case "table":
                    vizNodeTag = "table";
                    break;
                case "single":
                    vizNodeTag = "single";
                    break;
                case "line":
                    vizNodeTag = "chart";
                    chartType = "line";
                    break;
                case "column":
                    vizNodeTag = "chart";
                    chartType = "column";
                    break;
                default:
                    // if they are present but emptystring-valued, we assume we're in chart with "over nothing" turned on.
                    if (context.get("xField") == "" && context.get("zField") == "") {
                        vizNodeTag = "single";
                    }
                    else if (context.get("displayChartAs") == "Chart" && context.get("xField") != "") {
                        vizNodeTag = "chart";
                        chartType = context.get("charting.chart") || "column";
                    }
                    // well... something believes that a chart type is relevant here.
                    else if (context.get("charting.chart") && context.get("displayChartAs") != "Table") {
                        vizNodeTag = "chart";
                        chartType = context.get("charting.chart") || "column";
                    }
                    // if there's no chart tab selected upstream,
                    // or we're in "over nothing" but there IS a split by, then ok fine table.
                    else {
                        vizNodeTag = "table";
                    }
            }

            let currentView = Sideview.getCurrentView();

            //  BRACE YOURSELF.... WE'RE USING ACTUAL RAW DOM METHODS
            //  Which if you were born after 1985 you've probably never seen.

            let panelNode = xmlDoc.createElement("panel");

            let vizNode = xmlDoc.createElement(vizNodeTag);
            addNodeWithText(xmlDoc, vizNode, "title", context.get("panelTitle"));

            let searchNode = xmlDoc.createElement("search");
            let spl = context.get("searchPlusFields");

            addNodeWithText(xmlDoc, searchNode, "query", spl, false, false, true);
            if (context.get("search.timeRange.earliest")!=0) {
                addNodeWithText(xmlDoc, searchNode, "earliest", context.get("search.timeRange.earliest"));
            }
            if (context.get("search.timeRange.latest")) {
                addNodeWithText(xmlDoc, searchNode, "latest", context.get("search.timeRange.latest"));
            }

            panelNode.appendChild(vizNode);
            if (vizNodeTag=="table") {
                let htmlNode = xmlDoc.createElement("html");

                let label = this.getFullResultsLinkLabel(Sideview.getCurrentView());
                let rootRelativeURL = this.getRootRelativeURL();
                addNodeWithText(xmlDoc, htmlNode, "a", label, "href", rootRelativeURL, false);
                panelNode.appendChild(htmlNode);
            }
            vizNode.appendChild(searchNode);

            if (vizNodeTag == "chart" ) {

                if (chartType=="column") {
                    // this is to workaround a minor but annoying flaw in the Splunk charts
                    // where it always labels the xField.    This makes sense when the xField is like "infected_host"
                    // and is just annoying when the xField is "_time" because
                    // a) it is pretty much always obvious from the other labels that the x-axis is time.
                    // b) the underscore is confusing.
                    // c) it takes up an extra row for... no real reason.
                    if (context.get("xField") == "_time") {
                        addNodeWithText(xmlDoc, vizNode, "option", "collapsed", "name", "charting.axisTitleX.visibility");
                    }
                }
                else {
                    addNodeWithText(xmlDoc, vizNode, "option", chartType, "name", "charting.chart");
                    let nullValueMode = context.get("charting.chart.nullValueMode");
                    if (nullValueMode) {
                        addNodeWithText(xmlDoc, vizNode, "option", nullValueMode, "name", "charting.chart.nullValueMode");
                    }
                }
                // we only turn on stackMode if there is actually a split-by field.
                // if we turn it on in all cases, then users who later try and turn on
                // "show data labels" will get confusing behavior where the labels are rendered
                // inside the column, where the labels are largely illegible.
                // granted... this here might confuse the user who creates the dashboard panel
                // with no splitby, and then modifies it later to add the splitby but....
                // that user is deciding to do that, and they can consult the SimpleXML charting
                // reference.
                if (context.get("zField")) {
                    let stackMode = context.get("charting.chart.stackMode") || "default";
                    if (stackMode != "default") {
                        addNodeWithText(xmlDoc, vizNode, "option", stackMode, "name", "charting.chart.stackMode");
                    }
                }
            }


            if (context.get("drilldownEnabled") == "False") {
                // <option name="drilldown">none</option>
                addNodeWithText(xmlDoc, vizNode, "option", "none", "name", "drilldown");
            }
            else {
                let drilldownNode = this.getDrilldownNode(currentView, xmlDoc, context);
                if (drilldownNode) {
                    vizNode.appendChild(drilldownNode);
                }
            }
            // only for Table do we add the <panel>
            // for other viz nodes we ignore and just append the viz itself.
            if (vizNodeTag=="table") {
                xmlDoc.documentElement.appendChild(panelNode);
            } else {
                xmlDoc.documentElement.appendChild(vizNode);
            }

            let xmlStr = new XMLSerializer().serializeToString(xmlDoc);
            context.set("newDashboardPanel", this.prettyPrint(xmlStr));

            return context;
        };
    });




    Sideview.declareCustomBehavior("createNewDashboardButton", function(buttonModule) {
        buttonModule.replaceSpacesWithUnderscores = function(value) {
            if (!value) return "";
            return value.replace(/ /g,"_");
        }.bind(buttonModule);

        buttonModule.customClickHandler= function() {
            let context = this.getContext();
            let name = context.get("dashboardName") || "";
            // splunkd's error message says
            // must contain only alphanumeric ASCII, '-', '.', and '_' characters; and must not start with '.'.
            $(".Layer .inlineError").remove();
            let matches = name.match(/[^a-z0-9.-_\s]+/g);
            if (matches && matches.length>0) {
                let inlineError = $("<div>")
                    .addClass("inlineError")
                    .html(_("Unable to create dashboard panel - dashboard names must <br>\nbe only numbers, letters, spaces, '-', '.' and '_' characters."));
                let layerReference=false;
                this.withEachAncestor(function(module) {
                    if (module.container.hasClass("Layer")) {
                        layerReference = module.container;
                        return;
                    }
                });
                if (layerReference) {
                    layerReference.prepend(inlineError);
                }
                else {
                    alert(inlineError);
                }
                return false;
            }
            return true;
        }.bind(buttonModule);

        buttonModule.getModifiedContext = function(context) {
            let keyName = "dashboardName";
            let dashboardName = context.get(keyName);
            let cleanName = this.replaceSpacesWithUnderscores(dashboardName);
            context.set(keyName, cleanName);
            context.set(keyName +".rawValue", dashboardName);
            return context;
        }.bind(buttonModule);
    });

    Sideview.declareCustomBehavior("insertNewPanelWithinEaiData", function(module) {

        module.getFirstMatchingChild = function(xmlNode, tagNameArr) {
            if (!xmlNode) {
                console.error("getFirstMatchingChild given empty xmlNode");
                return false;
            }
            for (let i=0; i<xmlNode.childNodes.length;i++) {
                let tagName = xmlNode.childNodes[i].tagName;
                if (tagName && tagNameArr.indexOf(tagName)!=-1) {
                    return xmlNode.childNodes[i];
                }
            }
        };

        module.onContextChange = function(context) {
            context = context || this.getContext();
            let eaiData = context.get("eaiData");
            let parser  = new DOMParser();

            let xmlDoc = parser.parseFromString(eaiData, "text/xml");
            let newRow = parser.parseFromString(context.get("newDashboardPanel"), "text/xml").documentElement;

            // be cause DOM methods are pretty awful.  This allows us to
            // proceed carefully and insert our new row into the exact right place.
            let rootNode = this.getFirstMatchingChild(xmlDoc, ["dashboard","form"]);
            let firstRow = this.getFirstMatchingChild(rootNode, ["row"]);

            if (firstRow) {
                xmlDoc.documentElement.insertBefore(newRow,firstRow);
            } else {
                rootNode.appendChild(newRow);
            }
            let serializery = new XMLSerializer();
            this.newPanel = serializery.serializeToString(xmlDoc);
        };

        module.getModifiedContext = function(context) {
            context.set("eaiData",this.newPanel);
            return context;
        };
    });

    Sideview.declareCustomBehavior("reloadSavedSearchesInNav", function(htmlModule) {
        htmlModule.onHTMLRendered = function() {
            let AppNav = Sideview.getModule("AppNav_0");
            try {
                $.when(AppNav.reloadSavedSearches())
                    .done(function() {
                    AppNav.reloadMenus();
                });
            }
            catch(err) {
                console.error(err);
            }
        };
    });

    Sideview.declareCustomBehavior("reloadViewsInNav", function(htmlModule) {
        htmlModule.onHTMLRendered = function() {
            let AppNav = Sideview.getModule("AppNav_0");
            try {
                $.when(AppNav.reloadViews())
                    .done(function() {
                    AppNav.reloadMenus();
                });
            }
            catch(err) {
                console.error(err);
            }
            if (htmlModule.isPageLoadComplete() && Sideview.getCurrentView()=="home") {
                let delayedReload = function() {
                    let reloadSearch = function(module) {
                        if (module.moduleType=="Search") {
                            module.pushDownstream();
                            return false;
                        }
                    };
                    htmlModule.withEachAncestor(reloadSearch);
                };
                window.setTimeout(delayedReload, 3000);
            }
        };
    });
    /**************************************
     * END Create Report / Create Dashboard Panel things.
     **************************************/



    /**
     * This is what allows the "number" fields to say "enter number(s)"
     *  in greyed out text, only when the field is empty, and have that
     *  text vanish when the user clicks into or tabs into the field.
     */
    Sideview.declareCustomBehavior("inlineNumberLabel", function(textFieldModule) {

        let normalTextColor = $(textFieldModule.input).css("color") || "#000000";
        let defaultValue = textFieldModule.getParam("default");

        textFieldModule.input.css("color","#aaa");

        textFieldModule.resetToDefault = function() {
            this.input.val(defaultValue);
            this.input.css("color","#aaa");
        }.bind(textFieldModule);


        // inlines the default implementation, but we have to sneak OUT the
        // defaultValue
        textFieldModule.getModifiedContext= function(context) {
            // the textField module still had a bug here until Canary 1.5.9
            context = context || this.getContext();

            let template = this.getParam("template");
            let rawValue = this.input.val() || "";
            if (rawValue == defaultValue) rawValue="";

            context.set(this.name + ".element", Sideview.makeUnclonable(this.input));
            // we do not backslash escape rawValue, because we assume it is NOT
            // destined for searches.  rawValue is for QS args and for labels.
            context.set(this.name + ".rawValue", rawValue);

            let templatizedValue = Sideview.safeTemplatize(context, template, this.name, rawValue);

            context.set(this.name + ".value", templatizedValue);
            context.set(this.name, templatizedValue);
            return context;
        }.bind(textFieldModule);

        // inlines the default implementation, but whenever "" is written, we
        // write the defaultValue instead
        textFieldModule.setToContextValue= function(context) {
            let value = Sideview.getValueForFormElementSelection(this.name,context);
            if (value=="") {
                value=defaultValue;
                this.input.css("color", "#aaa");
            } else {
                this.input.css("color", normalTextColor);
            }
            this.input.val(value);
        }.bind(textFieldModule);


        // custom event handling for the "enter number(s)" string

        let maybeClearPlaceholderValue = function() {
            if (this.input.val().trim() == defaultValue) {
                this.input.val("");
                this.input.css("color", normalTextColor);
            }
        }.bind(textFieldModule);

        let maybeSetPlaceholderValue = function() {
            if (this.input.val().trim()=="") {
                this.input.val(defaultValue);
                this.input.css("color","#aaa");
            }
            else if (this.input.val().trim() != defaultValue) {
                this.input.css("color", normalTextColor);
            }
        }.bind(textFieldModule);

        // 1) if they focus into it.
        textFieldModule.input.bind("focus", maybeClearPlaceholderValue);
        // 2) for good measure if they click (whether or not they're ALREADY
        // focused. This is actually a subtly separate case)
        textFieldModule.input.bind("click", maybeClearPlaceholderValue);
        // Crazy Idea I didn't Do ) if all else fails, and  they start typing....
        // clear the default value onkeydown if it's in there.
        // NOTE: keydown runs and finishes BEFORE the triggering key is
        // actually entered into the field
        // However... seems like overkill.
        //textFieldModule.input.bind("keydown",  maybeClearPlaceholderValue);

        // 3) onblur, if value is empty then we put the placeholder value back.
        textFieldModule.input.bind("blur",  maybeSetPlaceholderValue);

        // 4) but the user can focus into the field BEFORE the module even initalizes.
        // So we fire it explicitly now.
        if ($(textFieldModule.input).is(":focus")) {
            maybeClearPlaceholderValue();
        }
    });

    Sideview.declareCustomBehavior("qualifyNumberOfResults", function(htmlModule) {

        htmlModule.addCustomKeys = function(context) {
            let search = context.getSplunkSearch();
            let job = search.job;
            if (job && !job.isDone() && job.getResultCount()>0 && job.getResultPreviewCount()>0) {
                context.set("qualifier", "at least");
            }
        };

        let showHideJobProgressModule = function(which) {
            console.assert(["show","hide"].indexOf(which)!=-1);

            htmlModule.parent.withEachDescendant(function(module) {
                if (module.moduleType=="ProgressIndicator") {
                    // canary modules can have many different axes/reasons to be visible/invisible
                    // but if any say they should be invisible, they get hidden
                    let visibilityReason = "custom behavior for pause";
                    if (which=="hide") {
                        module.hide(visibilityReason);
                    }
                    else {
                        module.show(visibilityReason);
                    }
                }
            });

        };

        let visibilityReason = "Hide the whole header after a cancel";
        let methodReference = htmlModule.onContextChange.bind(htmlModule);
        // whenever a new push comes from above, it will reset the search so we reset our little state machine.
        htmlModule.onContextChange = function(context) {
            this.instruction = "new calls search";
            this.show(visibilityReason);

            this.jobStartedAt = new Date().valueOf();
            $(".conjuredModule",this.container.parent()).remove();
            return methodReference(context);
        };
        htmlModule.onJobCancelled = function(_evt) {
            if (this.button) {
                this.button.container.remove();
            }
            this.hide(visibilityReason);
            this.resetUI();
        };

        htmlModule.resetUI = function() {
            showHideJobProgressModule("show");
        };
        var baseOnJobProgressMethod = htmlModule.onJobProgress.bind(htmlModule);
        htmlModule.onJobProgress = function(evt, job) {

            if (!this.isVisible()) {
                return false;
            }
            let context = this.getContext();

            if (Sideview.getCurrentView()!="calls") {
                this.renderHTML(context);
                return;
            }

            let flipToPausedState = function(job) {

                if (!this.isVisible()) {
                    console.error("the calls table header isn't visible, which means we shouldn't show our conjured button.");
                    return false;
                }
                this.instruction = "pause";
                showHideJobProgressModule("hide");
                $(".conjuredModule",this.container.parent()).remove();
                this.button = createButton(job);
            }.bind(htmlModule);
            let flipToUnpausedState = function() {
                if (this.instruction=="pause") {
                    this.instruction = "finish";
                }
                if (this.button) {
                    this.button.container.remove();
                }
                showHideJobProgressModule("show");
            }.bind(htmlModule);

            let createButton = function(job) {
                let label = "Resume";
                let container = $("<div><fieldset><button class=\"buttonPrimary svButton\"><span>" + label + "</span></button></fieldset></div>")
                    .addClass("Module")
                    .addClass("Button")
                    .addClass("conjuredModule")
                    .css("margin-left", "10px")
                    .insertAfter(this.container);
                let button = new Button(container, {"label":label});
                button.moduleId = "conjuredResumeButton";
                button.blueWire = true;
                button.customClickHandler = function(_evt) {
                    job.unpause();
                    flipToUnpausedState();
                };
                button.baseContext = this.getContext();
                button.markPageLoadComplete();
                this.addChild(button);
                return button;
            }.bind(htmlModule);

            let now = new Date().valueOf();
            let secondsElapsed = (now - this.jobStartedAt)/1000;


            // if we're still in the newbie state
            if (this.instruction=="new calls search"
                    && job.getScanCount()>10000
                    && (secondsElapsed > AUTOPAUSE_AT_N_SECONDS || job.getResultPreviewCount() > 10)) {
                job.pause();
                flipToPausedState(job);
            }
            // if we're in the paused state, it's likely that WE just did that
            // however it's possible the searchControls module did.
            // so we don't assume that all the things are already done
            if (this.instruction == "pause" || job.isPaused()) {
                flipToPausedState(job);
                context.set("isPaused", "(automatically paused)");
            }
            // likewise the unpausing was likely us, but could have been someone else.
            else {
                flipToUnpausedState();
                context.set("isPaused", "(running)");
            }
            baseOnJobProgressMethod(evt, job);
        };
    });




    Sideview.declareCustomBehavior("getKeysForModifiers", function(customBehaviorModule) {
        customBehaviorModule.getModifiedContext = function(context) {
            context = context || this.getContext();
            let modifiers = context.get("modifiers.rawValue") || "";

            if (modifiers.indexOf("numbersWithZeroCalls")!=-1) {
                context.set("includeNumbersWithZeroCalls","| inputlookup append=t groups | search NOT group=\"PLACEHOLDER GROUP\"");
            }

            if (modifiers.indexOf("sitesWithZeroCalls")!=-1) {
                context.set("includeSitesWithZeroCalls","| append [ | inputlookup cidr | rename site_name as site | fields site subnet subnet_description country]");
            }

            // this is for the "groups" view.
            if (modifiers.indexOf("groupsWithZeroCalls")!=-1) {
                context.set("includeGroupsWithZeroCalls","| append [| inputlookup groups | search group!=\"PLACEHOLDER GROUP\" | stats values(number) as number count by group ]");
            }

            if (modifiers.indexOf("devicesWithZeroCalls")!=-1) {
                context.set("addDevicesWithNoCalls","| inputlookup append=true devices | eval device = if(isnull(device), name, device) | search NOT device=\"PLACEHOLDER_DEVICE\" | eval number=if(isnull(number),directoryNumber,number)");
            }


            // include or not include calls of zero duration.
            if (modifiers.indexOf("callsWithZeroDuration")!=-1) {
                // tee hee
            }
            else {
                context.set("excludeCallsWithZeroDuration", "duration!=\"0\"");
            }
            return context;
        };
    });

    Sideview.declareCustomBehavior("showUserWarningsAndNotices", function(customBehaviorModule) {
        customBehaviorModule.onContextChange= function(context) {

            context = context || this.getContext();
            let message = false;
            let level = "warn";
            let modifiers = context.get("modifiers.rawValue") || "";


            // D'oh. we kind of need a message if you have failed_calls selected but count calls
            // with zero duration is off.

            if (currentlyWithin(["devices"])) {
                if (modifiers.indexOf("devicesWithZeroCalls") != -1) {
                    if (context.get("realDevicesExistInDevicesLookup")=="no") {
                        if (context.get("axlExists") == "yes") {
                            message = "Warning - you have installed the Supporting AXL App for Cisco CDR Reporting and Analytics but it has not yet generated a devices.csv file. Since the file does not yet exist, some field values and options on this page won't work as expected.";
                        }
                        else {
                            message = "Note that \"include devices with zero calls\" only works when devices.csv is populated. See \"Setup > Define devices\" for more details.";
                        }
                    }
                    else if (context.get("sites")) {
                        message = "Note that when you have \"show devices with zero calls\" active, and also any sites selected,  the devices with zero calls will be shown regardless of what sites/subnets their IP addresses would appear in. Contact Sideview for filtering suggestions here.";
                    }
                }
                else if (!message && context.get("realDevicesExistInDevicesLookup")=="no") {
                    message = "Note that many fields like productName will only exist if you have set up the devices lookup. See \"Setup > Define devices\" for more details.";
                }
            }
            else if (currentlyWithin(["groups"])) {
                if (context.get("moreThanOneRowInGroupsLookup")=="no") {
                    message = "The groups lookup has not been set up, so this page will only list one row with a group of \"(none)\". See \"Setup > Define groups and extensions\" for more details on how you can set up this optional feature.";
                    level = "error";
                }
            }

            if (message) {
                Sideview.broadcastMessage(level, message);
            }
        };
    });

    Sideview.declareCustomBehavior("showHiddenMessages", function(htmlModule) {
        htmlModule.onHTMLRendered= function() {
            $(".hiddenInitially", this.container).css("display","block");
        };
    });



    Sideview.declareCustomBehavior("showHideCustomCron", function(textFieldModule) {
        let baseMethodReference = textFieldModule.onContextChange.bind(textFieldModule);
        textFieldModule.onContextChange= function(context) {
            let cron_type = context.get("cron_type");
            let visibilityReason = "only show custom cron textfield if custom cron is selected";
            if (cron_type) {
                this.hide(visibilityReason);
            } else {
                this.resetToDefault();
                this.show(visibilityReason);
            }
            return baseMethodReference(context);
        };
    });



    /**
     * used in call_detail
     */
    Sideview.declareCustomBehavior("useLocaleForTimeStampRendering", function(htmlModule) {
        htmlModule.addCustomKeys = function(context) {

            let keys = ["originated","connected","disconnected"];
            let k, value, values;
            for (let i=0,len=keys.length;i<len; i++) {
                k = keys[i];
                value = context.get(k);
                if (value) {
                    values = value.split(",");
                    let output = [];
                    for (let j=0,jLen=values.length;j<jLen;j++) {
                        if (values[j]>0) {
                            output.push(format_datetime(values[j],"long"));
                        } else {
                            output.push("N/A");
                        }
                    }
                    context.set(k,output.join(", "));
                }
            }
        };
    });

    /**
     * used in call_detail and extension_detail
     */
    Sideview.declareCustomBehavior("onlySubmitIfFieldsAreSet", function(customBehaviorModule) {

        customBehaviorModule.isReadyForContextPush = function() {
            let requiredKey = this.getParam("arg.requiredKey");
            let c = this.getContext();
            if (c.get(requiredKey)) {
                return true;
            }
            return false;
        }.bind(customBehaviorModule);

        customBehaviorModule.onContextChange = function(_context) {

            if (this.isReadyForContextPush()) {
                this.showDescendants("hidePageContentsUntilRequiredFieldEntered");
                $(".dashboardCell").show();
                $(".flexContainer").show();
                $("#viewerPageInstructions").hide();
            } else {
                this.hideDescendants("hidePageContentsUntilRequiredFieldEntered");
                $(".dashboardCell").hide();
                $(".flexContainer").hide();
                $("#viewerPageInstructions").show();
                $("#viewerPageInstructions").parents().show();
            }
        };
    });


    /**
     * used only in call_detail
     */
    Sideview.declareCustomBehavior("createMultiValueClauses", function(resultsValueSetter) {

        // basically just returns a big string like:
        // callingPartyNumber="n" OR finalCalledPartyNumber="n" OR ...

        let baseMethodReference = resultsValueSetter.getModifiedContext.bind(resultsValueSetter);
        resultsValueSetter.getModifiedContext = function(context) {
            let modCon = baseMethodReference(context);

            let link = "<a href=\"extension_detail?number=%s&autoRun=True\">%s</a>";

            for (let i=0,iLen=extractor.NEW_PARTY_TERMS.length;i<iLen;i++) {
                let multipleValues = modCon.get(extractor.NEW_PARTY_TERMS[i]);
                // the joining on "::::" has the benefit of making the field values always
                // a single string value.  Without that they're sometimes mv values (arrays)
                // and sometimes singlevalued (strings).
                if (multipleValues) {
                    multipleValues = multipleValues.split("::::");
                    let term  = [];
                    let label = [];
                    for (let j=0,jLen=multipleValues.length;j<jLen;j++) {
                        let n = multipleValues[j];
                        term[j]  = extractor.getSearchTermsForSingleNumber(extractor.NEW_PARTY_TERMS, n);
                        label[j] = sprintf(link, n, n);
                    }
                    modCon.set(extractor.NEW_PARTY_TERMS[i] + ".searchTerm", "(" + term.join(" OR ") + ")");
                    modCon.set(extractor.NEW_PARTY_TERMS[i] + ".link", label.join(", "));
                    modCon.set(extractor.NEW_PARTY_TERMS[i] + ".values", "(\"" + multipleValues.join("\", \"") + "\")");
                }
            }
            let deviceTerms = ["origDeviceName", "destDeviceName"];
            link = "<a href=\"device_detail?device=%s&autoRun=True\">%s</a>";
            for (let i=0,iLen=deviceTerms.length;i<iLen;i++) {
                let multipleValues = modCon.get(deviceTerms[i]);
                if (multipleValues) {
                    multipleValues = multipleValues.split("::::");
                    let label = [];
                    for (let j=0,jLen=multipleValues.length;j<jLen;j++) {
                        let n = multipleValues[j];
                        label[j] = sprintf(link, n, n);
                    }
                    modCon.set(deviceTerms[i] + ".link", label.join(", "));
                }
            }
            return modCon;
        }.bind(resultsValueSetter);
    });





    /**********************************************
     * HOMEPAGE THINGS
     **********************************************/


    Sideview.declareCustomBehavior("enableShowLinks", function(htmlModule) {
        htmlModule.onHTMLRendered = function() {
            $(".showExamples", this.container).click(function(evt) {
                let link = $(evt.target);
                let div = $(link).parent();
                div.find(".exampleReports").show();
            });

            $(".expand", this.container).click(function(evt) {
                let link = $(evt.target);
                let shortDesc = $(link).parent();
                let td = $(shortDesc).parent();
                shortDesc.hide();
                td.find(".longDesc").show();
            });
        };
    });



    Sideview.declareCustomBehavior("setPageStateIfCriticalHealthCheckFailed", function(htmlModule) {
        let methodReference = htmlModule.renderHTML.bind(htmlModule);
        htmlModule.renderHTML = function(context) {
            let severityLevel = context.get("results[0].severity_level");
            // there's an initial render before the results are actually back.
            if (severityLevel==null) {
                return;
            }
            if (severityLevel>=2) {
                $("body").addClass("criticalHealthChecksFailed");
            } else {
                this.hide("Homepage users don't care about critical health checks if they PASS");
            }
            return (methodReference(context));
        };
    });

    /**
     * only used on gateway_utilization and busy_hour_calculator
     */
    Sideview.declareCustomBehavior("hideAndReturnNullIfInternalPresent", function(pulldownModule) {
        let occReference = pulldownModule.onContextChange.bind(pulldownModule);
        pulldownModule.onContextChange = function(context) {
            context = context || this.getContext();
            let types = context.get("type.rawValue") || CALL_TYPE_VALUES;
            if (types.indexOf("internal")!=-1) {
                this.hide("internal calls have no gateway");
            } else {
                this.show("internal calls have no gateway");
            }
            return occReference(context);
        };
        let gmcReference = pulldownModule.getModifiedContext.bind(pulldownModule);
        pulldownModule.getModifiedContext = function(context)  {
            let types = context.get("type.rawValue") || CALL_TYPE_VALUES;
            if (types.indexOf("internal")!=-1) {
                context.set(this.name,"");
                return context;
            }
            else {
                return gmcReference();
            }
        };
    });

    /**
     * only used on busy_hour_calculator
     */
    Sideview.declareCustomBehavior("displayMessageIfInternalPresent", function(customBehaviorModule) {
        customBehaviorModule.onContextChange = function(context) {
            context = context || this.getContext();
            let types = context.get("type.rawValue") || CALL_TYPE_VALUES;
            if (types.indexOf("internal")!=-1) {
                this.container
                    .text("(NOTE that this tab wont show any results for internal calls)")
                    .css("height","25px");
            } else {
                this.container.text("").css("height","0px");
            }
        };
    });

    /**
     * only used on gateway_utilization and busy_hour_calculator
     * It's possible this can be replaced by stock config eg conditional ValueSetter modules.
     */
    Sideview.declareCustomBehavior("createRequiredExtractions", function(customBehaviorModule) {
        customBehaviorModule.getModifiedContext = function(context) {
            let splitBy  = context.get("splitBy.rawValue");

            if (splitBy=="site") {
                context.set("required_extractions", "| `customizable_sites_extractions` | `get_sites` | mvexpand site");
            }
            if (splitBy && ["gateway","type"].indexOf(splitBy)!=-1) {
                let selectedValues = context.get(splitBy + ".rawValue");
                if (selectedValues && selectedValues.length>0) {
                    let explicitFieldList = ["_time", "_span"];
                    explicitFieldList = explicitFieldList.concat(selectedValues);
                    context.set("explicitFieldList", "| fields " + explicitFieldList.join(" "));
                }
            }
            // used for the header that says "incoming, outgoing and internal calls dropped ..."
            let typeList = context.get("type.rawValue") || CALL_TYPE_VALUES;
            let customLabel;
            if (typeList.length==1) {
                customLabel = typeList[0];
            }
            else {
                customLabel = typeList.slice(0,typeList.length-1).join(", ") + " and " + typeList[typeList.length-1];
            }
            context.set("type.customLabels", customLabel);
            return context;
        };
    });

    /**
     * This is used for the old filenames we ship like "browse.xml",  just for users who have
     * bookmarked these...
     */
    Sideview.declareCustomBehavior("redirectLegacyViewNames", function() {
        let currentView = Sideview.getCurrentView();
        let redirects = {
            "browse": "calls",
            "browse_cube": "investigate_cube"
        };
        if (currentView in redirects) {
            let replacement = redirects[currentView];
            let urlDict = Sideview.getURLDict();
            document.location = replacement + "?" + Sideview.dictToString(urlDict);
        }
    });

    Sideview.declareCustomBehavior("getBrowserInfo", function(module) {
        module.getModifiedContext = function(context) {
            context.set("userAgent", window.navigator.userAgent);
            return context;
        };
    });

}

