define([
	"jquery",
	"underscore",
	"backbone",
	"text!app/templates/ToolBar.html",
	"app/views/ModuleListView",
	"app/views/ModuleInfoView"
], function(
	$,
	_,
	Backbone,
	Template,
	ModuleListView,
	ModuleInfoView
) {
	return Backbone.View.extend({
                id: "toolBar",
                initialize: function() {
                    this.app = this.options.app;
                    this.$activeModuleLists = $();
                    this.$activeModuleEditor = $();
                    this.$visibleModuleListInfos = $();
                    this.$visibleModuleEditorInfo = $();
                    this.client_app = $(document.body).attr("s:app");

                    var that = this;
                    this.app.mediator.subscribe("modulelist:addModuleEditor",
                        function(editor) {
                            that.addModuleEditor(editor);
                        }
                    );
		},
		render: function() {
			// calculate top property:
			this.top = $("#navBar").offset().top + $("#navBar").outerHeight() - 1;
			this.$el.css("top", this.top);
			$(window).resize(_.bind(this.heightChange, this));

			this.$el.html(_.template(Template));
			this.renderModulesList();
			this.$moduleList = this.$("#moduleList");
			this.$moduleInfoList = this.$("#moduleInfoList");
			this.$groupList = this.$("#groupList");
			this.$editList = this.$("#editList");
			this.$notificationList = this.$("#notificationList");

			return this;
		},
		events: {
			"mouseenter .tabBarItem": "mouseenter",
			"mouseleave .tabBarItem": "mouseleave",
			"click .homeImage": "toggleHome",
			"click .groupsImage": "toggleGroups"
		},
		mouseenter: function(e) {
			$(e.target).addClass("active");
		},
		mouseleave: function(e) {
			if (!$(e.target).hasClass("open")) {
				$(e.target).removeClass("active");
			}
		},
		showLists: function() {
			this.$el.addClass("open");
			this.heightChange();
			this.shiftSVG();
		},
		hideLists: function() {
			if (this.$(".list:visible").length === 0) {
				this.$el.removeClass("open");
				this.heightChange();
			}
			this.shiftSVG();
		},
		toggleHome: function() {
			if (this.$moduleList.is(":hidden")) {
				this.showHome();
			} else {
				this.hideHome();
			}
		},
		showHome: function() {
			this.hideGroups();

			this.$(".homeImage").addClass("active");
			this.$(".homeImage").addClass("open");
			this.$moduleList.show();
			this.showLists();
		},
		hideHome: function() {

			this.$(".homeImage").removeClass("active");
			this.$(".homeImage").removeClass("open");
			this.$moduleList.hide();
			this.hideLists();
		},
		toggleGroups: function() {
			if (this.$groupList.is(":hidden")) {
				this.showGroups();
			} else {
				this.hideGroups();
			}
		},
		showGroups: function() {
			this.hideHome();
			this.$(".groupsImage").addClass("active");
			this.$(".groupsImage").addClass("open");
			this.$groupList.show();
			
			this.showLists();
		},
		hideGroups: function() {
			this.$(".groupsImage").removeClass("active");
			this.$(".groupsImage").removeClass("open");
			this.$groupList.hide();
			
			this.hideLists();
		},
		toggleNotification: function() {
			if (this.$notificationList.is(":hidden")) {
				this.showNotifications();
			} else {
				this.hideNotifications();
			}
		},
		togglePattern: function() {
			this.$el.addClass("editing");
			this.$("#moduleEditor").hide();
			this.$("#tabBar").hide();
            this.showHome();
		},
		toggleWorkspace: function() {
			this.$el.removeClass("editing");
			this.$("#tabBar").show();
		},
		/* shifts the position of the SVG, depending on what part of the toolbar is open */
		shiftSVG: function() {
			var left = 0;
			if (this.$(".list:visible").length > 0) {
				left = this.$el.outerWidth();
			}
			this.app.mediator.publish("toolbar:shiftSVG", left);
		},
		heightChange: function() {
			if (this.$el.hasClass("open")) {
				var height = $(window).height() - this.top;
				height -= parseInt(this.$el.css("margin-top"), 10);
				height -= parseInt(this.$el.css("margin-bottom"), 10);
				height -= parseInt(this.$el.css("padding-top"), 10);
				height -= parseInt(this.$el.css("padding-bottom"), 10);
				this.$el.height(height);

				height -= this.$("#tabBar").outerHeight();
				height -= parseInt(this.$("#toolbarLists").css("margin-top"), 10);
				height -= parseInt(this.$("#toolbarLists").css("margin-bottom"), 10);
				height -= parseInt(this.$("#toolbarLists").css("padding-top"), 10);
				height -= parseInt(this.$("#toolbarLists").css("padding-bottom"), 10);
				this.$("#toolbarLists").height(height);				
			} else {
				this.$el.height("auto");
				this.$("#toolbarLists").height("auto");
			}

		},
		addModuleEditor: function(editor) {
			this.$editList.append(editor.render().el);
		},
		/* splunk functions */
		renderModulesList: function() {
                    var that = this;
                    $.ajax({
                        url:  "/custom/splunk_app_shared_components/visual_editor/" + that.client_app + "/modules",
                        dataType: 'json',
                        async: false,
                        success:  function(data) {

                            // sort keys alphabetically and render 
                            var keys = _.pluck(_.values(data), 'filePrefix');
                            keys = keys.sort(
                            function(a, b) {
                                if (a.toLowerCase() < b.toLowerCase()) {
                                    return -1;
                                }
                                if (a.toLowerCase() > b.toLowerCase()) {
                                    return 1;
                                }
                                return 0;
                            });

                            _.each(keys, function(key) {
                                var module = _.find(data, function(val, k) {
                                    return key === val.filePrefix;
                                });
                                var info = new ModuleInfoView({app: that.app, data: module}),
                                    view = new ModuleListView({app: that.app, data: module, info: info});
                                $("#modals").append(info.render().el);
                                that.$("#moduleList").append(view.render().el);

                                //TODO: figure out a better way for this
                                that.app.moduleListViews[key.toLowerCase()] = view;
                            });
                        }
                    });
		}
	});
});
