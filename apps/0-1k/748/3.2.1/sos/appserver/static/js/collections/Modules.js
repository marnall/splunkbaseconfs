define([
	"jquery",
	"underscore",
	"backbone",
	"app/models/Module"
], function(
	$,
	_,
	Backbone,
	Module
) {
	return Backbone.Collection.extend({
		model: Module,
		comparator: function(modelA, modelB) {
			var ax = modelA.getX(), ay = modelA.getY(),
				aw = modelA.get('width'), ah = modelA.get('height'),
				bx = modelB.getX(), by = modelB.getY(),
				bw = modelB.get('width'), bh = modelB.get('height');

			if (Math.abs(ay - by) > (ah / 2.0 + bh / 2.0)) {
				return (ay < by) ? -1 : 1;
			} else {
				if (ax != bx) {
					return (ax < bx) ? -1 : 1;
				} else {
					return 0;
				}
			}
		},
		highlight: function() {
			this.each(function(model) {
				model.get("view").highlight();
			});
		},
		unhighlight: function() {
			this.each(function(model) {
				model.get("view").unhighlight();
			});
		},
		removeModules: function() {
			this.each(function(model) {
				model.get("view").remove();
			});
		},
		toSplunk: function() {
			var moduleArray = [];
			this.each(function(model) {
				moduleArray.push(model.toSplunk());
			});
			return moduleArray;
		},
		toPatterns: function() {
			var moduleArray = [];
			this.each(function(model) {
				moduleArray.push(model.toPatterns());
			});
			return moduleArray;	
		}
	});
});