define([
    'jquery',
    'underscore',
    'backbone',
    'd3',
    'app/views/ModuleView'
], function(
    $,
    _,
    Backbone,
    d3,
    ModuleView
) {
    return Backbone.View.extend({
        initialize: function() {
            this.app = this.options.app;
            this.view = this.options.view;
            this.source = this.options.source;
            this.target = this.options.target;

            this.g = d3.select(this.el);
            this.d3 = this.g.select("path");
            this.removePath = this.g.append("image", this.el)
                .attr("class", "removePath")
                .attr("width", this.app.moduleSettings.imageSize)
                .attr("height", this.app.moduleSettings.imageSize)
                .attr("x", 0)
                .attr("y", 0)
                .attr("xlink:href", "/static/app/splunk_app_shared_components/img/remove.gif")
                .style("display", "none")
                .on("click", _.bind(this.click, this));

            var that = this;
            this.app.mediator.subscribe("module:dragstart", function() {
                that.x1 = that.source.data.x + (that.source.data.width / 2) + that.source.tree.x;
                that.x2 = that.target.data.x + (that.target.data.width / 2) + that.target.tree.x;
                that.y1 = that.source.data.y + that.source.data.height + that.source.tree.y;
                that.y2 = that.target.data.y + that.source.tree.y;
                if (that.x1 === that.x2) {
                    that.x1 -= 5;
                    that.x2 += 5;
                }
            });
            this.app.mediator.subscribe("module:drag", function(e, moduleView) {
                var x = moduleView.data.x + (moduleView.data.width / 2),
                    y = moduleView.data.y + (moduleView.data.height / 2);
                if (((that.x1 > x && x > that.x2) 
                    || (that.x2 > x && x > that.x1))
                    && (that.y2 > y && y > that.y1)) {
                    that.mouseenter(e);
                } else {
                    that.mouseleave();
                }
            });
            this.app.mediator.subscribe("module:dragend", function(moduleView) {
                var x = moduleView.data.x + (moduleView.data.width / 2),
                    y = moduleView.data.y + (moduleView.data.height / 2);
                if (((that.x1 > x && x > that.x2) 
                    || (that.x2 > x && x > that.x1))
                    && (that.y2 > y && y > that.y1)
                    && that.view == that.app.view) {
                    that.insert(moduleView);
                }
                that.mouseleave();
            });
        },
        events: {
            "mouseenter": "mouseenter",
            "mouseleave": "mouseleave",
            "click": "click"
        },
        mouseenter: function(e) {
            var svg = "svg#" + this.app.view,
                svgLeft = parseInt($(svg).css("left"), 10),
                svgTop = parseInt($(svg).css("top"), 10),
                x = $(window).scrollLeft() + e.clientX - svgLeft - this.source.tree.x,
                y = $(window).scrollTop() + e.clientY - svgTop - this.source.tree.y;
            this.removePath.attr("x", x)
                .attr("y", y)
                .style("display", "inline");
            this.d3.classed("hover", true);
        },
        mouseleave: function() {
            this.removePath.style("display", "none");
            this.d3.classed("hover", false);
        },
        click: function() {

            this.remove();
            this.target.model.remove();

            var x = this.target.tree.x + this.target.data.x,
                y = this.target.tree.y + this.target.data.y;
            if (this.target.model.hasChildren()) {

                x += (this.target.data.width / 2);
                this.target.isRoot = true;
                this.app.mediator.publish("path:createTree", this.target, x, y);
            } else {
                this.target.position(x, y, this.app.transition);
                this.target.isRoot = true;
                this.target.tree = false;
                this.app.mediator.publish("path:addExistingModule", this.target);
            }

            x = this.source.tree.x + this.source.data.x;
            y = this.source.tree.y + this.source.data.y;   
            if (this.source.isRoot && !this.source.model.hasChildren()) {

                this.source.position(x, y, this.app.transition);
                this.app.mediator.publish("path:addExistingModule", this.source);
                this.source.tree.removeTree();
                this.source.tree = false;
            } else {
                this.source.tree.update();
            }
        },
        /* module: module to be inserted between source and target modules */
        insert: function(moduleView) {
            var module = moduleView.model;

            /* 
            take the source model of this path, and replace the original
            target with the new module as the child.
            */
            this.source.model.replace(this.target.model, module);
            module.addParentCollection(this.source.model.get("modules"));
            /* Subscribers: WorkspaceView, PatternView */
            this.app.mediator.publish("module:removeFromRoots", module);

            /*
            take the new module, and add the original target as its child.
            also add this path's new target as the new module.
            */
            module.addChild(this.target.model);
            this.target.model.addParentCollection(module.get("modules"));
            this.target = moduleView;

            this.d3.datum({source: this.source.model.toJSON(true), 
                target: this.target.model.toJSON(true)});
            this.source.tree.update();

            moduleView.pathView = this;
            moduleView.isRoot = false;
            moduleView.tree = this.source.tree;
        },
        /* helper functions */
        remove: function() {
            this.g.remove();
        }
    });
});