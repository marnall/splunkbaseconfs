define([
	"jquery",
	"underscore",
	"backbone",
	"app/views/NotificationView"
], function(
	$,
	_,
	Backbone,
	NotificationView
) {
	return Backbone.View.extend({
		id: "notifications",
		initialize: function() {
			this.app = this.options.app;
			this.notifications = [];

			var that = this;
			this.app.mediator.subscribe("add:notifications", function(notification) {
				that.addNotification(notification);
			});
			this.app.mediator.subscribe("remove:notifications", function(notification) {
				that.removeNotification(notification);
			});
		},
		render: function() {
			return this;
		},
		addNotification: function(notification) {
			
			this.$el.prepend(notification.render().el);

			this.notifications.push(notification);
			this.order();
		},
		removeNotification: function(notification) {
			
			this.notifications = _.without(this.notifications, notification);
			this.order();

		},
		order: function() {
			var spacing = 10,
				y = 5,
				that = this;
			_.each(this.notifications, function(notification) {
				notification.$el.animate({"bottom": y});
				y += notification.$el.outerHeight() + spacing;
			});

			this.$el.css("height", y + spacing);
		},
		clear: function() {
			_.each(this.notifications, function(notification) {
				notification.remove();
			});
		}
	});
});