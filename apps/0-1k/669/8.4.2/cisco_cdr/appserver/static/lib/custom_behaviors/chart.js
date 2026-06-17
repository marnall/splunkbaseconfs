// Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
/* global localAppStaticUrlPrefix */
define(
    ["jquery",
    "sideview",
    localAppStaticUrlPrefix + "lib/extractor.js",
    ],
    function($, Sideview, extractor) {


/**
 * just centralizing this, so it can be backwards compatible to the old chart view,
 * which we may just keep shipping for a while
 */
let getSelectedChartDisplay = function(context) {
    let st = context.get("displayChartAs") || context.get("selectedTab") || "";
    return st.toLowerCase();
};

Sideview.declareCustomBehavior("customReportLabel", function(htmlModule) {
    htmlModule.isDynamic = true;
    htmlModule.resetUI = function() {
        //this.container.html("");
    };

    // tedious, but we have to hardwire this, because the job token is not
    // in the HTML.
    htmlModule.onJobDone = function() {
        this.getResults();
        this.renderHTML(this.getContext());
    };

    htmlModule.renderHTML = function(context) {
        this.container.html("");

        Sideview.setStandardTimeRangeKeys(context);
        Sideview.setStandardJobKeys(context);

        const stat = context.get("stat");
        const statLabel = context.get("stat.label");
        const yField = context.get("yField");
        const yFieldLabel = context.get("yField.label");
        const xField = context.get("xField");
        const zField = context.get("zField");

        const xFieldLabel = xField ? "over " + context.get("xField.label"): "";


        const timeRangeLabel = context.get("search.timeRange.label");
        const resultsCount = context.get("results.count");

        let zFieldLabel = zField ? "split by " + zField : "";
        let html = "";

        // one giant special case for the "top values of $xField$" case
        if (xField!="_time" && stat=="dc" && yField == "call_id" && xField) {
            zFieldLabel = (zFieldLabel) ? "(" + zFieldLabel + ")" : "";
            let singularOrPlural = (resultsCount==1) ? "value" : "values";
            html = sprintf("%s %s of %s seen in matching calls %s %s", resultsCount, singularOrPlural, xField, timeRangeLabel, zFieldLabel);
        }
        else {
            let yFieldExpression = statLabel + " " + yFieldLabel;
            if (stat == "dc") {
                if (yField == "call_id") {
                    yFieldExpression = "calls";
                }
                else {
                    yFieldExpression = sprintf("distinct values of %s seen", yField);
                }
            }
            else if (stat == "sum") {
                yFieldExpression = sprintf("total %s", yFieldLabel);
            }
            else if (["perc95", "perc5"].includes(stat)) {
                yFieldExpression = sprintf("%s of %s", statLabel, yFieldLabel);
            }
            context.set("yFieldExpression", yFieldExpression);
            html = [yFieldExpression, xFieldLabel, zFieldLabel, timeRangeLabel].join(" ");
        }
        this.container.append($("<h2>").html(html));
        this.onHTMLRendered();
    };
})


Sideview.declareCustomBehavior("xFieldPulldown", function(pulldownModule) {

    pulldownModule.enableAppropriateOptions = function() {
        var context = this.getContext();
        //var stat = context.get("stat");
        var yField = context.get("yField");
        var opt, field;
        $("option",this.container).each(function() {
            opt = $(this);
            field = opt.attr("value");
            if (yField=="concurrency") {
                if (["_time", "hour_of_day"].includes(field)) {
                    opt.removeAttr("disabled");
                } else {
                    opt.attr("disabled","disabled");
                }
            }
            else {
                opt.removeAttr("disabled");
            }
        });
    }
    var OCC_methodReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        // if it's set to anything but time or hour_of_day, we need to reset it.
        if (context.get("yField") == "concurrency" && context.get("xField") && ["_time", "hour_of_day"].includes(context.get("xField"))) {
            context.set("xField", "_time");
        }
        // this goes and disables all the options except time.
        // although notably, disabling an option does NOT deselect it. o_O
        this.enableAppropriateOptions();
        return OCC_methodReference(context);
    }

    pulldownModule.onRendered= function() {
        this.enableAppropriateOptions();
    }

    var GMC_methodReference = pulldownModule.getModifiedContext.bind(pulldownModule);
    pulldownModule.getModifiedContext = function(context) {
        context = GMC_methodReference(context);
        // the "over nothing" option isn't compatible with the Chart module.
        if (this.select.val()=="") {
            context.set("selectedTab", "Table")
            context.set("displayChartAs", "Table")
        }
        return context;
    }
});


Sideview.declareCustomBehavior("yFieldPulldown", function(pulldownModule) {
    pulldownModule.enableAppropriateOptions = function() {
        let context = this.getContext();
        let stat = context.get("stat");

        let currentType = (stat=="dc")? "categorical":"numeric";
        $("option",this.container).each(function() {
            let opt = $(this);
            let field = opt.attr("value");
            if (extractor.fieldExists(field)) {
                let value = extractor.fieldDict[field][currentType];
                if (field=="concurrency") {
                    if (stat=="max") {
                        opt.removeAttr("disabled");
                    } else {
                        opt.attr("disabled","disabled");
                    }
                }
                else if (value) {
                    opt.removeAttr("disabled");
                } else {
                    opt.attr("disabled","disabled");
                }
            }
        });
        var currentValue = this.select.val();
        if (!currentValue && currentType=="numeric") {
            this.select[0].selectedIndex=1;
        } else if (!currentValue && currentType=="categorical") {
            this.select[0].selectedIndex=0;
        }
    }
    var OCC_methodReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        this.enableAppropriateOptions();
        return OCC_methodReference(context);
    }

    pulldownModule.onRendered= function() {
        this.enableAppropriateOptions();
    }
});


Sideview.declareCustomBehavior("concurrencyPatch", function(reportModule) {
    var GMC_methodReference = reportModule.getModifiedContext.bind(reportModule);
    reportModule.getModifiedContext= function(context) {
        context = GMC_methodReference(context);
        var xField = context.get("xField");
        var yField = context.get("yField");

        if (yField!="concurrency") {
            return context;
        }
        else {
            var zField = Sideview.replaceTokensFromContext(this.getParam("zField"), context);

            if (xField=="_time") {
                var commands = [];
                var xFieldBins = context.get("xFieldBins");
                if (zField) {
                    commands.push("`timechart_for_concurrency(" + zField + ", " + xFieldBins + ")`");
                }
                else {
                    commands.push("`timechart_for_concurrency_with_bins(" + xFieldBins + ")`");
                }
                context.set(this.getParam("name"), commands.join(" | "));
                //context.set("statsCommand", "");
            }
        }
        return context;
    }
});


Sideview.declareCustomBehavior("xFieldBinsPulldown", function(pulldown) {
    var onContextChangeReference = pulldown.onContextChange.bind(pulldown);
    pulldown.onContextChange = function(context) {
        context = context || this.getContext();
        var xField = context.get("xField");

        var xFieldInvisibility = "when x axis is categorical there is no x axis binning."
        var unknownFieldInvisibility = "if we've never seen the field then there's no binning"

        let retVal = onContextChangeReference(context);
        if (Object.hasOwn(extractor.fieldDict, xField)) {
            this.show(unknownFieldInvisibility);
            if (extractor.fieldDict[xField]["numeric"]) {
                if (this.select.val()=="") {
                    this.setSelection("15");
                }
                this.show(xFieldInvisibility);
            }
            else if (extractor.fieldDict[xField]["time"]) {
                if (this.select.val()=="") {
                    this.setSelection("100");
                }
                this.show(xFieldInvisibility);
            }
            else {
                this.setSelection("");
                this.hide(xFieldInvisibility);
            }
        } else {
            this.setSelection("");
            this.hide(unknownFieldInvisibility);
        }
        return retVal;
    }
});


Sideview.declareCustomBehavior("zFieldPulldown", function(pulldown) {
    var onContextChangeReference = pulldown.onContextChange.bind(pulldown);
    pulldown.onContextChange = function(context) {
        context = context || this.getContext();
        var currentValue = this.select.val();

        if (context.get("xField.rawValue") == currentValue) {
            context.set(this.getParam("name"),null)
            this.setSelection("")
        }
        this.enableAppropriateOptions();
        return onContextChangeReference(context);
    }

    pulldown.enableAppropriateOptions = function() {
        var context = this.getContext();
        var yField = context.get("yField.rawValue");
        var opt, field;
        $("option",this.container).each(function() {
            opt = $(this);
            field = opt.attr("value");
            if (yField=="concurrency") {
                if (Object.hasOwn(extractor.SPECIAL_CASED_STATS_FIELDS, field) || extractor.CMR_FIELDS.includes(field)) {
                    opt.attr("disabled","disabled");
                }
                else {
                    opt.removeAttr("disabled");
                }
            }
            else {
                opt.removeAttr("disabled");
            }
        });
    }
    pulldown.onRendered= function() {
        this.enableAppropriateOptions();
    }
});


Sideview.declareCustomBehavior("zFieldBinsPulldown", function(pulldown) {
    var onContextChangeReference = pulldown.onContextChange.bind(pulldown);
    pulldown.onContextChange = function(context) {
        context = context || this.getContext();

        var zField = context.get("zField");

        var zFieldInvisibility = "when z axis is categorical there is no z axis binning."
        var unknownFieldInvisibility = "if we've never seen the field then there's no binning"
        if (Object.hasOwn(extractor.fieldDict, zField)) {
            this.show(unknownFieldInvisibility);
            if (extractor.fieldDict[zField]["numeric"]) {
                if (this.select.val()=="") {
                    this.setSelection("15");
                }
                this.show(zFieldInvisibility);
            } else {
                this.setSelection("");
                this.hide(zFieldInvisibility);
            }
        } else {
            this.setSelection("");
            this.hide(unknownFieldInvisibility);
        }
        return onContextChangeReference(context);
    }
});


Sideview.declareCustomBehavior("sortByPulldown", function(pulldown) {
    let isCompatibleWithSortBy = function(context) {
        let xField = context.get("xField");

        if (["day_of_week", "date_wday", "month_of_year"].includes(xField)) {
            return false;
        }
        return ((context.get("zField")=="") && (context.get("xFieldBins")=="") && (xField!="_time") && (xField!=""));
    }

    var onContextChangeReference = pulldown.onContextChange.bind(pulldown);
    pulldown.onContextChange = function(context) {
        context = context || this.getContext();
        let yFieldInvisibilityMode = "when there's any split-by, or x=time, or x is binned, there is no sortby.";
        if (isCompatibleWithSortBy(context)) {
            this.show(yFieldInvisibilityMode);
        } else {
            this.hide(yFieldInvisibilityMode);
        }
        //let xField = context.get("xField");

        return onContextChangeReference(context);
    }

    let getModifiedContextReference = pulldown.getModifiedContext.bind(pulldown);
    pulldown.getModifiedContext = function(context) {
        context = context || this.getContext();
        if (isCompatibleWithSortBy(context)) {
            return getModifiedContextReference(context);
        } else {
            context.set(this.name, "");
            return context;
        }
    }
});



Sideview.declareCustomBehavior("chartTypePulldown", function(pulldownModule) {
    var baseOnContextChangeReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        var retVal = baseOnContextChangeReference(context);

        var selectedTab = getSelectedChartDisplay(context);

        var visibilityReason = "only show if we're in the Chart tab";
        if (selectedTab == "chart") {
            this.show(visibilityReason);
        }
        else {
            this.hide(visibilityReason);
        }
        // it doesn't make sense to let them try "bar" charts with time axes.
        $("option",this.container).each(function() {
            var opt = $(this);
            var type = opt.attr("value");
            if (type == "bar" && context.get("xField") == "_time") {
                opt.attr("disabled","disabled");
            }
            else {
                opt.removeAttr("disabled");
            }
        });
        return retVal;
    }.bind(pulldownModule);

    let baseGetModifiedContextReference = pulldownModule.getModifiedContext.bind(pulldownModule);
    pulldownModule.getModifiedContext = function(context) {
        context = baseGetModifiedContextReference(context);

        let field = context.get("yField");
        let stat = context.get("stat");
        if (field == "call_id" && stat == "dc") {
            context.set("sideview.yFieldTitle", "calls");
        }
        return context;
    }


});


Sideview.declareCustomBehavior("stackModePulldown", function(pulldownModule) {
    var baseMethodReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        var retVal = baseMethodReference(context);
        var splitByField = context.get("sideview.splitByField");
        var selectedTab = getSelectedChartDisplay(context);
        var visibilityReason = "don't show in 'table' mode, and only for stackable charts";
        var stackable = ["area","column","bar"];
        if (selectedTab != "table" && splitByField && stackable.includes(context.get("charting.chart"))) {
            this.show(visibilityReason);
        }
        else {
            this.hide(visibilityReason);
            this.setSelection("stacked");
        }
        return retVal;
    }.bind(pulldownModule);
});


Sideview.declareCustomBehavior("nullValueModePulldown", function(pulldownModule) {
    var baseMethodReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        var retVal = baseMethodReference(context);
        var selectedTab = getSelectedChartDisplay(context);
        var hasPoints = ["line","area"];
        var visibilityReason = "only show in Chart tab, and for chart types that have points";

        if (selectedTab == "chart" && hasPoints.includes(context.get("charting.chart"))) {
            this.show(visibilityReason);
        }
        else {
            this.hide(visibilityReason);
        }
        return retVal;
    }.bind(pulldownModule);
});


Sideview.declareCustomBehavior("showMarkersPulldown", function(pulldownModule) {
    var baseMethodReference = pulldownModule.onContextChange.bind(pulldownModule);
    pulldownModule.onContextChange = function(context) {
        context = context || this.getContext();
        var retVal = baseMethodReference(context);

        var selectedTab = getSelectedChartDisplay(context);
        var hasPoints = ["line"];
        var visibilityReason = "only show in Chart tab, for chartType=line";

        if (selectedTab == "chart" && hasPoints.includes(context.get("charting.chart"))) {
            this.show(visibilityReason);
        }
        else {
            this.hide(visibilityReason);
        }
        return retVal;
    }.bind(pulldownModule);
});


Sideview.declareCustomBehavior("customLogicWhenZeroResultsAreFound", function(module) {
    var reason = "no downstream modules should be shown if there are no results for the fieldsummary search";

    module.resetCustomVisibility = function() {
        $(".graphArea").show();
        $(".mainSearchControls").show();
        $(".zeroResultsFoundNoFilters").hide();
        $(".zeroResultsFoundWithFilters").hide();
        this.showDescendants(reason);

    }
    module.reset = function() {
        this.resetCustomVisibility();
    }
    module.onJobDone = function() {
        var context = this.getContext();
        // avoid the deprecation warning.
        var search = context.getSplunkSearch();

        var filterStr = context.get("filterCalls");
        // We are hitching a ride on the Table module's CSS.
        $(".zeroResultsFoundNoFilters").parent().addClass("Table").removeClass("HTML");

        if (search.job.getResultCount()==0) {
            this.hideDescendants(reason);
            $(".graphArea").hide();
            $(".mainSearchControls").hide();
            if (filterStr) {
                $(".zeroResultsFoundNoFilters").hide();
                $(".zeroResultsFoundWithFilters").show();
            } else {
                $(".zeroResultsFoundWithFilters").hide();
                $(".zeroResultsFoundNoFilters").show();
            }
        }
        else {
            this.resetCustomVisibility();
        }
    };
});


});