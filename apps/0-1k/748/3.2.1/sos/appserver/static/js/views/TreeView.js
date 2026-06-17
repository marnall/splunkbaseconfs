define([
    "jquery",
    "underscore",
    "backbone",
    "d3",
    "bootstrap.modal",
    "text!app/templates/SaveGroupModal.html",
    "app/views/PathView"
], function(
    $,
    _,
    Backbone,
    d3,
    modal,
    SaveGroupModalTemplate,
    PathView
) {
    return Backbone.View.extend({
        initialize: function() {
            
            this.app = this.options.app;
            this.root = this.options.root; // ModuleView of the tree's root
            this.isMinimized = false;

            this.d3 = d3.select(this.el);
            this.tree = d3.layout.tree()
                .children(function(d) {
                    return d.modules;
                });
            this.diagonal = d3.svg.diagonal()
                .source(function(d) {
                    var x = d.source.x,
                        y = d.source.y,
                        width = d.source.width,
                        height = d.source.height;
                    
                    return {"x": x + (width / 2), "y": y + height};
                })
                .target(function(d) {
                    var x = d.target.x,
                        y = d.target.y,
                        width = d.target.width;
                    
                    return {"x": x + (width/2), "y": y};
                });
           
        },
        render: function(x, y) {

            if (!x && !y) {
                x = this.root.model.attributes.x;
                y = this.root.model.attributes.y;
            }

            this.x = x;
            this.y = y;

            var width = this.root.model.attributes.width,
                height = this.root.model.attributes.height,
                textW = this.root.model.attributes.textW,
                text = this.root.model.attributes.text;
            this.d3.attr("transform", "translate(" + x + "," + y + ")");

            if (this.app.view === "workspace") {
                this.min = this.d3.append("image")
                    .attr("class", "min")
                    .attr("x", width / 2 - 25).attr("y", -25)
                    .attr("width", 15).attr("height", 15)
                    .attr("xlink:href", "/static/app/splunk_app_shared_components/img/min.png")
                    .on("click", _.bind(this.minimize, this));
                this.minimized = this.d3.append("g")
                    .attr("class", "minimized")
                    .attr("transform", "translate(" + (-textW / 2) + ",0)")
                    .style("display", "none");
                this.minimized.append("rect")
                    .attr("class", "minimized")
                    .attr("x", 0).attr("y", 0)
                    .attr("stroke", "#000").attr("fill", "white")
                    .attr("stroke-dasharray", "5,5")
                    .attr("width", textW + 10)
                    .attr("height", height)
                    .call(this.root.drag());
                this.minimized.append("text")
                    .attr("class", "minimized")
                    .attr("x", 5).attr("y", (height / 2) + 5)
                    .attr("width", textW).attr("height", height)
                    .call(this.root.drag())
                    .text(text);
            }
        },
        /* events */
        minimize: function() {
            if (this.isMinimized) {
                this.$(".minimized").hide();
                this.$(":not(.minimized)").show();
                this.$("image:not(.min)").hide();

                this.isMinimized = false;
            } else {
                this.$(":not(.minimized)").hide();
                this.$(".minimized").show();
                this.$(".min").show();
                this.$(".group").show();

                this.isMinimized = true;
            }

        },
        /* util functions */
        update: function() {
            this.data = this.root.model.toJSON(true);
            var nodes = this.tree.nodes(this.data),
                links = this.tree.links(nodes),
                thisTree = this;
            
            this.position(nodes);
            this.tree.size([this.width, this.height]);

            // add, update, or remove paths
            var paths = this.d3.selectAll("path.link"),
                path, d, pathLink;
            if (links.length >= paths[0].length) {
                _.each(links, function(link) {
                    path = paths.filter(function(d) {
                        return link.target.view.model.id === d.target.view.model.id
                            && link.source.view.model.id === d.source.view.model.id;
                    });

                    if (path[0].length > 0) {
                        d = path.datum();
                        d.source.x = link.source.x;
                        d.source.y = link.source.y;
                        d.target.x = link.target.x;
                        d.target.y = link.target.y;
                    } else {
                        path = thisTree.d3.insert("g", ".module")
                            .attr("class", "link");
                        path.append("path")
                            .datum(link).attr("class", "link")
                            .attr("fill", "none")
                            .attr("stroke", thisTree.app.colors.disableColor);
                        var pathView = new PathView({el: path[0], app: thisTree.app,
                            source: link.source.view, target: link.target.view,
                            view: thisTree.app.view});
                        link.target.view.pathView = pathView;
                    }
                });
            } else {
                paths.each(function(d) {
                    var that = this;
                    path = undefined;
                    pathLink = undefined;
                    _.each(links, function(link) {
                        if (link.target.view.model.id === d.target.view.model.id
                            && link.source.view.model.id === d.source.view.model.id) {
                            path = that;
                            pathLink = link;
                        }
                    });
                    if (path) {
                        d.source.x = pathLink.source.x;
                        d.source.y = pathLink.source.y;
                        d.target.x = pathLink.target.x;
                        d.target.y = pathLink.target.y;
                    } else {
                        d3.select(this).remove();
                    }
                });
            }

            this.d3.selectAll("path.link").transition()
                .duration(this.app.duration)
                .attr("d", this.diagonal);

            // update nodes
            _.each(nodes, function(node, i) {
                thisTree.$el.append(node.view.el);
                node.view.addToTree(thisTree, node.x, node.y, thisTree.app.duration);
            });

        },
        position: function(nodes) {
            var maxDepth = d3.max(nodes, function(d) {return d.depth;}) + 1,
                maxWidth = 0,
                y = 75,
                depth;
            
            for (depth = 0; depth < maxDepth; depth += 1) {
                var children = _.filter(nodes, function(node) {
                    return node.depth === depth;
                }),
                width = _.reduce(children, function(memo, child) {
                    return memo + child.expandedWidth;
                }, 0),
                space = 10,
                half = (width + (children.length - 1) * space) / 2, // how much x should be shifted by
                x = 0;
                    
                maxWidth = Math.max(half * 2, maxWidth);
                _.each(children, function(child) {
                    child.x = x - half;
                    child.y = y * depth;
                    x = x + child.expandedWidth + space;
                });
            }
            
            this.width = maxWidth;
            this.height = y * (maxDepth - 1) + 26;
        },
        highlight: function() {
            this.$("rect").attr("fill", this.app.colors.highlightColor);
        },
        unhighlight: function() {
            this.$("rect").attr("fill", this.app.colors.fill);
        },
        show: function() {
            this.$el.show();
        },
        hide: function() {
            this.$el.hide();
        },
        removeIfEmpty: function() {
            if (this.d3.selectAll("g.module")[0].length === 0) {
                this.removeTree();
            }
        },
        removeTree: function() {
            this.d3.remove();
        }
        
    });
});
