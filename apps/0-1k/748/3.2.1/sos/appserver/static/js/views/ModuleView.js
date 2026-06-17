define([
	"jquery",
	"underscore",
	"backbone",
	"d3",
    "app/views/TreeView"
], function(
	$,
	_,
	Backbone,
	d3,
    TreeView
) {
    /*
    ModuleView: owns the SVG group that represents a module in the workspace
    includes module name, icons to edit a module parameters and attributes and
    to delete the module.

    editing module parameters opens up an instance of ModuleEditorView.
    */
	return Backbone.View.extend({
        initialize: function() {
            this.app = this.options.app;
            this.data = this.options.data;
            this.model = this.options.model;
            this.model.attributes.view = this;
            this.editor = this.options.editor;
            this.editor.model = this.model;

            this.d3 = d3.select(this.el);

            // it is not part of a tree
            this.isRoot = true;
            this.root = false;
            this.tree = false;

            var that = this;
        },
        render: function() {

            // claculate x & y positions
            if (!this.data.x && !this.data.y) {

                if (this.app.view == "workspace") {
                    this.data.x = this.model.attributes.x = 0;
                    this.data.y = this.model.attributes.y = 0;                    
                } else {
                    this.data.x = this.model.attributes.x = $(window).width() / 2 - parseInt($("svg#pattern").css("left"), 10);
                    this.data.y = this.model.attributes.y = 100;
                }

            } else if (this.data.x < 0) {
                this.data.x = 0;
            } else if (this.data.y < 0) {
                this.data.y = 0;
            }

            this.d3.attr("transform", "translate("+ this.data.x + "," + this.data.y + ")");

            var padding = this.app.moduleSettings.padding,
                imageSize = this.app.moduleSettings.imageSize,
                stroke = this.app.colors.stroke,
                fill = this.app.colors.fill;
            this.rect = this.d3.append("rect")
                .attr("class", "module")
                .attr("width", this.data.width)
                .attr("height", this.data.height)
                .attr("x", 0).attr("y", 0)
                .attr("stroke", stroke).attr("fill", fill)
                .call(this.drag());
            this.text = this.d3.append("text")
                .attr("class", "module")
                .attr("text-anchor", "start")
                .attr("width", this.data.textW)
                .attr("height", this.data.textH)
                .attr("x", padding)
                .attr("y", (this.data.height / 2) + padding)
                .attr("fill", stroke)
                .call(this.drag())
                .text(this.data.text);
            this.imageEdit = this.d3.append("image")
                .attr("class", "editModule")
                .attr("width", imageSize)
                .attr("height", imageSize)
                .attr("x", this.data.textW + (2 * padding))
                .attr("y", (this.data.height / 2) - (imageSize / 2))
                .attr("xlink:href", "/static/app/splunk_app_shared_components/img/pencil.png")
                .style("display", "none")
                .on("click", _.bind(this.showEditor, this));
            this.imageRemove = this.d3.append("image")
                .attr("class", "removeModule")
                .attr("width", imageSize)
                .attr("height", imageSize)
                .attr("x", this.data.textW + (3 * padding) + imageSize)
                .attr("y", (this.data.height / 2) - (imageSize / 2))
                .attr("xlink:href", "/static/app/splunk_app_shared_components/img/remove.gif")
                .style("display", "none")
                .on("click", _.bind(this.remove, this));

            return this;
        },
        events: {
            "click rect": "addChild",
            "click text": "addChild",
            "mouseover rect": "hoverChild",
            "mouseover text": "hoverChild",
            "mouseover image": "hoverChild",
            "mouseleave rect": "unhoverChild",
            "mouseleave text": "unhoverChild",
            "mouseleave image": "unhoverChild" 
        },
        addChild: function() {
            var parent = this.app.parent,
                parentColor = this.app.colors.parentColor,
                disableColor = this.app.colors.disableColor;

            if (!parent) {
                this.app.parent = this;
                this.rect.attr("stroke", parentColor);
            } else {
                // if this module is to become the child
                var child = this,
                    tree;
                // the child is either the root, or not part of an existing tree
                if ((parent !== child) && (child.isRoot || !child.tree)) {
                    parent.model.addChild(child.model);
                    child.model.addParentCollection(parent.model.get("modules"));

                    // parent does not belong to a tree
                    if (!parent.tree) {
                        parent.isRoot = true;
                        // tell AppView to create the tree
                        this.app.mediator.publish("module:createTree", parent);
                    } else {
                        parent.tree.update();
                    }
                    // if child was root
                    if (child.isRoot) {
                        child.isRoot = false;
                        /* Subscribers: WorkspaceView, PatternView */
                        this.app.mediator.publish("module:removeFromRoots", child.model);
                    }
                    // reset
                    this.app.parent = false;
                    parent.rect.attr("stroke", disableColor);
                } else {
                    parent.rect.attr("stroke", disableColor);
                    // if parent is clicked on again, cancel add child
                    if (this == parent) {
                        this.app.parent = false;
                    } else {
                        this.rect.attr("stroke", parentColor);
                        this.app.parent = child;
                    }
                }
            }
        },
        hoverChild: function() {

            var parent = this.app.parent,
                child = this,
                childColor = this.app.colors.childColor,
                disableColor = this.app.colors.disableColor,
                parentColor = this.app.colors.parentColor;

            // for any module:
            if (!this.dragging) {
                this.showActions();
                this.rect.attr("width", this.data.expandedWidth);
            }

            // if this is a child that can be added
            if (parent && (parent !== child) && (child.isRoot || !child.tree)) {
                child.rect.attr("stroke", childColor);
                var source = parent.model.toJSON(),
                    target = child.model.toJSON(),
                    data = {"source": source, "target": target};
                
                if (parent.tree) {
                    source.x += parent.tree.x + (source.width / 2);
                    source.y += parent.tree.y;
                } else {
                    source.x += (source.width / 2);
                }
                
                if (child.tree) {
                    target.x = child.tree.x;
                    target.y = child.tree.y;
                } else {
                    target.x += (target.width / 2);
                }
                
                this.app.mediator.publish("module:hoverChild", data);

            } else {
                this.rect.attr("stroke", parentColor);
            }
        },
        unhoverChild: function() {
            var parent = this.app.parent,
                disableColor = this.app.colors.disableColor;

            if (!this.dragging) {
                this.hideActions();
                this.rect.attr("width", this.data.width);
            }

            if (parent !== this){
                this.rect.attr("stroke", disableColor);             
            }

            this.app.mediator.publish("module:unhoverChild");
        },
        addToTree: function(tree, x, y, transition) {
            // view.unhoverChild();
            var oldX, oldY;
            if (!this.tree) {
                // if it's not yet part of any tree
                oldX = this.model.get("x") - tree.x;
                oldY = this.model.get("y") - tree.y;
                this.d3.attr("transform", "translate(" + oldX + "," + oldY + ")");
                
            } else {
                // if it does have a tree, the tree it belongs to 
                // isn't the new tree it's being appended to
                oldX = (this.tree.x + this.model.get("x")) - tree.x;
                oldY = (this.tree.y + this.model.get("y")) - tree.y;
                this.d3.attr("transform", "translate(" + oldX + "," + oldY + ")");
                
                this.tree.removeIfEmpty();
            }
            this.tree = tree;
            this.position(x, y, transition);

        },
        remove: function() {
            this.removeModule();
            this.model.remove();
            if (this.isRoot && this.tree) {
                this.tree.removeTree();
            } else if (this.tree) {
                this.tree.update();
            }
        },
        drag: function() {
            /*
            The general problem here is that dragging can take place with the mouse over any part of the SVG element
            we need to offset the transform by that position
            
                a       b
                [ *] => [ *]

            Note the * is the initial drag position.
            The distance from A to B is the same as * to *.
            However, they are offset by the distance between A and *
            So we must subtract that distance from the transformation.
            */

            var that = this,
                path,
                dragData = {},
                drag = d3.behavior.drag()
                    .on("dragstart", function() {
                        if (that.tree) {
                            dragData.width = that.tree.width;
                            dragData.height = that.tree.height;
                            dragData.dx = d3.event.sourceEvent.clientX - that.tree.x;
                            if (that.app.view === "workspace") {
                                dragData.dy = d3.event.sourceEvent.clientY - that.tree.y;
                            } else {
                                dragData.dy = d3.event.sourceEvent.clientY - that.tree.y;
                            }
                        } else {
                            dragData.width = that.data.width;
                            dragData.height = that.data.height;
                            dragData.dx = d3.event.sourceEvent.clientX - that.data.x;
                            dragData.dy = d3.event.sourceEvent.clientY - that.data.y;                            
                        }
                        that.app.mediator.publish("module:dragstart");
                    }).on("dragend", function(){
                        that.dragging = false;
                        /* subscriber: PathView */
                        that.app.mediator.publish("module:dragend", that);

                        // rearrange roots order once model coordinates are set
                        if (that.app.view === "workspace") {
                            that.app.roots.sort();                            
                        } else {
                            that.app.patternRoots.sort();
                        }

                    }).on("drag", function() {

                        that.dragging = true;
                        var x, y,
                            svg = "svg#" + that.app.view,
                            svgWidth = $(svg).width(),
                            svgHeight = $(svg).height();

                            x = d3.event.sourceEvent.clientX - dragData.dx;
                            y = d3.event.sourceEvent.clientY - dragData.dy;
                            if (that.tree) {
                                if (x < dragData.width / 2) {

                                    x = dragData.width / 2;
                                } else if (x + (dragData.width / 2) > svgWidth) {
                                    x = svgWidth - (dragData.width / 2);
                                }
                            } else {
                                if (x < 0) {
                                    x = 0;
                                } else if (x + dragData.width > svgWidth) {
                                    x = svgWidth - dragData.width;
                                }
                            }
                            

                            if (y < 0) {
                                y = 0;
                            } else if (y + dragData.height > svgHeight) {
                                y = svgHeight - dragData.height;
                            }
                        that.position(x, y, 0, true);
                        if (that.tree) {
                            /* subscriber: PathView */
                            that.app.mediator.publish("module:drag", d3.event.sourceEvent, that);
                        }
                    });

            return drag;
        },
        showEditor: function() {

            if (this.editor.isHidden()) {
                this.editor.open();

            } else {
                this.editor.close();
            }

        },
        /* helper functions */
        position: function(x, y, duration, dnd) {
            if (this.tree && dnd) { // hack
                this.tree.d3.transition()
                    .duration(duration)
                    .attr("transform", "translate(" + x + "," + y + ")");
                this.tree.x = x;
                this.tree.y = y;
            } else {
                this.d3.transition()
                    .duration(duration)
                    .attr("transform", "translate(" + x + "," + y + ")");
                this.data.x = this.model.attributes.x = x;
                this.data.y = this.model.attributes.y = y;
            }
        },
        highlight: function() {
            if (this.tree) {
                this.tree.highlight();
            } else {
                this.rect.attr("fill", this.app.colors.highlightColor);
            }
        },
        unhighlight: function() {
            if (this.tree) {
                this.tree.unhighlight();
            } else {
                this.rect.attr("fill", this.app.colors.fill);
            }
        },
        showActions: function() {
            this.imageEdit.style("display", "inline");
            this.imageRemove.style("display", "inline");
        },
        hideActions: function() {
            this.imageEdit.style("display", "none");
            this.imageRemove.style("display", "none");
        },
        removeModule: function() {

            this.model.attributes.modules.each(function(childModel) {
                childModel.attributes.view.removeModule();
            });

            this.d3.remove();
            this.editor.remove();
            if (this.tree && !this.isRoot) {
                this.pathView.remove(); // this.pathView is the path where this module is the target
            }
        }
    });

});
