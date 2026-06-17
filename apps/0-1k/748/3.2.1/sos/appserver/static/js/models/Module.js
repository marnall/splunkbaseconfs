define([
    "jquery",
    "underscore",
    "backbone",
    "app/collections/Modules"
], function(
    $,
    _,
    Backbone,
    Modules
) {
	return Backbone.Model.extend({
        initialize: function() {
            this.attributes.modules = new Modules();
            this.attributes.params = {};
            this.attributes.attrs = {};
            this.id = this.attributes.id = this.cid + this.attributes.text;
        },
        hasChildren: function() {
            return this.attributes.modules.length > 0;
        },
        addChild: function(child) {
            this.attributes.modules.add(child);
        },
        addParentCollection: function(parentCollection) {
            this.attributes.parentCollection = parentCollection;
        },
        addGroup: function(group) {
            /* when the module belongs to the group */
            this.attributes.group = group;
        },
        replace: function(firstModel, secondModel) {
            var i = this.attributes.modules.indexOf(firstModel);
            this.attributes.modules.add(secondModel, {at: i});
            this.attributes.modules.remove(firstModel);
        },
        remove: function() {
            if (this.attributes.parentCollection) {
                this.attributes.parentCollection.remove(this);
            }
        },
        getX: function() {
            return (this.hasChildren()) ? this.get('view').tree.x : this.get('x');
        },
        getY: function() {
            return (this.hasChildren()) ? this.get('view').tree.y : this.get('y');
        },
        toJSON: function(needView) {
            var data = {},
                relevant = ["text", "textW", "textH", "width", "expandedWidth", "height", "x", "y"];
            
            if (needView) {
                relevant.push("view");
            }

            $.each(this.attributes, function(key, val) {
                if (key === "modules") {
                    data[key] = val.toJSON(needView);
                } else if ($.inArray(key, relevant) >= 0){
                    data[key] = val;
                }
            });
            
            return data;
        },
        toSplunk: function() {
            var json = {};

            json._name = this.attributes.text;
            if (json._name === "paginator") {json._name = "Paginator"; }
            if (!_.isEmpty(this.attributes.params)) {
                json.param = this.fromParams();
            }
            if (!_.isEmpty(this.attributes.attrs)) {
                this.fromAttrs(json);
            }
            if (!this.attributes.modules.isEmpty()) {
                json.module = this.attributes.modules.toSplunk();
                json.module_asArray = json.module;
            }
            return json;
        },
        toPatterns: function() {
            var json = {};

            json._name = this.attributes.text;
            if (json._name === "paginator") {json._name = "Paginator"; }
            json.modules = this.attributes.modules.toPatterns();
            json.module_asArray = json.modules;
            json.params = this.attributes.params;
            json.attrs = this.attributes.attrs;

            return json;
        },
        /* from splunk params *to* Model compatible params */
        toParams: function(moduleObject) {
            var params = {},
                self = this,
                dest;

            if (moduleObject.param_asArray) {
                $.each(moduleObject.param_asArray, function(i, param) {
                    
                    if (param.list_asArray) {
                        params[param._name] = self.toListParam(param);
                    } else if(_.isObject(param.param)) {
                        params[param._name] = self.toDictParam(param);
                    } else if (_.isString(param.__text)) {
                        params[param._name] = param.__text;
                    }
                });
            } else if (moduleObject.params) {
                params = moduleObject.params;
            }
            return params;
        },
        toAttrs: function(moduleObject) {
            var attrs = {};
            if (moduleObject.attrs) {
                attrs = moduleObject.attrs;
            } else {
                $.each(moduleObject, function(k, v) {

                    if (k.match(/^_[^_].*/) && k !== "_name") {
                        attrs[k] = v;
                    }
                });
            }
            
            return attrs;
        },
        toDictParam: function(data) {
            var that = this,
                dict = {};
            _.each(data.param_asArray, function(child) {
                if (child.param) {
                    dict[child._name] = that.toDictParam(child);
                } else if (child.list) {
                    dict[child._name] = that.toListParam(child);
                } else if (_.isString(child.__text)) {
                    dict[child._name] = child.__text;
                }
            });
            return dict;
        },
        toListParam: function(data) {
            var that = this,
                list = [];
            _.each(data.list_asArray, function(child) {
                if (child.param) {
                    list.push(that.toDictParam(child));
                } else if (child.list) {
                    list.push(that.toListParam(child));
                } else if (_.isString(child.__text)) {
                    // i hope this is right
                    list.push(child.__text);
                }
            });
            return list;
        },
        /* to splunk params *from* Model compatible params */
        fromParams: function() {
            var paramArray = [],
                that = this;
            _.each(this.attributes.params, function(v, k) {
                if (_.isArray(v)) {
                    paramArray.push({_name: k, list: that.fromListParam(v)});
                } else if (_.isObject(v)) {
                    paramArray.push({_name: k, param: that.fromDictParam(v)});
                } else if (_.isString(v)) {
                    paramArray.push({_name: k, __text: v});
                }
            });
            return paramArray;
        },
        fromAttrs: function(json) {
            $.each(this.attributes.attrs, function(k, v) {
                if (!k.match(/^_[^_].*/)) {
                    k = "_" + k;
                }
                json[k] = v;
            });
        },
        fromDictParam: function(data){
            var list = [],
                that = this;
            _.each(data, function(v, k) {
                if (_.isArray(v)) {
                    list.push({_name: k, list: that.fromListParam(v)});
                    // dict._name = k;
                    // dict.list = that.fromListParam(v);
                } else if (_.isObject(v)) {
                    list.push({_name: k, param: that.fromDictParam(v)});
                    // dict._name = k;
                    // dict.param = that.fromDictParam(v);
                } else if (_.isString(v)) {
                    list.push({_name: k, __text: v});
                    // dict._name = k;
                    // dict.__text = v;
                }
            });
            return list;
        },
        fromListParam: function(data){
            var list = [],
                that = this;
            _.each(data, function(child) {
                if (_.isObject(child)) {
                    list.push({param: that.fromDictParam(child)});
                } else if (_.isArray(child)) {
                    list.push({list: that.fromListParam(child)});
                } else if (_.isString(child)) {
                    list.push({__text: child});
                }
            });
            return list;
        }
    });
});
