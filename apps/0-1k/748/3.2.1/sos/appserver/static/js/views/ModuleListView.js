define([
    'jquery',
    'underscore',
    'backbone',
    "text!app/templates/ModuleList.html",
    "app/views/ModuleView",
    "app/views/ModuleEditorView",
    "app/models/Module"
], function(
    $,
    _,
    Backbone,
    Template,
    ModuleView,
    ModuleEditorView,
    Module
) {
    return Backbone.View.extend({
        className: "moduleListItem",
        initialize: function() {
            this.app = this.options.app;
            this.data = this.options.data;
            this.infoView = this.options.info;
        },
        render: function() {
            this.$el.html(_.template(Template, this.data));

            if (this.data['blacklisted'] === 'true') {
                this.$el.addClass('blacklisted');
            }
            d3.selectAll(this.$(".moduleNameText"))
                .call(this.drag());

            return this;
        },
        drag: function() {
            var that = this,
                view,
                dragData = {},
                notContextClick = false,
                drag = d3.behavior.drag()
                    .on("dragstart", function() {
                        // ignore context clicks
                        if (that.notContextClick(d3.event.sourceEvent)) {
                            notContextClick = true; 
                            var x = d3.event.sourceEvent.clientX,
                                y = d3.event.sourceEvent.clientY,
                                svg = "svg#" + that.app.view,
                                svgLeft = parseInt($(svg).css("left"), 10),
                                svgTop = parseInt($(svg).css("top"), 10),
                                offset = $(d3.event.sourceEvent.target).offset();
    
                            dragData.dx = x - offset.left;
                            dragData.dy = y - offset.top;
                            x -= svgLeft + dragData.dx;
                            y -= svgTop + dragData.dy;
                            var data = that.addModule(x, y);
    
                            dragData.width = data.width;
                            dragData.height = data.height;
    
                            that.app.mediator.publish("module:dragstart");
                        } 
                    }).on("dragend", function(){
                        // ignore context clicks
                        //if (that.notContextClick(d3.event.sourceEvent)) {
                        if (notContextClick) {
                            that.app.mediator.publish("module:dragend", view);
                            view.dragging = false;
                            view = false;
                            // rearrange roots order once model coordinates are set
                            if (that.app.view === "workspace") {
                                that.app.roots.sort();                            
                            } else {
                                that.app.patternRoots.sort();
                            }
                        }
                        
                    }).on("drag", function() {
                        // ignore context clicks
                        if (notContextClick) {
                            var x = d3.event.sourceEvent.clientX,
                                y = d3.event.sourceEvent.clientY,
                                svg = "svg#" + that.app.view,
                                svgLeft = parseInt($(svg).css("left"), 10),
                                svgTop = parseInt($(svg).css("top"), 10),
                                svgWidth = $(svg).width(),
                                svgHeight = $(svg).height();

                            x -= svgLeft + dragData.dx;
                            y -= svgTop + dragData.dy;

                            if (view) {
                                view.dragging = true;
                                if (x < 0) {
                                    x = 0;
                                } else if (x + dragData.width > svgWidth) {
                                    x = svgWidth - dragData.width;
                                }
                                if (y < 0) {
                                    y = 0;
                                } else if (y + dragData.height > svgHeight) {
                                    y = svgHeight - dragData.height;
                                }
                                view.position(x, y, 0, true);
                                that.app.mediator.publish("module:drag", d3.event.sourceEvent, view);
                            }
                            view.position(x, y, 0, true);
                            that.app.mediator.publish("module:drag", d3.event.sourceEvent, view);
                        }
                    });

                this.app.mediator.subscribe("addModule:success", function(moduleView) {
                    view = moduleView;
                    
                });

            return drag;
        },
        events: {
            "click .moduleInfo": "toggleModuleInfo",
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
        notContextClick: function(sourceEvent) {
            console.log('sourceEvent', sourceEvent);
            if (sourceEvent.which !== 1) {
                return false;
            } else if (sourceEvent.ctrlKey === true) {
                return false;
            }
            return true;
        },
        toggleModuleInfo: function() {
            if (this.infoView.isHidden()) {
                this.infoView.show();
            } else {
                this.infoView.hide();
            }
        },
        /* workspace interactions */
        addModule: function(x, y) {
            
            var helper = this.addModuleHelper(x, y),
                data = helper.data,
                editor = helper.editor,
                model = helper.model;
            this.app.mediator.publish("modulelist:addModule", data, editor, model);
            this.app.mediator.publish("modulelist:addModuleEditor", editor);

            return data;
        },
        addModuleHelper: function(x, y) {
            var data = {},
                padding = this.app.moduleSettings.padding,
                imageSize = this.app.moduleSettings.imageSize,
                $temp;

            data.text = this.$(".moduleNameText").text();
            $temp = $("<span></span>").addClass("moduleName").text(data.text);
            $("#temp").append($temp);
            data.textW = $temp.width();
            data.textH = $temp.height();
            $temp.remove();

            data.width = data.textW + (2 * padding);
            data.expandedWidth = data.width + (2 * padding) + (2 * imageSize);
            data.height = data.textH + (2 * padding);
            if (x && y) {
                data.x = x;
                data.y = y;
            }

            var model = new Module(data),
                editor = new ModuleEditorView({app: this.app, data: this.data, model: model, info: this.infoView});
            return {data: data, model: model, editor: editor};
        }
    });
});
