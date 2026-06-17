define([
	"jquery",
	"underscore",
	"backbone",
	"text!app/templates/Alert.html"
], function(
	$,
	_,
	Backbone,
	Template
) {
	return Backbone.View.extend({
		className: "alert",
		initialize: function() {
			this.app = this.options.app;
			this.message = this.options.message;
			this.view = this.options.view;
			this.closeable = this.options.closeable;
			this.type = this.options.type;
		},
		render: function() {
			this.$el.append(_.template(Template, {dismiss: this.closeable,
				message: this.message}));

			if (this.type === "success") {
				this.$el.addClass("alert-success");

				// also make it disappear after a second
				var that = this;
				window.setTimeout(function() {
					that.clicked();
				}, 2000);
			} else if (this.type === "error") {
				this.$el.addClass("alert-error");
			}
			return this;
		},
		// fadeIn: function() {
		// 	this.$el.fadeIn("fast");
		// },
		// fadeOut: function(callback) {
		// 	this.$el.fadeOut("slow", function() {
		// 		callback();
		// 	});
		// },
		events: {
			"click": "clicked"
		},
		clicked: function() {
			if (this.view) {
				this.view.clickedNotification();				
			} else {
				this.remove();
			}

		},
		remove: function() {
			this.$el.fadeOut("slow", function() {
				$(this).remove(); 
			});
            this.app.mediator.publish("remove:notifications", this);
		}
	});
});