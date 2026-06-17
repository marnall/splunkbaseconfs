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
			this.attributes.name = this.attributes.name || "";
			this.attributes.data = this.attributes.data || [];
			// this.attributes.modules = this.attributes.modules || new Modules(this.attributes.data);

		},
		toPatterns: function() {
			var json = {};
			json.name = this.attributes.name;
			json.data = this.attributes.data;

			return json;
		}
	});
});