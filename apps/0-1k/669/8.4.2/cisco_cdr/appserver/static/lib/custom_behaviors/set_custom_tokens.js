// Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
/* global sprintf, _, localAppStaticUrlPrefix */
define(
    ["jquery",
    "sideview",
    "context",
    localAppStaticUrlPrefix + "lib/extractor.js",

    ],
    function($, Sideview, Context, extractor) {



    function getBaseMessage(context) {
        let message = {};

        let tokens = {}
        tokens["number"] = context.get("number") || false;
        tokens["searchterms"] = context.get("searchterms") || false;
        tokens["fields"] = context.get("results.fields") || false;
        tokens["type"] = context.get("type") || false;


        message.view = Sideview.getCurrentView();
        message.tokens = tokens;
        return message;
    }
    Sideview.utils.declareCustomBehavior("tourEnabledFields", function(fieldsModule) {

        fieldsModule.getBestExampleField = function() {
            let possibleFields = ["quality", "orig_device_type", "dest_device_type", "origDeviceName", "destDeviceName", "callMediaType", "destAudioCodec", "destVideoCodec", "duration", "duration_elapsed"]
            for (const field of possibleFields) {
                if (!this.fields.includes(field)) return field;
            }
            return "quality";
        }.bind(fieldsModule);

        let lazyBuildLayer_mr = fieldsModule.lazyBuildLayer.bind(fieldsModule);
        fieldsModule.lazyBuildLayer = function() {
            if (window.tourWindow) {
                let context = this.getContext();
                let message = getBaseMessage(context);
                message.customBehavior = this.getParam("customBehavior") + " - openFieldPicker";
                this.relevantField = this.getBestExampleField();
                message.relevantField = this.relevantField;
                window.tourWindow.postMessage(message, window.origin);
            }

            return lazyBuildLayer_mr();

        }.bind(fieldsModule);

        let addSelectedField_mr = fieldsModule.addSelectedField.bind(fieldsModule);
        fieldsModule.addSelectedField = function(field) {
            if (window.tourWindow) {
                if (field == this.relevantField) {
                    let context = this.getContext();
                    let message = getBaseMessage(context);
                    message.customBehavior = this.getParam("customBehavior") + " - field added";
                    message.relevantField = this.relevantField;
                    window.tourWindow.postMessage(message, window.origin);
                }
            }
            return addSelectedField_mr(field);
        }

        let renderResults_mr = fieldsModule.renderResults.bind(fieldsModule);
        fieldsModule.renderResults = function (envelope) {
            if (window.tourWindow) {
                let currentFilter = $(".filterAvailableFields input", this.layer).val();
                if (this.relevantField) {
                    let prefix = this.relevantField.substring(0,4)
                    if (currentFilter.indexOf(prefix) == 0) {
                        let context = this.getContext();
                        let message = getBaseMessage(context);
                        message.customBehavior = this.getParam("customBehavior") + " - filtered";
                        message.relevantField = this.relevantField;
                        window.tourWindow.postMessage(message, window.origin);
                    }
                }
            }
            return renderResults_mr(envelope);
        }.bind(fieldsModule);
    })

    Sideview.utils.declareCustomBehavior("tourListener", function(customBehaviorModule) {

        /*
        if (! ("tourWindow" in window)) {
            console.error("there is no tourWindow reference, so this is a worst-case scenario but we are explicitly opening a clean tour window with window.open")
            let windowFeatures = "popup=true,left=20,top=20,width=600,height=600";
            window.tourWindow = window.open("tour?view=" + Sideview.getCurrentView(), "tourWindow", windowFeatures);
            console.error(window.tourWindow)
        }
        else {
            console.error("presumably tourWindow exists")
            console.error(window.tourWindow)
        }
        */



        customBehaviorModule.onContextChange = function(context) {
            if (window.tourWindow) {
                //console.error("posting a message to the tourWindow")
                let message = getBaseMessage(context);
                message.customBehavior = this.getParam("customBehavior")
                window.tourWindow.postMessage(message, window.origin);
            }
        }
    });


    Sideview.declareCustomBehavior("tour_chartShowing", function(mod) {
        mod.onContextChange = function(evt) {
            if (window.tourWindow) {
                let context = this.getContext();
                let message = getBaseMessage(context);
                let splitByField = context.get("zField");
                // avoid emptystring values just out of general paranoia.
                message.relevantField = splitByField || false;

                message.customBehavior = this.getParam("customBehavior")
                console.error("about to post " + message.customBehavior + " from the main window")
                window.tourWindow.postMessage(message, window.origin);
            }
        }.bind(mod);
    })




    Sideview.declareCustomBehavior("tour_zeroCallsFound", function(mod) {
        mod.onJobDone = function(evt) {
            if (window.tourWindow) {
                let context = this.getContext();
                let search = context.getSplunkSearch();
                if (search && search.getResultCount() == 0) {
                    let message = getBaseMessage(context);
                    message.customBehavior = this.getParam("customBehavior")
                    //console.error("about to post " + message.customBehavior + " from the main window")
                    window.tourWindow.postMessage(message, window.origin);
                }
            }
        }.bind(mod);
    })

    for (const cb of [
            "tour_tabularCallResultsMenuOpened",
            "tour_contextualFieldDocsOpened",
            "tour_chartResultsMenuOpened",
            "tour_tabularResultsMenuOpened",

            "tour_callDetailPage",
            "tour_sitesPage",
            "tour_outsidePartiesPage",
            "tour_huntgroupsPage",
            "tour_groupsPage",
            "tour_gatewaysPage",
            "tour_extensionsPage",
            "tour_devicesPage",
            "tour_concurrencyPage"
        ]) {

        //console.error("attaching custom behavior for " + cb)

        Sideview.declareCustomBehavior(cb, function(mod) {

            let onContextChangeReference = mod.onContextChange.bind(mod)
            mod.onContextChange = function(context) {
                onContextChangeReference(context);
                let customBehavior = this.getParam("customBehavior");

                // the suchAndSuchPage ones just need to fire. the only onContextChange that will ever fire is while the page is loading.
                if (customBehavior.indexOf("Page")==-1 && customBehavior!="tour_chartShowing" && !this.isPageLoadComplete()) return;

                if (window.tourWindow) {

                    let message = getBaseMessage(context);
                    if (this.getParam("customBehavior")=="tour_tabularCallResultsMenuOpened") {
                        let tableName = context.get("click.selectedTableName");
                        message.relevantField = context.get(sprintf("%s.cell.field", tableName));
                        message.relevantValue = context.get(sprintf("%s.cell.value", tableName));

                    }
                    message.customBehavior = this.getParam("customBehavior")
                    console.error("about to post " + message.customBehavior + " from the main window")
                    window.tourWindow.postMessage(message, window.origin);
                }
            }.bind(mod);

        })
    }



    Sideview.declareCustomBehavior("createPhoneNumberTermsForTeams", function(custom) {
        let getSearchTermsForTeamsNumbers = function(context) {
            let numbers = extractor.getNumbers(context, "number");
            let numberType = context.get("numberType");
            let terms = [];
            for (let i=0,len=numbers.length;i<len;i++) {
                if (numbers[i].length==0) continue;
                if (numberType=="all" || numberType=="from") {
                    terms.push('from="' + numbers[i] + '"');
                }
                if (numberType=="all" || numberType=="to") {
                    terms.push('to="' + numbers[i] + '"');
                }
            }
            return terms;
        }
        custom.getModifiedContext = function(context) {
            let terms = getSearchTermsForTeamsNumbers(context);
            if (terms.length>0) {
                context.set("numberTerms", "( " + terms.join(" OR ") + " )");
            }
            return context;
        }
    });



    Sideview.declareCustomBehavior("createPhoneNumberTermsForCube", function(custom) {
        let getSearchTermsForCubeNumbers = function(context) {
            let numbers = extractor.getNumbers(context, "number");
            let numberType = context.get("numberType");
            let terms = [];
            for (let i=0,len=numbers.length;i<len;i++) {
                if (numbers[i].length==0) continue;
                if (numberType=="all" || numberType=="callingParty") {
                    terms.push('clid="' + numbers[i] + '"');
                }
                if (numberType=="all" || numberType=="calledParty") {
                    terms.push('dnis="' + numbers[i] + '"');
                }
            }
            return terms;
        }

        custom.getModifiedContext = function(context) {
            let terms = getSearchTermsForCubeNumbers(context);
            if (terms.length>0) {
                context.set("numberTerms", "( " + terms.join(" OR ") + " )");
            }
            return context;
        }
    });

    // type=incoming     number=8885552002
    // can't put both of those in the subsearch because on a multileg call, the leg(s) with that number might not have that type.
    // we're back to the subsearch ONLY having the number in it....
    // SEE UNIT_TESTS.js
    Sideview.declareCustomBehavior("buildMainReportingTokens", function(customBehaviorModule) {

        Sideview.testRunnerModule = customBehaviorModule;

        customBehaviorModule.getModifiedContext = function(context) {
            context = context || this.getContext();
            let searchTerms = context.get("searchterms.rawValue");
            let stFieldDict = extractor.getFieldsFromExpression("search " + searchTerms);

            if ($.isNumeric(searchTerms)) {
                let message = _("warning - the search filters field does not support having raw extensions entered. try a field=value term.");
                Sideview.broadcastMessage("error",message);
                throw message;
            }


            let advancedSPL = context.get("advancedSearchLanguage.rawValue");
            let advancedFieldDict = extractor.getFieldsFromExpression("| " + advancedSPL);
            let fieldPickerFields = [];

            let displayingCalls = this.getParam("arg.displayingCalls")=="True";

            if (displayingCalls) {
                fieldPickerFields = context.get("results.fields") || [];
                extractor.checkForDeprecatedFields(context,fieldPickerFields);
            }

            let requiredFields = extractor.getRequiredFields(context, stFieldDict, fieldPickerFields, advancedFieldDict, displayingCalls);
            let requiredExtractions = extractor.getRequiredExtractions(requiredFields, context, stFieldDict, fieldPickerFields, displayingCalls);
            context.set("baseEventsSearch", extractor.getBaseEventsSearch(requiredFields,context,displayingCalls).join(" ") + "\n");
            context.set("requiredExtractions", requiredExtractions);
            let statsCommand = extractor.getStatsCommand(requiredFields, context, displayingCalls);
            context.set("statsCommand", statsCommand);
            context.set("postStatsTransform", extractor.getPostStatsTransform(requiredFields, context, fieldPickerFields, displayingCalls ));




            if (Sideview.compareVersions(Sideview.getConfigValue("SPLUNK_VERSION"), "8.3") >= 0) {
                context.set("disableSearchOptimization", '\n| noop search_optimization="false"');
            }
            // this is..... confusing but as written it's necessary.
            if (requiredFields.indexOf("durationStr")!=-1) {
                requiredFields.splice(requiredFields.indexOf("durationStr"), 1);

            }
            requiredFields.push("durationInSeconds")
            context.set("fields", requiredFields.join(" "));

            let postStatsSearch = extractor.getPostStatsSearch(requiredFields, context, stFieldDict, displayingCalls);
            // This means, if the following little modification is not here, then we would pipe a search
            // clause to another search clause.  then since we ship with | noop search_optimization="false"
            // it... actualy wont combine them.  So we would incur a really :facepalm: level of performance
            // degradation especially when user is filtering to one or more extensions, just for
            // "dc(callid) over nothing"
            if (!requiredExtractions && !advancedSPL && !statsCommand) {
                postStatsSearch = postStatsSearch.replace(/^\| search /,"")
            }
            context.set("postStatsSearch",postStatsSearch);

            return context;
        }
    });

    Sideview.declareCustomBehavior("createPhoneNumberSearchTerms", function(custom) {
        custom.getModifiedContext = function(context) {
            let numbers    = extractor.getNumbers(context,"number");
            let huntPilots = extractor.getNumbers(context,"huntPilotDN");
            let numberType = context.get("numberType") || "all";
            if (numbers.length>0) {
                let internalPartyNumberTerms = [];
                let externalPartyNumberTerms = [];
                let genericNumberTerms = [];
                for (let i=0;i<numbers.length; i++) {
                    let n = numbers[i];
                    if (!n) continue;

                    let outgoing_and_internal = '(%s="%s" (type="outgoing" OR type="internal"))';
                    let incoming_and_internal = '(%s="%s" (type="incoming" OR type="internal"))';
                    let incoming_and_tandem   = '(%s="%s" (type="incoming" OR type="tandem"))';
                    let outgoing_and_tandem   = '(%s="%s" (type="outgoing" OR type="tandem"))';

                    extractor.NUMBER_TERMS_ORIG.forEach(function(term) {
                        let value = sprintf(outgoing_and_internal, term, n);
                        internalPartyNumberTerms.push(value);
                        value = sprintf(incoming_and_tandem, term, n);
                        externalPartyNumberTerms.push(value);
                    });
                    extractor.NUMBER_TERMS_DEST.forEach(function(term) {
                        let value = sprintf(incoming_and_internal, term, n);
                        internalPartyNumberTerms.push(value);
                        value = sprintf(outgoing_and_tandem, term, n);
                        externalPartyNumberTerms.push(value);
                    });

                    genericNumberTerms.push('number="' + n + '"');
                }
                context.set("internalPartyNumberTerms", internalPartyNumberTerms.join(" OR "));
                context.set("externalPartyNumberTerms", externalPartyNumberTerms.join(" OR "));
                context.set("genericNumberTerms",genericNumberTerms.join(" OR "));
                let terms = extractor.getSearchTermsForNumbers(numbers, numberType);
                context.set("numberTerms", terms.join(" OR "));
            }
            if (huntPilots.length>0) {
                let huntPilotTerms = [];
                for (let j=0;j<huntPilots.length; j++) {
                    huntPilotTerms.push('huntPilotDN="' + huntPilots[j] + '"');
                }
                // used in both investigate extensions and investigate groups
                context.set("huntPilotSubsearch", "[ search `custom_index` sourcetype=cucm_cdr ( " + huntPilotTerms.join(" OR ") + " ) | stats count by " + extractor.ID_FIELDS.join(" ") + " | fields - count ]");

                // this is currently used only in extension_detail
                context.set("huntPilotNumberTerms", huntPilotTerms.join(" OR "));
            }
            return context;
        }
    });
});
