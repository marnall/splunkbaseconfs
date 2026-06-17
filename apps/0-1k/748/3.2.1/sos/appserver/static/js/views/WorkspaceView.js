define([
    "jquery",
    "underscore",
    "backbone",
    "d3",
    "bootstrap.modal",
    "text!app/templates/SaveGroupModal.html",
    "text!app/templates/OverwritePatternModal.html",
    "app/collections/Modules",
    "app/views/ModuleView",
    "app/views/TreeView"
], function(
    $,
    _,
    Backbone,
    d3,
    modal,
    SaveGroupModalTemplate,
    OverwritePatternModalTemplate,
    Modules,
    ModuleView,
    TreeView
) {
    return Backbone.View.extend({
        el: "svg#workspace",
        initialize: function() {
            this.app = this.options.app;
            this.roots = this.app.roots;
            this.d3 = d3.select(this.el);
            this.savePattern = [];
            this.d3.call(this.drag());

            this.$overwritePatternModal = $(OverwritePatternModalTemplate).appendTo('#modals');
            this.$modal = $(SaveGroupModalTemplate).appendTo('#modals');
            this.$modal.find(".saveGroup").click(_.bind(this.saveGroup, this));
            this.$modal.on("hidden", _.bind(this.cancelGroup, this));
            // this.roots.on("sort", _.bind(this.cleanUp, this));

            var that = this;
            this.app.mediator.subscribe("modulelist:addModule", function(data, editor, model) {
                that.addModule(data, editor, model);
            });
            this.app.mediator.subscribe("module:createTree", function(rootView) {
                that.addTree(rootView);
            });
            this.app.mediator.subscribe("path:createTree", function(rootView, x, y) {
                that.addTree(rootView, x, y);
            });
            this.app.mediator.subscribe("module:removeFromRoots", function(formerRootModel) {
                that.removeFromRoots(formerRootModel);
            });
            this.app.mediator.subscribe("module:hoverChild", function(data) {
                that.hoverModule(data);
            });
            this.app.mediator.subscribe("module:unhoverChild", _.bind(this.unhoverModule, this));
            this.app.mediator.subscribe("path:addExistingModule", function(view) {
                that.addExistingModule(view);
            });
        },
        drag: function() {
            var that = this,
                dragData = {},
                drag = d3.behavior.drag()
                    .on("dragstart", function() {
                        dragData.offset = that.$el.offset();
                        dragData.x = $(window).scrollLeft() + d3.event.sourceEvent.clientX - dragData.offset.left;
                        dragData.y = $(window).scrollTop() + d3.event.sourceEvent.clientY - dragData.offset.top;
                        dragData.selected = new Modules();

                        dragData.rect = that.d3.append("rect")
                            .attr("x", dragData.x)
                            .attr("y", dragData.y)
                            .attr("width", 0)
                            .attr("height", 0)
                            .attr("fill", that.app.colors.highlightColor)
                            .attr("opacity", 0.5);
                    }).on("dragend", function() {
                        $(document).trigger('elementDragEnd');

                        that.selected = dragData.selected;
                        dragData.rect.remove();

                        // if more than one module is selected, allow save modal to show
                        if (that.selected.length > 0) {
                            that.$modal.modal("show");
                            that.$modal.find("input").val("");
                            that.$modal.find("input").focus();
                        }
                    }).on("drag", function() {
                        var x = $(window).scrollLeft() + d3.event.sourceEvent.clientX - dragData.offset.left,
                            y = $(window).scrollTop() + d3.event.sourceEvent.clientY - dragData.offset.top,
                            width = x - dragData.x,
                            height = y - dragData.y,
                            temp = [],
                            view, x1, x2, y1, y2;

                        dragData.rect.attr("width", Math.abs(x - dragData.x))
                            .attr("height", Math.abs(y - dragData.y));
                        if (width < 0) {
                            dragData.rect.attr("x", x);
                        }
                        if (height < 0) {
                            dragData.rect.attr("y", y);
                        }

                        that.roots.each(function(model) {
                            view = model.get("view");
                            if (view.tree) {
                                x1 = view.tree.x - (view.tree.width / 2);
                                x2 = x1 + view.tree.width;
                                y1 = view.tree.y;
                                y2 = y1 + view.tree.height;
                            } else {
                                x1 = model.get("x");
                                x2 = x1 + model.get("width");
                                y1 = model.get("y");
                                y2 = y1 + model.get("height");
                            }

                            var selected = false;
                            if ((x > x1 && x1 > dragData.x)
                                || (dragData.x > x1 && x1 > x)
                                || (x > x2 && x2 > dragData.x)
                                || (dragData.x > x2 && x2 > x)
                                || (x > x2 && x1 > dragData.x)
                                || (dragData.x > x2 && x1 > x)
                                || (x2 > x && dragData.x > x1)
                                || (x2 > dragData.x && x > x1)) {
                                
                                if ((y > y1 && y1 > dragData.y)
                                    || (dragData.y > y1 && y1 > y)
                                    || (y > y2 && y2 > dragData.y)
                                    || (dragData.y > y2 && y2 > y)
                                    || (y > y2 && y1 > dragData.y)
                                    || (dragData.y > y2 && y1 > y)
                                    || (y2 > y && dragData.y > y1)
                                    || (y2 > dragData.y && y > y1)) {
                                    view.highlight();
                                    dragData.selected.add(model);
                                    selected = true;
                                }
                            }

                            if (!selected) {
                                view.unhighlight();
                                dragData.selected.remove(model);
                            }

                            
                        });
                    });
            return drag;
        },
        cancelGroup: function() {
            this.selected.unhighlight();
            this.selected = undefined;
        },
        saveGroup: function() {
            var input = this.$modal.find("input"),
                name = $(input).val(),
                data = this.selected.toPatterns();
            if (input) {
                if (!this.checkGroupExist(name, data)) {
                    this.app.mediator.publish("workspace:saveGroup", name, data);
                    this.$modal.modal("hide");
                }
            }
        },
        checkGroupExist: function(name, data) {
            var exists = _.contains(_.keys(this.app.patterns), name);
            if (exists) {
                this.$modal.modal("hide");
                this.$overwritePatternModal.modal("show");

                var that = this;
                this.$overwritePatternModal.find(".overwritePattern").one("click", function() {
                    // this saves group under something that's already existing
                    that.app.mediator.publish("workspace:overwriteGroup", name, data);
                    that.$overwritePatternModal.modal("hide");
                });

                return true;
            } else {
                return false;
            }
        },
        addModule: function(data, editor, model) {
            if (this.isCurrentView()) {
                this.roots.add(model, {sort: false});
                model.addParentCollection(this.roots);

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
                this.roots.add(view.model, {sort: false});
                view.model.addParentCollection(this.roots);
                this.$el.append(view.el);
            }
        },
        removeFromRoots: function(formerRootModel) {
            if (this.isCurrentView()) {
                this.roots.remove(formerRootModel);
            }
        },
        addGroup: function(modules) {
            var that = this;
            _.each(modules, function(moduleObject) {
                that.createModules(moduleObject);
            });
            var x = 0,
                y = 0,
                spacing = 40,
                width = 0,
                height = 0,
                maxWidth = this.$el.width() - 50;
            $.each(modules, function(i, moduleObject) {

                var moduleView = moduleObject.view;
                if (moduleObject.module_asArray.length === 0) {
                    if (x + moduleView.data.width > maxWidth) {
                        x = 0;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleObject.left = x;
                    moduleObject.top = y;

                    moduleView.position(x, y, that.app.duration, false);
                    x += moduleView.model.get("width") + spacing;
                    height = Math.max(height, moduleView.model.get("height"));
                    width = Math.max(height, x);
                } else {
                    that.createTree(moduleObject, null);
                    var treeWidth = moduleView.tree.width,
                        treeHeight = moduleView.tree.height;

                    if (x + treeWidth > maxWidth) {
                        x = 0;
                        y = y + height + spacing;
                        height = 0;
                    }
                    moduleObject.left = x;
                    moduleObject.top = y;

                    moduleView.position((x + treeWidth / 2), y, that.app.duration, true);
                    x += treeWidth + spacing;
                    height = Math.max(height, treeHeight);
                    width = Math.max(height, x - (treeWidth / 2));
                }
            });

            /* subscriber: GroupListView (drag) */
            this.app.mediator.publish("workspace:addTree:success", modules, width, height);
        },
        /* tree functions */
        addTree: function(rootView, x, y) {

            if (this.isCurrentView()) {
                this.roots.add(rootView.model, {sort: false});
                rootView.model.addParentCollection(this.roots);

                var g = this.d3.append("g")
                    .classed("tree", true),
                    tree = new TreeView({el: g[0], app: this.app, root: rootView});
                tree.render(x, y);
                tree.update();

            }

        },
        hoverModule: function(data) {
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
        },
        unhoverModule: function() {
            this.d3.selectAll(".childPath").remove();
        },
        clear: function() {
            this.$el.empty();
        },
        show: function() {
            this.$el.show();
        },
        hide: function() {
            this.$el.hide();
        },
        isCurrentView: function() {
            return this.app.view === "workspace";
        },
        /* rendering views from splunk */
        renderExistingView: function(view_json) {

            var that = this;
            $.each(view_json._fromXML.view.module_asArray, function(i, moduleObject) {
                that.createModules(moduleObject);
            });
            var x = 50,
                y = 50,
                spacing = 40,
                height = 0,
                maxWidth = this.$el.width() - 50;
            $.each(view_json._fromXML.view.module_asArray, function(i, moduleObject) {
                var moduleView = moduleObject.view;
                // that.roots.add(moduleView.model);
                if (!moduleObject.module_asArray) {
                    if (x + moduleView.data.width > maxWidth) {
                        x = 50;
                        y = y + height + spacing;
                        height = 0;
                    }
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
                    moduleView.position((x + treeWidth / 2), y, that.app.duration, true);
                    x += treeWidth + spacing;
                    height = Math.max(height, treeHeight);
                }
            });
            // rearrange roots order once model coordinates are set
            this.roots.sort();
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
            if (moduleObject.module_asArray) {
                var that = this;
                $.each(moduleObject.module_asArray, function(i, childModule) {
                    that.createModules(childModule);
                });
            }

        },
        createTree: function(moduleObject, parentView) {
            var moduleView = moduleObject.view;
            if (parentView) {
                this.app.parent = parentView;
                moduleView.addChild();
            } else {
                moduleView.isRoot = true;
            }
            if (moduleObject.module_asArray) {
                var that = this;
                $.each(moduleObject.module_asArray, function(i, childModule) {
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
            this.roots.each(function(model) {
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
        }
    });
});
