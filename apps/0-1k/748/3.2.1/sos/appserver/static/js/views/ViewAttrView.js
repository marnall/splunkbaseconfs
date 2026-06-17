define([
	"jquery",
	"underscore",
	"backbone",
	"bootstrap.modal",
	"text!app/templates/ViewAttrModal.html",
	"text!app/templates/AddAttribute.html"
], function(
	$,
	_,
	Backbone,
	modal,
	Template,
	AddAttributeTemplate
) {
	return Backbone.View.extend({
		className: "viewAttrModal",
		initialize: function() {
			this.app = this.options.app;
			this.model.on("change:view_name", this.render, this);
		},
		render: function() {
			this.$el.html(_.template(Template, this.model.attributes));

			this.$(".addAttrContainer").append(_.template(AddAttributeTemplate, {name: "", val: ""}));
			return this;
		},
		events: {
			"keydown input": "keyDown",
			"change input": "getInputValue"
		},
		keyDown: function(e) {
			var charCode = e.which || e.keyCode;
			if (charCode == 13) {
				this.getInputValue(e);
				return false;
			}
		},
		getInputValue: function(e) {
			var key = $(e.target).attr("name"),
				val = $(e.target).val(),
				$keyInput = this.$("input.control-label");

			if ($(e.target).hasClass("attribute")) {
				if ($keyInput.val()) {
					// entered a custom attribute
					key = $keyInput.val();
					this.$(".attrs").append(_.template(AddAttributeTemplate, {name: key, val: val}));
					this.clearAddAttr();
				}
				if (key == "label") {
					this.model.attributes[key] = val;
				} else {
					this.model.attributes.attrs[key] = val;
				}
			}
			
		},
		open: function() {
			this.$('.modal').modal("show");
		},
		close: function() {
			this.$('.modal').modal("hide");
		},
		clearAddAttr: function() {
			this.$(".addAttr input").val("");
		}
	});
});