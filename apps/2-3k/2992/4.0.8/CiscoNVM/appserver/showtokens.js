require(['splunkjs/mvc/simplexml/ready!', 'css!../app/simplexml/showtokens.css'], function() {
    var _ = require('underscore');
    var $ = require('jquery');
    var Backbone = require('backbone');
    var mvc = require('splunkjs/mvc');

    var defaultTokenModel = mvc.Components.get('default');
    var submittedTokenModel = mvc.Components.get('submitted');
    var urlTokenModel = mvc.Components.get('url');
    var models = [defaultTokenModel, submittedTokenModel, urlTokenModel];

    var TokenDebugView = Backbone.View.extend({
        className: 'show-tokens',
        initialize: function() {
            this.model = new Backbone.Model({ includeFormTokens: false });
            if ('localStorage' in window && window.localStorage) {
                try {
                    var STORAGE_KEY = 'splunk-show-tokens';
                    var localSettings = window.localStorage.getItem(STORAGE_KEY);
                    if (localSettings) {
                        this.model.set(JSON.parse(localSettings));
                    }
                    this.model.on('change', function(model) {
                        try {
                            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(model.toJSON()));
                        } catch (e) {
                        }
                    });
                } catch (e) {
                }
            }
            this.listenTo(this.model, 'change', this.render);
            this.listenTo(defaultTokenModel, 'change', this.render);
            this.listenTo(submittedTokenModel, 'change', this.render);
            this.listenTo(urlTokenModel, 'change', this.render);
        },
        events: {
            'click .checkbox a': function(e) {
                e.preventDefault();
                this.model.set('includeFormTokens', !this.model.get('includeFormTokens'));
            }
        },
        render: function() {
            this.$el.addClass('show-tokens');
            if (this.$el.is(':empty')) {
                this.$el.html(this.template);
            }

            var includeFormTokens = this.model.get('includeFormTokens');
            this.$('.checkbox>a>i')[includeFormTokens ? 'show' : 'hide']();

            var tbody = this.$('tbody');
            tbody.empty();

            var keys = _.union.apply(_, _(models).invoke('keys'));

            if (!includeFormTokens) {
                keys = _(keys).filter(function(k) { return k.indexOf('form.') !== 0; });
            }

            keys.sort();

            _(keys).each(function(token) {
                var tr = $('<tr></tr>');
                $('<td class="token-name"></td>').text('$' + token + '$').appendTo(tr);
                _(models).each(function(ns) {
                    var td = $('<td class="token-value"></td>').appendTo(tr);
                    var val = ns.get(token);
                    if (val === undefined) {
                        td.addClass('undefined').text('undefined');
                    } else {
                        if (_.isString(val)) {
                            td.text(val);
                        } else {
                            $('<code title="Non-string value"></code>').text(JSON.stringify(val)).appendTo(td);
                        }
                    }
                });
                tr.appendTo(tbody);
            });

            return this;
        },
        template: '<div class="form-switch">' +
            '<label class="checkbox">' +
            '<a href="#" class="btn"><i class="icon-check" style="display:none"></i></a>' +
            ' Show <code>form.</code> tokens' +
            '</label>' +
            '</div>' +
            '<h3>Token Debug Info</h3>' +
            '<table class="table table-striped table-chrome table-hover">' +
            '<thead>' +
            '<tr>' +
            '   <th>Token</th>' +
            '   <th>Default</th>' +
            '   <th>Submitted</th>' +
            '   <th>URL</th>' +
            '</tr>' +
            '</thead>' +
            '<tbody></tbody>' +
            '</table>'
    });

    var ct = $('#show-tokens');
    if (!ct.length) {
        ct = $('<div id="show-tokens"></div>').insertAfter($('.dashboard-body'));
    }
    window.tokenDebug = new TokenDebugView({ el: ct }).render();
});