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
			this.attributes.view_name = this.attributes.view_name || "";
			this.attributes.targetApp = this.attributes.targetApp || "";
			this.attributes.label = this.attributes.label || "";
			this.attributes.attrs = this.attributes.attrs || {};
		},
		clear: function() {
			this.attributes.view_name = "";
			this.attributes.targetApp = "";
			this.attributes.label = "";
			this.attributes.attrs = {};

			this.attributes.modules = this.attributes.modules.reset();
		},
		toSplunk: function() {
			var json = {};
			json.label = this.attributes.label || "";
			if (this.attributes.modules.length > 0) {
				json.module = this.attributes.modules.toSplunk();
			}

			$.each(this.attributes.attrs, function(key, val) {
				if (!key.match(/^_[^_].*/)) {
                    key = "_" + key;
                }
				json[key] = val;
			});	

			return json;
		}
	});
});