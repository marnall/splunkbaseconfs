define([
	"jquery",
	"underscore",
	"backbone",
	"d3",
	"app/collections/Modules",
	"app/models/Group",
	"text!app/templates/GroupList.html"
], function(
	$,
	_,
	Backbone,
	d3,
	Modules,
	Group,
	Template
) {
	/*
	GroupListView: owns the div within #groupList, that includes the group/pattern name
	and the icon to edit the pattern as well as to remove the pattern if it is a non-default
	pattern.
	*/
	return Backbone.View.extend({
		initialize: function() {
			this.app = this.options.app;
			this.name = this.options.name;
			this.data = this.options.data;
			this.isDefault = this.options.isDefault;
			this.model = new Group({name: this.name, data: this.data, isDefault: this.isDefault});

			var that = this;
			this.model.on("change:name", function(model, name) {
				that.render();
				that.name = name;
			});
			this.model.on("change:data", function(model, data) {
				that.data = data;
			});
			// this.app.mediator.subscribe("pattern:addTree:success", function(modules) {
			// 	that.addTreeSuccessful(modules);
			// });
		},
		render: function() {
			this.$el.html(_.template(Template, this.model.attributes));
			d3.selectAll(this.$(".groupNameText"))
				.call(this.drag());

			return this;
		},
		drag: function() {
			var that = this,
				view, modules,
				width, height,
				dragData = {},
				drag = d3.behavior.drag()
					.on("dragstart", function() {
						that.addGroup();
					}).on("dragend", function(){
						_.each(modules, function(moduleObject) {
							moduleObject.view.dragging = false;
						});
						modules = false;
						// rearrange roots order once model coordinates are set
						that.app.roots.sort();
	                    $(document).trigger('elementDragEnd');
	                }).on("drag", function() {
						var x = d3.event.sourceEvent.clientX,
							y = d3.event.sourceEvent.clientY,
							svg = "svg#" + that.app.view,
							svgLeft = parseInt($(svg).css("left"), 10),
							svgTop = parseInt($(svg).css("top"), 10),
							svgWidth = $(svg).width(),
                            svgHeight = $(svg).height(),
                            tempX, tempY;
						x = x - svgLeft;
						y = y - svgTop - 10;

						if (modules) {
							if (x < 0) {
								x = 0;
							} else if (x + width > svgWidth) {
								x = svgWidth - width;
							}
							if (y < 0) {
								y = 0;
							} else if (y + height > svgHeight) {
								y = svgHeight - height;
							}

							_.each(modules, function(moduleObject) {
								view = moduleObject.view;
								view.dragging = true;

								tempX = x;
								tempY = y;
								if (view.tree) {
									tempX += moduleObject.left + (view.tree.width / 2);
								} else {
									tempX += moduleObject.left;
								}
								tempY += moduleObject.top;
								view.position(tempX, tempY, 0, true);
								view = undefined;
							});
						}
	                });

	        	this.app.mediator.subscribe("workspace:addTree:success", function(sentModules, sentWidth, sentHeight) {
	        		modules = sentModules;
	        		width = sentWidth;
	        		height = sentHeight;
	        	});

			return drag;
		},
		events: {
			"click .editGroup": "editGroup",
			"click .removeGroup": "removeGroup",
			"mouseenter": "mouseenter",
			"mouseleave": "mouseleave"
		},
		mouseenter: function() {
			this.$(".hidden").addClass("shown");
			this.$(".hidden").removeClass("hidden");
		},
		mouseleave: function() {
			this.$(".shown").addClass("hidden");
			this.$(".shown").removeClass("shown");
		},
		addGroup: function() {
			var json = this.model.toPatterns();
			/* subscriber: AppView (addGroup) */
			this.app.mediator.publish("groupList:addGroup", json.data);
		},
		editGroup: function() {
            this.app.spinner.spin();
			var json = this.model.toPatterns();
			/* subscriber: AppView (editGroup), NavbarView (editGroup) */
			this.app.mediator.publish("groupList:editGroup", this, json.data);
		},
		removeGroup: function() {
			if (!this.isDefault) {
				this.app.mediator.publish("groupList:removeGroup", this);
			}
		},
		remove: function() {
			this.$el.remove();
		}
		// addTreeSuccessful: function(modules) {
		// 	modules = _.map(modules, function(moduleObject) {
		// 		return moduleObject.view.model;
		// 	});
		// 	this.modules = new Modules(modules);
		// 	// this.model.set("model", moduleView.model);
		// }
	});
});