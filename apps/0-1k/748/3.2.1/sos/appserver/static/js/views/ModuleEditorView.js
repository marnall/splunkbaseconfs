define([
    "jquery",
    "underscore",
    "backbone",
    "bootstrap.tooltip",
    "app/views/DictEditorView",
    "bootstrap.modal",
    "text!app/templates/ModuleEditor.html",
    "text!app/templates/AddAttribute.html",
    "app/views/NotificationView"
], function(
    $,
    _,
    Backbone,
    tooltip,
    DictEditorView,
    modal,
    Template,
    AddAttributeTemplate,
    NotificationView
) {
    return Backbone.View.extend({
        className: "moduleEditor modal hide fade",
        initialize: function() {
            this.app = this.options.app;
            this.data = this.options.data;
            this.infoView = this.options.info;
            // temporarily store params and attrs
            this.prevParams = {};
            this.params = {};
            this.attrs = {};
            this.alerts = {};

        },
        render: function() {
            this.$el.html(_.template(Template, this.data));
            this.$el.attr("data-backdrop", "static");
            this.updateParams();
            this.updateAttrs();
            this.validateForm();

            this.model.on("change:params", this.updateParams, this);
            this.model.on("change:attrs", this.updateAttrs, this);
            this.$(".addAttrContainer").append(_.template(AddAttributeTemplate, {name: "", val: ""}));

            this.close();

            return this;
        },
        updateParams: function() {
            var params = this.model.get("params"),
                that = this,
                dictEditorView;
            $.each(params, function(k, v) {
                if (_.isObject(v) || _.isArray(v)) {
                    that.$(".input-append[name='" + k + "']").hide();
                    if (that.params[k]) {
                        that.params[k].clear();
                        that.params[k].setData(_.clone(v));
                        that.params[k].render();
                        
                    } else {
                        dictEditorView = new DictEditorView({app: that.app, name: k, data: _.clone(v)});
                        that.$(".list-dict-container[data-key='" + k + "']").html(dictEditorView.el);

                        that.params[k] = dictEditorView; 
                    }
                    
                } else if (_.isString(v)) {
                    that.$('input[name="' + k + '"], select[name="' + k + '"]').val(v);
                }
            });
        },
        updateAttrs: function() {
            var attrs = this.model.get("attrs"),
                that = this;
            $.each(attrs, function(k, v) {
                var elem = that.$('[name="' + k + '"]');
                if (elem.length > 0) {
                    elem.val(v);
                } else {
                    that.$(".attrs").append(_.template(AddAttributeTemplate, {name: k, val: v}));
                }
            });
        },
        events: {
            "shown": "shown",
            "keydown input": "keyDown",
            "change input": "getInputValue",
            "change select": "getSelectValue",
            "click .saveModuleEditor": "save",
            "click .cancelModuleEditor": "cancel",
            // "click .existingDictList": "existingDictList",
            "click .startDict": "newDict",
            "click .startList": "newList",
            "removeDictList .dictEditor": "removeDictList",
            "mouseover .triggerTooltip": "showTooltip"
        },
        shown: function() {

            /* calculate width */
            var left = this.$el.outerWidth() / -2;
            this.$el.css("margin-left", left);
        },
        newDict: function(e){
            this.createDictEditorView(e, {});
        },
        newList: function(e) {
            this.createDictEditorView(e, []);
        },
        removeDictList: function(e, name) {
            this.params[name] = "";
            this.$(".input-append[name='" + name + "']").show();
        },
        showTooltip: function(e) {
            $(e.target).tooltip("show");
        },
        /**/
        createDictEditorView: function(e, data) {
            var $target = $(e.target),
                $parent = $target.parent().next(".list-dict-container"),
                dictEditorView,
                key;

            $target.parent().hide();
            key = $parent.attr('data-key');

            dictEditorView = new DictEditorView({app: this.app, name: key, data: data});
            $parent.append(dictEditorView.el);
            if (this.params[key]) {
                this.prevParams[key] = _.clone(this.params[key]);
            }
            this.params[key] = dictEditorView;
        },
        keyDown: function(e) {
            var charCode = e.which || e.keyCode;
            if (charCode === 13) {
                this.getInputValue(e);
                return false;
            }
        },
        getInputValue: function(e) {
            var type = $(e.target).attr("class"),
                key = $(e.target).attr("name"),
                val = $(e.target).val(),
                id;

            if ($(e.target).hasClass("param")) {
                this.params[key] = val;
            } else if ($(e.target).hasClass("attribute")) {
                id = $(e.target).attr("id");
                $keyInput = this.$("input.control-label");

                if ($keyInput.val()) {
                    // entered a custom attribute
                    key = $keyInput.val();
                    this.$(".attrs").append(_.template(AddAttributeTemplate, {name: key, val: val}));
                    this.clearAddAttr();
                }
                this.attrs[key] = val;
            }

        },
        getSelectValue: function(e) {
            var type = $(e.target).attr("class"),
                key = $(e.target).attr("name"),
                val = $(e.target).val();

            if (val === "--") {
                this.params[key] = "";
            } else {
                this.params[key] = val;
            }
        },
        save: function() {
            var that = this;
            _.each(this.params, function(val, key) {
                if (val === "") {
                    delete that.model.attributes.params[key];
                } else if (_.isString(val)) {
                    that.model.attributes.params[key] = val;
                } else {
                    // must be a DictEditorView
                    that.model.attributes.params[key] = val.toJSON();
                    delete that.prevParams[key];
                }
            });

            _.each(this.attrs, function(val, key) {
                if (val === "") {
                    delete that.model.attributes.attrs[key];
                } else {
                    that.model.attributes.attrs[key] = val;
                }
            });

            this.close();
            this.validateForm();
        },
        cancel: function() {
            this.updateParams();
            this.updateAttrs();

            // take care of params/attrs that aren't set in model
            var params = _.difference(_.keys(this.params), _.keys(this.model.get("params"))),
                attrs = _.difference(_.keys(this.attrs), _.keys(this.model.get("attrs"))),
                that = this;
            _.each(params, function(k) {
                if (_.isString(that.params[k])) {
                    that.$('input[name="' + k + '"], select[name="' + k + '"]').val("");
                } else {
                    // else dictlist
                    that.params[k].clear();
                    // if the previous parameter was a string, refill the input with string
                    if (that.prevParams[k] && _.isString(that.prevParams[k])) {
                        that.$('input[name="' + k + '"], select[name="' + k + '"]').val(that.prevParams[k]);
                        that.params[k] = that.prevParams[k];
                        delete that.prevParams[k];
                    }
                }
            });
            _.each(attrs, function(k) {
                that.$('input[name="' + k + '"]').val("");
            });

            this.close();
        },
        open: function() {

            this.$el.modal({"backdrop": "static", "show": true});
            this.$el.trigger("show");
        },
        close: function() {
            this.$el.modal("hide");
            this.$el.trigger("hide");
        },
        remove: function() {
            _.each(this.alerts, function(val, key) {
                val.remove();
            });
            this.$el.remove();
        },
        isHidden: function() {
            return this.$el.is(":hidden");
        },
        validateForm: function() {
            var required, existing, missing, that, message, notification;

            required = _.chain(this.data.params)
                .values().filter(function(param) {
                    return param.required === "True";
                }).pluck("name").value();
            
            existing = _.keys(this.model.get("params"));
            missing = _.difference(required, existing);
            filled = _.difference(_.keys(this.alerts), missing);

            // if not missing anything, then validated
            that = this;
            _.each(missing, function(m) {
                if (!that.alerts[m]) {
                    message = "missing required parameter <strong>" + m + "</strong> in module <strong>" + that.model.get("text") + "</strong>";
                    notification = new NotificationView({app: that.app, view: that, message: message, closeable: false});
                    that.app.mediator.publish("add:notifications", notification);

                    that.alerts[m] = notification;
                    that.$('input[name="' + m + '"]').addClass("unfilledParam");
                }   
            });
            _.each(filled, function(f) {
                that.alerts[f].remove();
                that.$('input[name="' + f + '"]').removeClass("unfilledParam");
                delete that.alerts[f];
            });
        },
        clearAddAttr: function() {
            this.$(".addAttr input").val("");
        },
        clickedNotification: function() {
            this.open();
        }
    });
});
