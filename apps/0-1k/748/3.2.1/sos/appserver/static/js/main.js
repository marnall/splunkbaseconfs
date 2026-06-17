require.config({
        baseUrl: "/static/app/splunk_app_shared_components/js/contrib",
        paths: {
                "app": "..",
                "d3": "d3/d3.v3",
                "bootstrap.modal": "bootstrap/bootstrap-modal.min",
                "bootstrap.button": "bootstrap/bootstrap-button",
                "bootstrap.tooltip": "bootstrap/bootstrap-tooltip",
                "domReady": "domReady",
                "jquery": "jquery/jquery.min",
                "jquery.bgiframe": "jquery/jquery.bgiframe",
                "lowpro": "/static/js/contrib/lowpro_for_jquery",
                "splunk.logger": "/static/js/logger",
                "splunk.menu_builder": "/static/js/menu_builder",
                "backbone": "backbone/backbone-1.0.0",
                "spinner": "spin.min"
        },
        shim: {
                "underscore": {
                        exports: "_"
                },
                "backbone": {
                        deps: ["underscore", "jquery"],
                        exports: "Backbone"
                },
                "d3": {
                	exports: 'd3'
                },
                "bootstrap.modal": {
                	deps: ['jquery']
                },
                "bootstrap.button": {
                    deps: ['jquery']
                },
                "bootstrap.tooltip": {
                    deps: ['jquery']
                },
                "jquery": {
                	exports: '$'
                },
                "lowpro": {
                        deps: ['jquery']
                },
                "jquery.bgiframe": {
                        deps: ['jquery']
                },
                "splunk.menu_builder": {
                        deps: ['jquery', 'lowpro', 'jquery.bgiframe']
                }
        }
});

require([
	"jquery",
	"underscore",
	"backbone",
	"d3",
	"mediator",
    "spinner",
	"app/views/AppView",
    "app/collections/Modules",
    "app/routers/router"

], function(
	$,
	_,
	Backbone,
	d3,
	Mediator,
    Spinner,
	AppView,
    Modules,
    Router
) {
	var app = {},
	    appView,
	    $body = $('body'),
        app_name = $body.attr('s:app'),
        pattern = $body.attr('s:pattern'),
        view = $body.attr('s:view');
        
    app.view = "workspace";
	app.mediator = new Mediator();
    app.moduleSettings = {padding: 5, imageSize: 12};
    app.moduleListViews = {};
    app.router = new Router(); 
    app.parent = false;
    app.colors = {fill: "#fff", stroke: "#666", red: "#dc322f",
                highlightColor: "#08c", parentColor: "#08c", 
                childColor: "#999", disableColor: "#000"};
    app.duration = 750;
    app.roots = undefined;
    app.patternRoots = new Modules(); // the roots of the particular pattern being edited
    app.patterns = {};
    app.spinner = new Spinner({radius: 10, className: "spinner"}).spin();
    app.prevURL = window.location.pathname;
    app.patternToDelete = undefined;
    $("body").append(app.spinner.el);
    $(app.spinner.el).css("position", "fixed");

	appView = new AppView({app:app});
	appView.render();
    if (view !== "") {
        appView.navbarView.openView(view, app_name);
    } else if (pattern !== "") {
        app.mediator.subscribe("app:getPatternsJSON:finished", function() {
            app.patterns[pattern].editGroup(); // calls editGroup on a GroupListView
        });
    } else {
        app.spinner.stop();
    }
    Backbone.history.start();
    window.appView = appView;
});

