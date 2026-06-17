define([
	'jquery',
	'underscore',
	'backbone',
	'bootstrap.modal',
	'text!app/templates/ModuleInfo.html'
], function(
	$,
	_,
	Backbone,
	modal,
	Template
) {
	return Backbone.View.extend({
		className: "ModuleInfo modal hide fade",
		initialize: function() {
			this.app = this.options.app;
			this.data = this.options.data;
		},
		render: function() {
			this.$el.html(_.template(Template, this.data));
			// this.hide();
			return this;
		},
		isHidden: function() {
			return this.$el.is(":hidden");
		},
		show: function() {
			this.$el.modal("show");
		},
		hide: function() {
			this.$el.modal("hide");
		}
	});
});