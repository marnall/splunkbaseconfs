
Splunk.namespace("Module");
Splunk.Module.WindowsMonitoring_FTR = $.klass(Splunk.Module, {

    ADMIN_CONFIGURE: '<p class="popupText">The Splunk App for Windows has not been configured yet.</p><p class="popupText">Until it is configured, it may not work as expected.</p><p class="popupText">Please click \'Configure\' below to perform setup configuration.</p>',
    NON_ADMIN_CONFIGURE:  '<p class="popupText">The Splunk App for Windows has not been configured yet.</p><p class="popupText">  Until it is configured, it may not work as expected. Please notify your Splunk admin about this message.</p>',

    initialize: function($super, container) {
        $super(container);
        this.logger = Splunk.Logger.getLogger("windowsmonitoring_ftr.js");
        this.messenger = Splunk.Messenger.System.getInstance();
        this.popupDiv = $('.ftrPopup', this.container).get(0);
        this.redirectTo = this.getParam('configLink', 'setup');
        this.getResults();
    },

    renderResults: function(response, turbo) {
        if (!(response.is_windows || response.is_windows===false)) {
            if ((response.has_ignored && response.has_ignored===true) 
                    || (response.is_configured && response.is_configured===true)) {
                return true;
            } else if (response.is_admin && response.is_admin===true) {
                this.popupDiv.innerHTML = this.ADMIN_CONFIGURE; 
                this.popup = new Splunk.Popup(this.popupDiv, {
                    cloneFlag: false,
                    title: _("This App Needs Configuration"),
                    pclass: 'configPopup',
                    buttons: [
                         {
                             label: _("Ignore"),
                             type: "secondary",
                             callback: function(){
                                 this.setIgnored();
                                 return true;
                             }.bind(this)
                         },
                         {
                             label: _("Configure"),
                             type: "primary",
                             callback: function(){
                                 Splunk.util.redirect_to(['app', Splunk.util.getCurrentApp(),
                                                          this.redirectTo].join('/'));
                             }.bind(this)
                         }
                     ]
                 });
            } else {
                this.popupDiv.innerHTML = this.NON_ADMIN_CONFIGURE;
                this.popup = new Splunk.Popup(this.popupDiv, {
                    cloneFlag: false,
                    title: _("This App Needs Configuration"),
                    pclass: 'configPopup',
                    buttons: [
                        {
                            label: _("Continue"),
                            type: "primary",
                            callback: function(){
                                this.setIgnored();
                                return true;
                            }.bind(this)
                        }
                    ]
               });
            }
        }
    },

    setIgnored: function() {
        var params = this.getResultParams();
        if (!params.hasOwnProperty('client_app')) {
            params['client_app'] = Splunk.util.getCurrentApp();
        }
        params['set_ignore'] = true;
        var xhr = $.ajax({
                        type:'GET',
                        url: Splunk.util.make_url('module', Splunk.util.getConfigValue('SYSTEM_NAMESPACE'), this.moduleType, 'render?' + Splunk.util.propToQueryString(params)),
                        beforeSend: function(xhr) {
                            xhr.setRequestHeader('X-Splunk-Module', this.moduleType);
                        }, 
                        success: function() {
                            return true;
                        }.bind(this),
                        error: function() {
                            this.logger.error(_('Unable to set ignored flag')); 
                        }.bind(this),
                        complete: function() {
                            return true; 
                        }
        });

    }
});
