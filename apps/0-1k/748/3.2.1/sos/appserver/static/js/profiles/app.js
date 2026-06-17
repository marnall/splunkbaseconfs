// reference this from another build profile with mainConfigFile: './shared.build.profile.js'
require.config({
    baseUrl: '/static',
    preserveLicenseComments: false,
    paths: {
        // paths outside of baseUrl
        'modules': '/modules',
        'domReady': '/static/app/splunk_app_shared_components/js/contrib/domReady', 

        // jQuery and contrib plugins
        'jquery': '/static/app/splunk_app_shared_components/js/contrib/jquery/jquery.min',
        'jquery.iframe.auto.height': '/static/app/splunk_app_shared_components/js/contrib/jquery/jquery.iframe-auto-height',
        'jquery-multiselect': '/static/app/splunk_app_shared_components/js/contrib/jquery-ui/jquery.multiselect',
        'jquery-multiselect-filter': '/static/app/splunk_app_shared_components/js/contrib/jquery-ui/jquery.multiselect.filter',
        'jquery.history': 'js/contrib/jquery.history',
        'jquery.bgiframe': '/static/app/splunk_app_shared_components/js/contrib/jquery/jquery.bgiframe',
        'jquery.cookie': 'js/contrib/jquery.cookie',

        // internal jQuery plugins
        /*
        'splunk.jquery.csrf': 'js/splunk.jquery.csrf_protection',
        'splunk.widget.popupmenu': 'js/splunk.widget.popupMenu',
        */

        // jQuery UI plugins
        'jquery.ui.core': '/static/app/splunk_app_shared_components/js/contrib/jquery-ui/jquery-ui-1.9.2.custom',
        //'jquery.ui.position': 'js/contrib/jquery/ui/jquery.ui.position',
        /*
        'jquery.ui.widget': '/sc/js/contrib/jquery-ui/jquery.ui.widget',
        'jquery.ui.datepicker': 'js/contrib/jquery.ui.datepicker/jquery.ui.datepicker',
        'jquery.ui.button': '/js/contrib/jquery/ui/jquery.ui.button',
        'jquery.ui.menu': '/sc/js/contrib/jquery/ui/jquery.ui.menu',
        'jquery.ui.popup': '/sc/js/contrib/jquery/ui/jquery.ui.popup',
        'jquery.ui.mouse': '/sc/js/contrib/jquery/ui/jquery.ui.mouse',
        'jquery.ui.draggable': '/sc/js/contrib/jquery/ui/jquery.ui.draggable',
        'jquery.ui.droppable': '/sc/js/contrib/jquery/ui/jquery.ui.droppable',
        'jquery.ui.sortable': '/sc/js/contrib/jquery/ui/jquery.ui.sortable',
        'jquery.ui.dialog': '/sc/js/contrib/jquery/ui/jquery.ui.dialog',
        'jquery.ui.resizable': '/sc/js/contrib/jquery/ui/jquery.ui.resizable',
        'jquery.ui.effect': '/sc/js/contrib/jquery/ui/jquery.ui.effect',
        'jquery.ui.effect-bounce': '/sc/js/contrib/jquery/ui/jquery.ui.effect-bounce',
        'jquery.ui.effect-shake': '/sc/js/contrib/jquery/ui/jquery.ui.effect-shake',
        */

        // bootstrap components
        'bootstrap.affix': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-affix',
        'bootstrap.alert': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-alert',
        'bootstrap.button': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-button',
        'bootstrap.carousel': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-carousel',
        'bootstrap.collapse': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-collapse',
        'bootstrap.dropdown': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-dropdown',
        'bootstrap.modal': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-modal',
        'bootstrap.popover': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-popover',
        'bootstrap.scrollspy': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-scrollspy',
        'bootstrap.tab': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-tab',
        'bootstrap.tooltip': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-tooltip',
        'bootstrap.transition': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-transition',
        'bootstrap.typeahead': '/static/app/splunk_app_shared_components/js/contrib/bootstrap/bootstrap-typeahead',
        
        //syntax highlighter
        'shCore': '/static/app/splunk_app_shared_components/js/contrib/syntaxHighlighter/shCore',
        'shBrushJS': '/static/app/splunk_app_shared_components/js/contrib/syntaxHighlighter/brushes/shBrushJScript',
        'shBrushXML': '/static/app/splunk_app_shared_components/js/contrib/syntaxHighlighter/brushes/shBrushXml',
        'shBrushPY': '/static/app/splunk_app_shared_components/js/contrib/syntaxHighlighter/brushes/shBrushPython',

        // other contrib libraries
        'underscore': '/static/app/splunk_app_shared_components/js/contrib/underscore',
        'backbone': '/static/app/splunk_app_shared_components/js/contrib/backbone/backbone',
        'highcharts': 'js/contrib/highcharts',
        'json': 'js/contrib/json2',
        //'backbone_validation': '/sc/js/contrib/backbone-validation',
        /* augments builtin prototype */
        'strftime': 'js/contrib/strftime',
        //'swfobject': 'contrib/swfobject',
        //'leaflet': 'contrib/leaflet/leaflet',
        //'jg_global': 'contrib/jg_global',
        //'jgatt': 'contrib/jg_library',
        'lowpro': 'js/contrib/lowpro_for_jquery',
        'spin': '/static/app/splunk_app_shared_components/js/contrib/spin',

        // Splunk legacy
        'splunk': 'js/splunk',
        'splunk.init': 'js/init',
        'splunk.legend': 'js/legend',
        'splunk.logger': 'js/logger',
        'splunk.util': 'js/util',
        'splunk.pdf': 'js/pdf',
        'splunk.i18n': 'js/i18n',
        'splunk.paginator': 'js/paginator',
        'splunk.messenger': 'js/messenger',
        'splunk.menu_builder': 'js/menu_builder',
        'splunk.time': 'js/splunk_time',
        'splunk.timerange': 'js/time_range',
        'splunk.window': 'js/window',
        'splunk.jabridge': 'js/ja_bridge'
    },
    shim: {

        /* START contrib jQuery plugins */
        'jquery.cookie': {
            deps: ['jquery']
        },
        'jquery.history': {
            deps: ['jquery'],
                exports: 'History'
        },
        'jquery.bgiframe': {
            deps: ['jquery']
        },

        "jquery.attributes": {
            deps: ['jquery']
        },
        "spin": {
            deps: ['jquery'],
            exports: 'Spinner'
        },

        "jquery.sparkline": {
            deps: ['jquery']
        },

        "jquery.deparam": {
            deps: ['jquery']
        },

        /* START internal jQuery plugins */
        'splunk.jquery.csrf_protection': {
            deps: ['jquery.cookie', 'splunk.util']
        },

        /* jQuery UI plugins */
        'jquery.ui.core': {
            deps: ['jquery']
        },

        // bootstrap components
        'bootstrap.affix': {
            deps: ['jquery']
        },
        'bootstrap.alert': {
            deps: ['jquery']
        },
        'bootstrap.button': {
            deps: ['jquery']
        },
        'bootstrap.carousel': {
            deps: ['jquery']
        },
        'bootstrap.collapse': {
            deps: ['jquery']
        },
        'bootstrap.dropdown': {
            deps: ['jquery']
        },
        'bootstrap.modal': {
            deps: ['jquery']
        },
        'bootstrap.popover': {
            deps: ['jquery', 'bootstrap.tooltip']
        },
        'bootstrap.scrollspy': {
            deps: ['jquery']
        },
        'bootstrap.tab': {
            deps: ['jquery']
        },
        'bootstrap.tooltip': {
            deps: ['jquery']
        },
        'bootstrap.transition': {
            deps: ['jquery']
        },
        'bootstrap.typeahead': {
            deps: ['jquery']
        },
        'jquery.multiselect': {
            deps: ['jquery']
        },
        'jquery.multiselect.filter': {
            deps: ['jquery', 'jquery.multiselect']
        },
        shBrushXML: {
            deps: ['shCore']
        },
        shBrushJS: {
            deps: ['shCore']
        },
        shBrushPY: {
            deps: ['shCore']
        },
        underscore: {
            deps: ['splunk.i18n'],
            exports: '_',
            init: function(i18n) {
                // use underscore's mixin functionality to add the ability to localize a string
                this._.mixin({
                    t: function(string) {
                        return i18n._(string);
                    }
                });
                // can't put underscore in no conflict mode here because Backbone needs to find it on the global scope
                return this._;
            }
        },
        backbone: {
            deps: ['jquery', 'underscore'],
            exports: 'Backbone',
            init: function($, _) {
                // now that Backbone has a reference to underscore, we need to give the '_' back to i18n
                _.noConflict();

                // inject a reference to jquery in case we ever run it in no conflict mode
                // set up for forward compatibility with Backbone, setDomLibrary is being replaced with Backbone.$
                if(this.Backbone.hasOwnProperty('setDomLibrary')) {
                    this.Backbone.setDomLibrary($);
                }
                else {
                    this.Backbone.$ = $;
                }
                return this.Backbone.noConflict();
            }
        },
        /*
        backbone_validation: {
            deps: ['backbone', 'underscore']
        },
        "backbone.nested": {
            // Not sure if needed
            deps: ['backbone'],
            exports: 'Backbone.NestedModel'
        },
        */
        highcharts: {
            //deps: ['jquery', 'highcharts.runtime_patches'],
            deps: ['jquery'],
            exports: 'Highcharts'
            //init: function($, runtimePatches) {
            //    runtimePatches.applyPatches(this.Highcharts);
            //    return this.Highcharts;
            //}
        },
        json: {
            exports: 'JSON'
        },

        lowpro: {
            deps: ['jquery']
        },

        /* Start Splunk legacy */
        splunk: {
            exports: 'Splunk'
        },
        'splunk.menu_builder': {
            deps: ['jquery', 'jquery.ui.core', 'jquery.bgiframe', 'lowpro', 'splunk.logger']
        },
        'splunk.util': {
            //deps: ['jquery', 'splunk', 'splunk.config'],
            deps: ['jquery', 'splunk'],
            exports: 'Splunk.util',
            init: function($, Splunk, config) {
                return $.extend({ sprintf: this.sprintf }, Splunk.util);
            }
        },
        'splunk.legend': {
            deps: ['splunk'],
                exports: 'Splunk.Legend'
        },
        'splunk.logger': {
            deps: ['splunk', 'splunk.util'],
                exports: 'Splunk.Logger'
        },
        'splunk.pdf': {
            deps: ['splunk', 'splunk.util', 'jquery'],
            exports: 'Splunk.pdf'
        },
        strftime: {
            deps: []
        },
        'splunk.paginator': {
            deps: ['splunk'],
                exports: 'Splunk.paginator'
        },
        'splunk.jquery.csrf': {
            deps: ['jquery', 'jquery.cookie', 'splunk.util']
        },
        'splunk.messenger': {
            deps: ['splunk', 'splunk.util', 'splunk.logger', 'splunk.i18n', 'lowpro'],
            exports: 'Splunk.Messenger'
        },
        'splunk.timerange': {
            //deps: ['splunk', 'splunk.util', 'splunk.logger', 'splunk.i18n', 'splunk.time', 'lowpro'],
            deps: ['splunk', 'splunk.util', 'splunk.logger', 'splunk.i18n', 'lowpro'],
            exports: 'Splunk.Timerange',
            init: function(Splunk) {
                Splunk.namespace("Globals");
                if (!Splunk.Globals.timeZone) {
                    Splunk.Globals.timeZone = new Splunk.TimeZone(Splunk.util.getConfigValue('SERVER_ZONEINFO'));
                }
                return Splunk.TimeRange;
            }
        },
        'splunk.window': {
            deps: ['splunk', 'splunk.util', 'splunk.i18n'],
            exports: 'Splunk.window'
        },
        'splunk.jabridge': {
            deps: ['splunk'],
            exports: 'Splunk.JABridge'
        },
        'splunk.init': {
            deps: ['splunk', 'splunk.i18n', 'splunk.util', 'lowpro']
        }
    }
});

