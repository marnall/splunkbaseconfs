define([
	"jquery",
	"underscore",
	"backbone",
    "d3",
    "app/collections/Modules",
    "app/views/ModuleView",
    "app/views/TreeView"
], function(
	$,
	_,
	Backbone,
	d3,
    Modules,
	ModuleView,
	TreeView
) {
	return Backbone.View.extend({
		el: "svg#pattern",
		initialize: function() {
            this.app = this.options.app;
            this.patternRoots = this.app.patternRoots;
            this.d3 = d3.select(this.el);

            // this.patternRoots.on("sort", _.bind(this.cleanUp, this));

            var that = this;
            this.app.mediator.subscribe("groupList:editGroup", function(groupView, data) {
                that.group = groupView.model;
                that.patternRoots.reset();
                that.editGroup(data);
            });
            this.app.mediator.subscribe("modulelist:addModule", function(data, editor, model) {
                that.addModule(data, editor, model);
            });
            this.app.mediator.subscribe("module:createTree", function(rootView) {
                that.addTree(rootView);
            });
            this.app.mediator.subscribe("module:hoverChild", function(data) {
                that.hoverModule(data);
            });
            this.app.mediator.subscribe("module:unhoverChild", _.bind(this.unhoverModule, this));
            this.app.mediator.subscribe("module:removeFromRoots", function(model) {
                that.removeFromRoots(model);
            });
            this.app.mediator.subscribe("path:createTree", function(rootView, x, y) {
                that.addTree(rootView, x, y);
            });
            this.app.mediator.subscribe("path:addExistingModule", function(view) {
                that.addExistingModule(view);
            });
            this.app.mediator.subscribe("navbar:saveGroup", _.bind(this.saveGroup, this));
        },
        editGroup: function(modules) {

            var that = this;
            _.each(modules, function(moduleObject) {
                that.createModules(moduleObject);
            });
            var x = 50,
                y = 50,
                spacing = 40,
                height = 0,
                maxWidth = this.$el.width() - 50;
            $.each(modules, function(i, moduleObject) {

                var moduleView = moduleObject.view;
                if (moduleObject.module_asArray.length === 0) {
                    if (x + moduleView.data.width > maxWidth) {
                        x = 50;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleObject.left = x;
                    moduleObject.top = y;

                    moduleView.position(x, y, that.app.duration, false);
                    x += moduleView.model.get("width") + spacing;
                    height = Math.max(height, moduleView.model.get("height"));
                } else {
                    that.createTree(moduleObject, null);
                    var treeWidth = moduleView.tree.width,
                        treeHeight = moduleView.tree.height;

                    if (x + treeWidth > maxWidth) {
                        x = 50;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleObject.left = x;
                    moduleObject.top = y;

                    moduleView.position((x + treeWidth / 2), y, that.app.duration, true);
                    x += treeWidth + spacing;
                    height = Math.max(height, treeHeight);
                }
            });

            /* subscriber: GroupListView (addTreeSuccessful) */
            // this.app.mediator.publish("pattern:addTree:success", modules);
        },
        saveGroup: function() {
            var data = this.patternRoots.toPatterns();
            this.group.set("data", data);
            this.app.mediator.publish("pattern:saveGroup", this.group.toPatterns());
        },
        cancelGroup: function() {
            this.clear();
        },
        addModule: function(data, editor, model) {
            if (this.isCurrentView()) {
                this.patternRoots.add(model, {sort: false});
                model.addParentCollection(this.patternRoots);

                var g = this.d3.append("g")
                    .classed("module", true),
                    view = new ModuleView({el: g[0], app: this.app, data: data, editor: editor, model: model});
                view.render();

                this.app.mediator.publish("addModule:success", view);
                return view;
            }
        },
        addExistingModule: function(view) {
            if (this.isCurrentView()) {
                this.patternRoots.add(view.model, {sort: false});
                view.model.addParentCollection(this.patternRoots);
                this.$el.append(view.el);
            }
        },
        addTree: function(rootView, x, y) {

            if (this.isCurrentView()) {
                this.patternRoots.add(rootView.model, {sort: false});
                rootView.model.addParentCollection(this.patternRoots);
                var g = this.d3.append("g")
                    .classed("tree", true),
                    tree = new TreeView({el: g[0], app: this.app, root: rootView});
                tree.render(x, y);
                tree.update();
            }

        },
        removeFromRoots: function(formerRootModel) {
            if (this.isCurrentView()) {
                this.patternRoots.remove(formerRootModel);
            }
        },
        hoverModule: function(data) {
        	if (this.isCurrentView()) {
	            var childColor = this.app.colors.childColor,
	                disableColor = this.app.colors.disableColor,
	                parentColor = this.app.colors.parentColor;
	            var diagonal =  d3.svg.diagonal()
	                .source(function(d) {
	                    var x = d.source.x,
	                        y = d.source.y,
	                        height = d.source.height;
	                    return {"x": x, "y": y + height};
	                });

	            this.d3.selectAll(".childPath").remove();
	            this.d3.append("path").data([data])
	                .classed("childPath", true)
	                .attr("stroke-dasharray", "10, 10")
	                .attr("fill", "none").attr("stroke", childColor)
	                .attr("d", diagonal);           		
            }
        },
        unhoverModule: function() {
        	if (this.isCurrentView()) {
	            this.d3.selectAll(".childPath").remove();
        	}
        },
        createModules: function(moduleObject) {

            var moduleListViews = this.app.moduleListViews,
                moduleName = moduleObject._name,
                moduleListView = moduleListViews[moduleName.toLowerCase()],
                helper = moduleListView.addModuleHelper(),
                data = helper.data,
                model = helper.model,
                editor = helper.editor,
                view = this.addModule(data, editor, model);

            model.set("params", model.toParams(moduleObject));
            model.set("attrs", model.toAttrs(moduleObject));
            moduleObject.view = view;
            this.app.mediator.publish("modulelist:addModuleEditor", editor);
            if (moduleObject.modules) {
                var that = this;
                $.each(moduleObject.modules, function(i, childModule) {
                    that.createModules(childModule);
                });
            }

        },
        createTree: function(moduleObject, parentView) {
            var moduleView = moduleObject.view,
                that = this;
            if (parentView) {
                this.app.parent = parentView;
                moduleView.addChild();
            } else {
                moduleView.isRoot = true;
            }
            if (moduleObject.modules) {
                $.each(moduleObject.modules, function(i, childModule) {
                    that.createTree(childModule, moduleView);
                });
            }
        },
        cleanUp: function() {
            var x = 50,
                y = 50,
                spacing = 40,
                height = 0,
                maxWidth = this.$el.width() - 50,
                that = this;
            this.patternRoots.each(function(model) {
                var moduleView = model.get("view");
                if (model.hasChildren()) {
                    var treeWidth = moduleView.tree.width,
                        treeHeight = moduleView.tree.height;
                    if (x + treeWidth > maxWidth) {
                        x = 50;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleView.position((x + treeWidth / 2), y, that.app.duration, true);
                    x += treeWidth + spacing;
                    height = Math.max(height, treeHeight);
                } else {
                    if (x + model.get("width") > maxWidth) {
                        x = 50;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleView.position(x, y, that.app.duration, false);
                    x += model.get("width") + spacing;
                    height = Math.max(height, model.get("height"));
                }
            });
        },
        show: function() {
            this.$el.show();
        },
        hide: function() {
            this.$el.hide();
        },
        clear: function() {
            this.$el.empty();
        },
        isCurrentView: function() {
            return this.app.view === "pattern";
        }
    });
});