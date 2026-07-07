require(['jquery',
    'underscore',
    'splunkjs/mvc',
    'backbone',
    'splunkjs/mvc/simpleform/input/base',
    'splunkjs/mvc/simplexml/element/base',
    'splunkjs/mvc/simplexml/ready!'],function($,
                                              _,
                                              mvc,
                                              backbone,
                                              input,
                                              element){
        var tokenModel = new backbone.Model();
        var eventHandler = function(e) {
            if (typeof e.preventDefault === "function") {
                e.preventDefault();
            }
            tokenModel.clear({silent: true});
            tokenModel.set(e.data);
        };
        _(mvc.Components.toJSON()).each(function(component) {
            console.log(component);
            if (component instanceof input) {
                console.log('input component');
                component.on('valueChange', eventHandler);
            } else if (component instanceof element) {
                console.log('input component');
                component.on('drilldown', eventHandler);
                component.on('selection', eventHandler);
            }
        });

        var TokenEventView = backbone.View.extend({
            className: 'show-tokens',
            initialize: function() {
                this.listenTo(this.model, 'change', this.render);
            },
            render: function() {
                this.$el.html(this.template);

                var tbody = this.$('tbody');
                _(this.model.toJSON()).each(function(value, token) {
                    var tr = $('<tr></tr>');
                    $('<td class="token-name"></td>').text('$' + token + '$').appendTo(tr);
                    $('<td class="token-value"></td>').text(value).appendTo(tr);
                    tr.appendTo(tbody);
                });

                return this;
            },
            template: '<h3>Event Token Info</h3>' +
                '<table class="table table-striped table-chrome table-hover">' +
                '<thead>' +
                '<tr>' +
                '   <th>Token</th>' +
                '   <th>Value</th>' +
                '</tr>' +
                '</thead>' +
                '<tbody></tbody>' +
                '</table>'
        });

        var ct = $('#show-event-tokens');
        if (!ct.length) {
            ct = $('<div id="show-event-tokens"></div>').insertAfter($('.dashboard-body'));
        }
        window.eventTokenDebug = new TokenEventView({ el: ct, model: tokenModel }).render();

    }
);