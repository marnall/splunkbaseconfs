// Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
define(
    ["jquery",
    "sideview",
    "api/splunk/SplunkSearch"
    ],
    function($, Sideview, SplunkSearch) {


Sideview.utils.declareCustomBehavior("receivePushesForRowUpdates", function(searchModule) {
    if (window.__rowUpdater) {
        console.error("receivePushesForRowUpdates - hees already got one");
    }
    searchModule.enabled = false;
    // normally it would be sketchy to clobber the base implementation, and we'd have to get a method
    // reference to the base method and then call it in here. However here we know that these
    // Search modules dont do any async loading and... they're not dependent on any other upstream
    // dispatch so....  we're just doing the simple dumb thing here.
    searchModule.isReadyForContextPush = function() {
        return this.enabled;
    }.bind(searchModule)
    window.__rowUpdater = searchModule;
});


Sideview.utils.declareCustomBehavior("receivePushesForRowDeletes", function(searchModule) {
    if (window.__rowDeleter) {
        console.error("receivePushesForRowDeletes - hees already got one");
    }
    searchModule.enabled = false;
    // see comment on "receivePushesForRowUpdates" above.
    searchModule.isReadyForContextPush = function() {
        return this.enabled;
    }.bind(searchModule)
    window.__rowDeleter = searchModule;
});


Sideview.utils.declareCustomBehavior("reloader", function(module) {

    if (window.__reloader) {
        console.error("hookForReloadingLookup - hees already got one");
    }
    window.__reloader = module;

    module.onContextChange = function(context) {
        context = context || this.getContext();
        var form = document.forms["lookupUpdater"];

        if (form) {
            $(form.lookupName).val(context.get("lookupName.rawValue"));

            // these are just so we know what app and view we're at,  to
            // redirect back to the right one after.
            // obviously it'll be sideview_utils/update_lookup often, but
            // not for OEM's.
            //$(form.currentApp).val(Sideview.utils.getCurrentApp());
            //$(form.app).val(context.get("app.rawValue"));
            $(form.currentView).val(Sideview.utils.getCurrentView());

            form.setAttribute("action", "../../cisco_cdr_replace_lookup");

            var getSplunkFormKey = function() {
                var legacy_key_value = Sideview.utils.getConfigValue("MRSPARKLE_PORT_NUMBER", false);
                var current_key_value = Sideview.utils.getConfigValue("SPLUNKWEB_PORT_NUMBER", false);
                var port = current_key_value || legacy_key_value || document.location.port;
                var name = "splunkweb_csrf_token_" + port;
                return $.cookie(name ) || "";
            }

            $(form.splunk_form_key).val(getSplunkFormKey())

            // the restmap.conf handler returns json so we just ajaxPost
            // the form here.
            $(form).submit(function(evt) {
                evt.preventDefault();
                Sideview.broadcastMessage("info","Uploading...");

                var formData = new FormData(this);

                $.ajaxSetup({
                    headers: { "X-Splunk-Form-Key": getSplunkFormKey() }
                });

                $.ajax({
                    url: this.getAttribute("action"),
                    type: 'POST',
                    headers: {
                        "X-Splunk-Form-Key": getSplunkFormKey()
                    },
                    traditional: true,
                    data: formData,
                    success: function (resp) {
                        if (resp.success) {
                            console.info(resp.messages);
                            console.info(resp.messages.length);
                            var message = "successfully uploaded"
                            if (resp.messages.length>0) {
                                message = resp.messages[0].text;
                            }

                            Sideview.broadcastMessage("info", message);
                            setTimeout(Sideview.clearMessages, 8000)
                        }
                    },
                    error: function(jqXHR, textStatus, errorThrown){
                        var response =  JSON.parse(jqXHR.responseText);
                        var message = response["messages"][0]["text"]
                        Sideview.broadcastMessage("error", message);
                    },
                    processData: false,
                    contentType: false
                });
                return false;
            });

        }
    }
});


Sideview.utils.declareCustomBehavior("changeResultsOffset", function(module) {
    module.getModifiedContext = function(context) {
        context = context || this.getContext();
        if (window.__pageOffset) {
            context.set("results.offset",window.__pageOffset);
        }
        return context;
    }
});


Sideview.utils.declareCustomBehavior("reloadEditedLookup", function(customBehaviorModule) {
    customBehaviorModule.onContextChange = function(context) {
        if ($("#messageBar .error").length>0) {
            console.error("DONT CLEAR - we have an error!!")
        } else {
            window.__reloader.pushContextToChildren();
        }
    }
});


Sideview.utils.declareCustomBehavior("addNewRow", function(customBehaviorModule) {
    customBehaviorModule.getModifiedContext = function(context) {
        context = context || this.getContext();

        var values = {};
        $("div.addNewRow input").each(function() {
            var key = $(this).attr("name");
            values[key] = $(this).val();
        });
        var lookupName = context.get("lookupName.rawValue");
        var s = [];
        s.push("| inputlookup " + lookupName);
        s.push("| append [ | stats count | fields - count")
        for (let key in values) {
            if (Object.hasOwn(values, key) && values[key]!="") {
                s.push('| eval ' + key + '="' + Sideview.escapeForSearchLanguage(values[key]) + '"');
            }
        }
        s.push("]");
        // We have to sneak this in because the Sites lookup has max_matches=1, and the
        // smallest networks have to get their chance to match before the larger catchall
        // networks which come further down in the file.
        if (lookupName=="cidr") {
            s.push("| eval network_bits=mvindex(split(subnet,\"/\"),1) | sort 0 - network_bits | fields site_name subnet subnet_description country lat long");
        }
        s.push("| outputlookup " + lookupName + " create_empty=false override_if_empty=false");
        var search = new SplunkSearch(s.join(""));
        context.set("search",search);

        return context;
    };
});


Sideview.utils.declareCustomBehavior("confirmNewRowAdded", function(cbModule) {
    cbModule.onJobDone = function() {
        Sideview.utils.broadcastMessage("info", "Your new row was successfully added to the lookup.");
        setTimeout(Sideview.clearMessages, 8000)
    }
});


Sideview.utils.declareCustomBehavior("neverReload", function(htmlModule) {
    htmlModule.onContextChange = function(){}
});


Sideview.utils.declareCustomBehavior("editableTable", function(tableModule) {
    tableModule.hasUncommittedChanges = function(row) {
        var retVal=false;
        row.find("input").each(function() {
            var oldValue = $(this).attr("s:oldValue") || "";
            if (oldValue != $(this).val()) {
                retVal=true;
                return false
            }
        });
        return retVal;
    }
    tableModule.renderDataCell = function(tr, field, value) {
        var tableModule = this;
        var td = $("<td>");
        var primaryButtonClass="";
        var secondaryButtonClass="buttonSecondary";

        var input = $("<input>")
            .attr("s:field",field)
            .keyup(function(e) {
                var me = $(this);
                var row = $(me.parents("tr")[0]);
                var button = $(me.parents("tr")[0]).find("button.update");

                if (tableModule.hasUncommittedChanges(row)) {
                    button.removeClass(secondaryButtonClass);
                    button.addClass(primaryButtonClass);
                }
                else {
                    button.removeClass(primaryButtonClass);
                    button.addClass(secondaryButtonClass);
                }
                var code = e.which;
                if(code==13) {
                    Sideview.clearMessages();
                    button.click();
                }
                // warn people if they try and type a comma plus the port.
                if (field=="axlHost" && code==16) {
                    Sideview.broadcastMessage("error", "the axlHost field should only get the IP or FQDN as entered into the AXL app's connection config. Do not enter the port or the colon character.");
                    return false;
                }
            });

        if (value) {
            input.val(value).attr("s:oldValue",value);
        }
        td.append(input);
        tr.append(td);
        return td;
    }

    /**
     * magic part where we sneak in the label from the props stanza.
     TODO - the sorting clicks on the custom field column labels wont... sort right.
            will anyone care?  probably...
     */
    let renderColumnRow_methodReference = tableModule.renderColumnRow.bind(tableModule);
    tableModule.renderColumnRow = function(tr) {
        let context = this.getContext();
        let lookup_fields = context.get("lookup_fields");
        let output_fields = context.get("output_fields");

        if (!lookup_fields || !output_fields) {
            // so very carefully we dissappear into the shrubbery.
            return renderColumnRow_methodReference(tr);
        }
        lookup_fields = lookup_fields.split(" ");
        output_fields = output_fields.split(" ");

        let prettifier = {}
        for (let i=0;i<lookup_fields.length; i++) {
           prettifier[lookup_fields[i]] = output_fields[i];
        }

        tr.addClass("columnRow");

        for (let i=0,len=this.fieldOrder.length;i<len;i++) {
            let fieldName = this.fieldOrder[i];
            let fieldLabel = fieldName;
            if (fieldName in prettifier){
                fieldLabel = prettifier[fieldName];
            }
            if (!Object.hasOwn(this.hiddenFields, fieldName)) {
                let th = $("<th>");
                th.append($("<span>").addClass("sortLabel").text(fieldLabel));
                if (this.allowSorting) {
                    th.addClass("sortable");
                    th.click(this.onSortClick.bind(this))
                    if (fieldName == this.activeSortField) {
                        th.addClass("activeSort");
                        if (!this.activeSortIsAscending) {
                            th.addClass("descending");
                        }
                    }
                    th.append($("<span>").addClass("sortArrow"));
                }

                tr.append(th);
            }
        }
    }


    tableModule.getBaseMatchingSearch = function(lookupName,oldValueDict) {
        var s = [];
        s.push("| inputlookup " + lookupName);
        s.push("| eval zomgItsOurRow=if(");
        var condi = [];
        for (let key in oldValueDict) {
            if (Object.hasOwn(oldValueDict, key)) {
                if (!oldValueDict[key] ) {
                    condi.push("(" + key + '=="' + Sideview.escapeForSearchLanguage(oldValueDict[key]) + '" OR isnull(' + key + '))');
                }
                // splunk has irritating habit of returning time with subseconds even if _subseconds is null.
                else if (key=="_time") {
                    condi.push(key + '==round(tonumber("' + oldValueDict[key] + '"))');
                } else {
                    condi.push(key + '=="' + Sideview.escapeForSearchLanguage(oldValueDict[key]) + '"');
                }
            }
        }
        s.push(condi.join(" AND "));
        s.push(',"1","0")');
        // now the problem is,  that if you have dupes on page 3 and page 5,
        // and the user edits the page 5 dupe, the page 3 record is updated.
        // we can potentially pass row number and use that as an additional criterion
        // for the base match?
        s.push('| streamstats count(eval(zomgItsOurRow==1)) as zomgHaveWeMatchedYet');
        s.push('| eval zomgItsOurRow=if(zomgHaveWeMatchedYet<2,zomgItsOurRow,0)');
        s.push('| fields - zomgHaveWeMatchedYet');
        return s;
    }

    /**
     * uses these 2 dicts to create a big search string that does
     * | inputlookup
     * | eval zomgItsOurRow=if (every old value is the same)
     * | eval field1=if(zomgItsOurRow,newField1,field1)
     * | eval field2=if(zomgItsOurRow,newField1,field1)
     *   ...
     * | fields - zomgItsOurRow
     * | outputlookup
     */
    tableModule.getRowUpdateSearch = function(lookupName, oldValueDict, newValueDict) {
        var s = this.getBaseMatchingSearch(lookupName, oldValueDict);

        var evalStatements = []
        for (let key in newValueDict) {
            if (Object.hasOwn(newValueDict, key)) {
                let value = newValueDict[key];
                value = value==""? "null()" : "\"" + Sideview.escapeForSearchLanguage(newValueDict[key]) + "\"";
                evalStatements.push('eval ' + key + '=if(zomgItsOurRow=="1",' + value + ',' + key + ')')
            }
        }
        s.push(" | " + evalStatements.join(" | "));
        s.push(" | fields - zomgItsOurRow");
        s.push(" | outputlookup " + lookupName + " create_empty=false override_if_empty=false");
        return s.join("");
    }

    tableModule.getRowDeleteSearch = function(lookupName,oldValueDict) {
        var s = this.getBaseMatchingSearch(lookupName, oldValueDict);
        s.push("| search NOT zomgItsOurRow=1");
        s.push(" | fields - zomgItsOurRow ");
        s.push(" | outputlookup " + lookupName + " create_empty=false override_if_empty=false");
        return s.join("");
    }
    tableModule.getHiddenFields = function() {
        return {};
    }

    tableModule.onEditClick = function(evt) {
        let button = $(evt.target);
        let oldValueDict = {};
        let newValueDict = {};
        $(button.parents("tr")[0]).find("input").each(function() {
            let field = $(this).attr("s:field");
            let newValue = $(this).val();
            let oldValue = $(this).attr("s:oldValue") || "";

            newValueDict[field] = newValue;
            oldValueDict[field] = oldValue;
        });
        let context = this.getContext();
        let lookupName = context.get("lookupName.rawValue");

        if (lookupName == "call_quality_thresholds") {
            let allowed_quality_names = ["good", "acceptable", "fair", "poor"];
            if (allowed_quality_names.indexOf(newValueDict["quality"]) == -1) {
                let oxfordCommaMsg = "Sorry but the only quality values allowed are ";
                oxfordCommaMsg += allowed_quality_names.slice(0,-1).join(",") + ", and ";
                oxfordCommaMsg += allowed_quality_names[allowed_quality_names.length-1] + ".";
                Sideview.broadcastMessage("error", oxfordCommaMsg);
                return;
            }
        }
        let s = this.getRowUpdateSearch(lookupName,oldValueDict, newValueDict);


        window.__pageOffset = context.get("results.offset");
        // we can unlock it now.  It was locked so it wouldn't dispatch the placeholder SPL on startup
        window.__rowUpdater.enabled = true;
        window.__rowUpdater._params["search"] = s.replace(/\$/g, "$$$");
        window.__rowUpdater.pushContextToChildren();
    }

    tableModule.onDeleteClick = function(evt) {
        let button = $(evt.target);
        let oldValueDict = {};

        $(button.parents("tr")[0]).find("input").each(function() {
            let field = $(this).attr("s:field");
            let oldValue = $(this).attr("s:oldValue") || "";
            oldValueDict[field] = oldValue;
        });
        let context = this.getContext();
        let lookupName = context.get("lookupName.rawValue");
        let s = this.getRowDeleteSearch(lookupName,oldValueDict);

        window.__pageOffset = context.get("results.offset");
        // we can unlock it now.  It was locked so it wouldn't dispatch the placeholder SPL on startup
        window.__rowDeleter.enabled = true;
        window.__rowDeleter._params["search"] = s.replace(/\$/g, "$$$");
        window.__rowDeleter.pushContextToChildren();
    }

    let renderRowMethodReference = tableModule.renderRow.bind(tableModule);
    tableModule.renderRow = function(table, rowIndex, row, context) {
        let tr = renderRowMethodReference(table, rowIndex, row, context);

        let editButton = $("<button>")
            .addClass("svButton")
            .addClass("update")
            .text("Update")
            .click(this.onEditClick.bind(this));


        let deleteButton = $("<button>")
            .addClass("svButton")
            .addClass("delete")
            .text("Delete");

        if (context.getSplunkSearch().getResultCount()>1) {
            deleteButton
                .click(this.onDeleteClick.bind(this));
        } else {
            deleteButton
                .addClass("disabled")
                .css("opacity","0.65")
        }

        editButton.addClass("buttonSecondary");
        deleteButton.addClass("buttonSecondary");

        let buttonCell = $("<td>")
            .append(editButton)
            .append(deleteButton);

        tr.append(buttonCell);
        return tr;
    }

    let onContextChangeMethodReference = tableModule.onContextChange.bind(tableModule);
    tableModule.onContextChange = function(context) {
        context = context || this.getContext();
        window.__pageOffset = null;
        return onContextChangeMethodReference(context);
    }
    tableModule.getTimeFormatPostProcess = function() {return false;}
});


Sideview.utils.declareCustomBehavior("addNewFilterToFilterBar", function(module) {
    module.onContextChange = function(context) {
        context = context || this.getContext();
        var callback = context.get("filters.addNewFilter");
        var field = context.get("field");
        var operator = context.get("operator");
        var value = context.get("value");
        callback(field,value,operator);
    }
});


Sideview.utils.declareCustomBehavior("hideDownstreamModulesUntilFieldSelected", function(pulldown) {
    let visibilityId = "userHasntPickedAFieldYet";
    let methodReference = pulldown.pushDownstream.bind(pulldown);
    pulldown.markPageLoadComplete();

    pulldown.pushDownstream = function(explicitContext) {
        let active = this.select.val().length>0;
        let retVal = [];
        this.withEachDescendant(function(module) {
            if (active) {
                module.show(visibilityId);
            }
            else {
                module.hide(visibilityId);
            }
        }.bind(this))

        if (active) {
            retVal = methodReference(explicitContext);
        }
        return retVal;
    }.bind(pulldown);
});


Sideview.utils.declareCustomBehavior("activeOnlyIfManualEntrySelected", function(module) {
    var onContextChangeReference = module.onContextChange.bind(module);
    module.onContextChange = function(context) {
        context = context || this.getContext();
        var retVal = onContextChangeReference(context);

        if (context.get("value")) {
            this.active=false;
            this.hide();
        }
        else {
            this.active=true;
            this.show();
        }
        return retVal;
    }
    var getModifiedContextReference = module.getModifiedContext.bind(module);
    module.getModifiedContext = function(context) {
        if (this.active) {
            return getModifiedContextReference(context);
        } else {
            return context || this.getContext();
        }
    }
});


});