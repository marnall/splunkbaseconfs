/**
 * check for Splunk version, if 6.0 or higher, do not display body in license usage views
 */

var splunkVersion = Splunk.util.getConfigValue("VERSION_LABEL");
var splunkMajorVersion = splunkVersion.split(".")[0];

if ((splunkMajorVersion >= 6 ) && (Splunk.util.getCurrentView() == "license_usage_today" || Splunk.util.getCurrentView() == "license_usage_30days")) {

    $("#bubbleslicenseredirect").show();
    $(".dashboardCell").hide();
    $(".Button").hide();
    $(".Pulldown").hide();
}


/**
 * check for presence of Sideview Utils and check the required version.
 */
(function () {
    var REQUIRED_VERSION = "1.1.7";
    function isAppLoaded() {
        var appList = false;
        try {appList = Splunk.Module.loadParams.AccountBar_0_0_0.appList;}
        catch(e) {}
        if (!appList) return -1;
        for (var i=0,len=appList.length;i<len;i++) {
            if (appList[i].id == "sideview_utils") return 1;
        }
        return 0;
    }
    function isModulePresent() {
        return ($("div.SideviewUtils").length>0);
    }
    var error = false;
    // only show the most pressing error at a time.
    if (isAppLoaded()==0)        error ="SideviewAppNotInstalled";
    else if (!isModulePresent()) error = "SideviewModuleNotPresent";
    else if (REQUIRED_VERSION && typeof(Sideview)!="undefined") {
        var currentVersion = false;

        if (Sideview.utils.hasOwnProperty("checkRequiredVersion")) {
            currentVersion = Sideview.utils.getCurrentVersion();
        }
        if (!currentVersion || !Sideview.utils.checkRequiredVersion(REQUIRED_VERSION)){
            currentVersion = currentVersion || "1.0.5.2 or older";
            $("#SideviewModuleVersionTooOld .currentVersion").text(currentVersion);
            $("#SideviewModuleVersionTooOld .requiredVersion").text(REQUIRED_VERSION);
            error = "SideviewModuleVersionTooOld";
        }
    }
    if (error && $("#" + error).length>0) {
        $("#" + error).show();
        // supply empty class definitions to stop the alerts from attacking.
        Splunk.Module.HTML = Splunk.Module.Pulldown = Splunk.Module.TextField =
            Splunk.Module.ValueSetter = Splunk.Module.SideviewUtils =
            Splunk.Module.ResultsValueSetter = Splunk.Module.Button =
            Splunk.Module.URLLoader = Splunk.Module.Redirector =
            Splunk.Module.Search = Splunk.Module.CustomBehavior =
            Splunk.Module.PostProcess = Splunk.Module.Pager =
            Splunk.Module.Checkbox =
            $.klass(Splunk.Module, {});
    }
})()




$(document).bind("allModulesInHierarchy", function() {

    if (typeof(Sideview)!="undefined" && Sideview.utils) {

        Sideview.utils.forEachModuleWithCustomBehavior("correlateSelectedFields", function(i,module) {
            module.getModifiedContext = function(context) {
                context = context || this.getContext();
                var selected = context.get("filename.rawValue");
                var matchingParam = this.getParam("arg." + selected);

                var newFieldList = (matchingParam)? matchingParam.split(" ") : [this.getParam("arg.defaultFieldList")];
                context.set("results.fields", newFieldList);
                return context;
            }
        });

        Sideview.utils.forEachModuleWithCustomBehavior("whenShownScrollUpIfOffscreen", function(i,module) {
            var baseMethod = module.onContextChange.bind(module);
            module.onContextChange = function() {
                baseMethod();
                var ours = this.container.offset().top;
                var windows = $(window).scrollTop();
                $(window).scrollTop(Math.min(windows, ours));
            }
        });

        Sideview.utils.forEachModuleWithCustomBehavior("adjustColumnWidths", function(i,module) {
            var leftPanel  = module.container.parent();
            var rightPanel = leftPanel.next();
            leftPanel.css( "width", "25%");
            rightPanel.css("width", "75%");
        });

        Sideview.utils.forEachModuleWithCustomBehavior("setToSourceHostIfOnePortSelected", function(i,module) {
            var baseMethodReference = module.onContextChange.bind(module);
            module.onContextChange = function() {
                if (this.getContext().get("destPort.rawValue") != "") {
                    this.select.val("sourceHost");
                }
                return baseMethodReference();
            }
        });

        Sideview.utils.forEachModuleWithCustomBehavior("onlyShowForOlderVersions", function(i,module) {
            var currentSplunkVersion = Splunk.util.getConfigValue("VERSION_LABEL")
            if (Sideview.utils.compareVersions) {
                if (Sideview.utils.compareVersions(currentSplunkVersion, "4.2.3")==-1) {
                    $("#bumpDiv",module.container).parents().filter("div.layoutRow").show();
                }
            }
        });



        Sideview.utils.forEachModuleWithCustomBehavior("helpButton", function(i,button) {
            var closedLabel = button.getParam("label");
            var openLabel = closedLabel.replace(_("►"),_("▼"));
            button.textVisible = false;

            var toggle = function() {
                button.textVisible = !button.textVisible;
                button._submitButton.find("span").text((button.textVisible)?closedLabel:openLabel);
                button.withEachDescendant(function(module) {
                    if (button.textVisible) {
                        module.container.slideUp("slow")
                    }
                    else {
                        module.container.hide();
                        module.container.find("table").show();
                        module.container.slideDown("slow");
                    }
                });
            }
            toggle(false);
            button._submitButton.click(function(){
                toggle();
            }.bind(button));
        });

    }
});


if (Splunk.util.getCurrentView() == "masaaki_diagram_prototype" && Splunk.Module.FlashChart) {
    Splunk.Module.FlashChart = $.klass(Splunk.Module.FlashChart, {
        /* Make FlashChart not hide the modules downstream from it.
         * In this modified mode it acts a lot like FlashTimeline
         */
        hideDescendants: function() {},
        showDescendants: function() {},
        isReadyForContextPush:function() {
            if (this.getLoadState() < Splunk.util.moduleLoadStates.HAS_CONTEXT) return false;
            return true;
        }
    });
}

if(Splunk.util.getCurrentView() == "splunk_ps" || Splunk.util.getCurrentView() == "splunk_searches_mem_usage") {
    Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
        renderResults: function($super,data) {
            $super(data);
            $('td:nth-child(3),th:nth-child(3)', this.container).hide();
        }
    });
}

if(Splunk.util.getCurrentView() == "crashes") {
    Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
        renderResults: function($super,data) {
            $super(data);
            $('td:nth-child(7),th:nth-child(7)', this.container).hide();
            $('td:nth-child(8),th:nth-child(8)', this.container).hide();
        }
    });
}


if(Splunk.util.getCurrentView() == "inputs") {
    Splunk.Module.EventsViewer = $.klass(Splunk.Module.EventsViewer, {
        initialize: function($super, container) {
            var $p;
            var $ps;
            $super(container);
            $p = $('<p>').addClass('resultsStatusMessage init_results')
                .text('This panel displays details for data inputs.')
            $ps = $('<p>').addClass('resultsStatusMessage init_results')
                .text('Click the details list in the panel on the left to populate this panel with details of the clicked item.')
            this.$helper = $('<ol>').addClass('buffer EventsViewerSoftWrap')
                .append($p,$ps),

            this.$helper.appendTo(this.container);
        },

        renderResults: function($super, htmlFragment) {
            this.$helper.remove();
            $super(htmlFragment);
        },

        hide: function($super, invisibilityMode) {
            console.log("Don't hide me, brah");
            //$super(invisibilityMode);
        }

    });
}

if (Splunk.util.getCurrentView() == "indexing_distributed" && Splunk.Module.FlashChart) {
    Splunk.Module.FlashChart = $.klass(Splunk.Module.FlashChart, {

        BASE_HEIGHT: 50,
        SERIES_HEIGHT: 40,
        MAX_HEIGHT: 4000,

        onDataUpdated: function($super, event) {
            $super(event);

            this.updateAutoSize();
        },

        updateAutoSize: function() {
            var splitSeries = Splunk.util.normalizeBoolean(this.callBridgeMethod("getValue", "layout.splitSeries"));
            if (!splitSeries)
                return;

            var numColumns = parseInt(this.callBridgeMethod("getValue", "data.numColumns"));
            var numSeries = (numColumns > 1) ? (numColumns - 1) : 0;

            var height = parseFloat(this.getParam("height"));
            height = Math.max(height, Math.min(this.BASE_HEIGHT + this.SERIES_HEIGHT * numSeries, this.MAX_HEIGHT));

            $(".FlashWrapperContainer", this.container).css("height", height + "px");
        }

    });
}

    if(Splunk.util.getCurrentView() == "scheduler_activity") {
        Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
            onResultsRendered: function() {
                this.decorateRange(this.container);
            },
            decorateRange: function(container) {
                var _this = this;
                var interval_value = 0
                $('td', container).each(function() {
                    var coordinates = _this.getXYCoordinates($(this));
                    var col_name =_this.getColumnName(coordinates.x, $(this)).toLowerCase();
                    if (col_name == "interval_usage_ratio" ) {
                        interval_value = $(this).text();
                    }
                    if (col_name == "median runtime (seconds)" &&  interval_value > .80 && interval_value < 1) {
                        $(this).css("background-color", '#e67918');
                        $(this).css("color", 'white');
                        $(this).css("font-weight", 'bold');
                    }else if(col_name == "median runtime (seconds)" &&  interval_value > 1) {
                        $(this).css("background-color", '#bb2121');
                        $(this).css("color", 'white');
                        $(this).css("font-weight", 'bold');
                    }
                    if (col_name == "schedule" &&  interval_value > .80 && interval_value < 1) {
                        $(this).css("background-color", '#e67918');
                        $(this).css("color", 'white');
                        $(this).css("font-weight", 'bold');
                    }else if(col_name == "schedule" &&  interval_value > 1) {
                        $(this).css("background-color", '#bb2121');
                        $(this).css("color", 'white');
                        $(this).css("font-weight", 'bold');
                    }
                });
            },
        });
 }
if(Splunk.util.getCurrentView() == "cluster_master_info") {
        Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
            onResultsRendered: function() {
                this.decorateRange(this.container);
            },
            decorateRange: function(container) {
                var _this = this;
                var interval_value = 0
                $('td', container).each(function() {
                    var coordinates = _this.getXYCoordinates($(this));
                    var col_name =_this.getColumnName(coordinates.x, $(this)).toLowerCase();
                    if (col_name == "peer bucket status") {
                         var text = $(this).html();
                         var primary = new RegExp("\\[(.*)\\]", "gi");
                         var searchable = new RegExp("\\{([^\}]*)\\}", "gi");
                         var finalresult = new RegExp("(.*)","gi");
                         var primaryresult = text.replace(primary, "<span class='primary'>$1</span>");
                         var secondaryresult = primaryresult.replace(searchable, "<span class='searchable'>$1</span>");
                         var finalresult = secondaryresult.replace(finalresult, "<span class='unsearchable'>$1</span>");
                         $(this).html(finalresult);
                  }
                });
            },
        });
}

switch (Splunk.util.getCurrentView()) {
    case "performance_splunkd_http":
         Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
             onResultsRendered: function () {
                 // Change status fonts to bold and colorize
                 //$("td[field='sstatus']:contains('OKAY')").addClass("a_okay");
                 //$("td[field='sstatus']:contains('WARNING')").addClass("a_warning");
                 //$("td[field='sstatus']:contains('DANGER')").addClass("a_danger");
                 // add icons to the table
                 $("td[field='status']:contains('OKAY')").addClass("a_okay").html("");
                 $("td[field='status']:contains('WARNING')").addClass("a_warning").html("");
                 $("td[field='status']:contains('DANGER')").addClass("a_danger").html("");
                 // blank icon label field text (we skip adding a class and trying this via CSS due to some IE8 incompatabilities with that approach)
                 $("th:contains('icon')").html("");
         },
       });
     break;



    case 'home':
        // ensure consistent style between Splunk 4.x and 5.x
        if ($('body').hasClass('splVersion-4') === true) {
            $('.SingleValue .singleResult').css('vertical-align', '-4px');
        }

        // keep the 'refreshed' meta information consistent on headlines panel
        $(document).ready(function() {
            var $meta = $('.panel_row2_col').children(':first-child').find('.meta'),
                $span = $('<span>').addClass('splLastRefreshed'),
                $belm = $('<b>').text('real-time');
            $span.append($belm);
            $meta.append($span);
        });

        // override simple results table to add grey rows
        if (Splunk.Module.SimpleResultsTable) {

            Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {

                initialize: function($super, container) {
                    $super(container);
                    this.clicked = null;
                    $('tr', this.container).bind('click', this.onRowClick.bind(this));
                },
                renderResults: function($super, htmlFragment, turbo) {
                    $super(htmlFragment);
                    $(this.resultsContainer, this.container).find('tbody tr')
                        .each(function(idx, evt) {
                           if (idx%2 !== 0) { $(evt).addClass('greyRow'); }
                        });

                    $('tr', this.container).css('cursor','pointer');
                },
                onRowClick: function() {
                    var context = this.getContext();
                    this.clicked = true;
                    context.set('click', this.moduleId);
                    this.pushContextToChildren(context);
                },
                isReadyForContextPush: function($super) {
                    if (this.clicked === null) {
                        return Splunk.Module.CANCEL;
                    }
                    return Splunk.Module.CONTINUE;
                },
            });

        }

        // make the look consistent whether displaying 2 or 3 rows in the activities panel
        if (Splunk.Module.HadoopOpsSingleRowTable) {

            Splunk.Module.HadoopOpsSingleRowTable = $.klass(Splunk.Module.HadoopOpsSingleRowTable, {

                onContextChange: function($super) {
                    if (this.moduleId==="HadoopOpsSingleRowTable_2_2_0") {
                        if (this.getContext().get("search").getTimeRange().isRealTime()) {
                            this.hide('TOGGLE VISIBILITY');
                            this.container.parent()
                                .find('.HadoopOpsSingleRowTable:visible:last')
                                  .find('.HadoopOpsSingleRowTableInner').addClass('islast');
                            $(this.container).closest('.HadoopOpsSingleRowTable')
                        } else {
                            this.container.parent()
                                .find('.HadoopOpsSingleRowTable:visible:last')
                                  .find('.HadoopOpsSingleRowTableInner').removeClass('islast');
                            this.show('TOGGLE VISIBILITY');
                        }
                    }
                    $super();
                }
            });
        }

        // wire up hidden search to listen for context changes pushed upwards
        // in ordet to dispatch its search again
        if (Splunk.Module.HiddenSearch) {

            Splunk.Module.HiddenSearch = $.klass(Splunk.Module.HiddenSearch, {

                applyContext: function(context) {
                    context.get('search').abandonJob();
                    this.pushContextToChildren();
                }

            });
        }
        break;
}






if(Splunk.util.getCurrentView() == "scheduler_activity") {
    Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
        renderResults: function($super,data) {
            $super(data);
            $('td:nth-child(1),th:nth-child(1)', this.container).hide();
        }
    });
}

if(Splunk.util.getCurrentView() == "splunk_topology" ) {

         if (Splunk.Module.StaticContentSample){
            Splunk.Module.StaticContentSample = $.klass(Splunk.Module.StaticContentSample, {
            onContextChange: function($super) {
                    var context = this.getContext(),
                        click = context.get('click') || null,
                        form = context.get('form') || null,
                        prev = this.container.prev(),
                        search = context.get('search'),
                        tables=$(".SimpleResultsTable"),
                        charts=$(".FlashChart"),
                        othercharts=$(".JSChart"),
                        psview=$("#splunk_ps_link"),
                        t;
                    if (form['host']==null){
                        this.container[0].innerHTML="Click a node for details";
                        tables.hide();
                        charts.hide();
                        othercharts.hide();

                    }

                    if (click !== undefined && click !== null) {
                        //this.hide('CLICK KEY');
                        if (form !== null
                          && form['host'] !== null
                          && form['host'] !== undefined) {
                          this.container[0].innerHTML=form['host'];
                          this.container.show();
                          tables.show();
                          charts.show();
                          othercharts.show();
                        }
                    }

                }


                }

            )}

            if (Splunk.Module.HTML){
            Splunk.Module.HTML = $.klass(Splunk.Module.HTML, {
                  onContextChange: function($super) {
                  var context = this.getContext(),
                  click = context.get('click') || null,
                  psview=$("#splunk_ps_link"),
                  form = context.get('form') || null,
                  host=form['host'];
                  psview[0].innerHTML='<a href="splunk_ps?host='+host+'" target="_blank">Click for more detailed CPU/Memory usage for instance <b>'+host+'</b></a>';
 
                  if (form['host']==null){
                        psview.hide() 
                  }
                
                   if (form !== null
                          && form['host'] !== null
                          && form['host'] !== undefined) {
                          psview.show()
                          }

}
}
)};

}


if(Splunk.util.getCurrentView() == "inputs") {
    Splunk.Module.EventsViewer = $.klass(Splunk.Module.EventsViewer, {
        renderResults: function($super,data) {
            $super(data);
            $('td:nth-child(1),th:nth-child(3)', this.container).hide();
        }
    });
}

