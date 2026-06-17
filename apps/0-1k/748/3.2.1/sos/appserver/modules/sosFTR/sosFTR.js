Splunk.namespace("Module");
Splunk.Module.sosFTR = $.klass(Splunk.Module, {

    initialize: function($super, container) {
        $super(container);
        this.logger = Splunk.Logger.getLogger("sosFTR.js");
        this.messenger = Splunk.Messenger.System.getInstance();
        this.popupDiv = $('.sosPopup', this.container).get(0);
        this.redirectTo = 'manager/sos/apps/remote?q=Sideview+Utils+(LGPL)';
        this.getResults();
    },
    renderResults: function(htmlFragment, turbo) {
        if (htmlFragment.indexOf('hasSVU') === -1) {
            this.popupDiv.innerHTML = '<div style="text-align:center;padding:0px 10px 0px 10px;width:520px"><br><br><h2>This instance of Splunk does not have the <a target="_blank" class="spl-icon-external-link-xsm" href="http://apps.splunk.com/app/466">Sideview Utils</a> app installed.</h2><br><img height="300" width="400" src="../../static/app/sos/images/porblem.jpg"><br><p>The Splunk on Splunk app depends on custom modules from Sideview Utils in order to function.</p><br><br><br></div>';
            this.popup = new Splunk.Popup(this.popupDiv, {
                cloneFlag: false,
                title: _("Sideview Utilikilts Not Installed!!!!1!"),
                pclass: 'configPopup',
                buttons: [
                     {
                         label: _("Install Sideview Utils"),
                         type: "primary",
                         callback: function(){
                             Splunk.util.redirect_to(this.redirectTo);
                         }.bind(this)
                     }
                 ]
             });
        } else {
             Splunk.util.redirect_to(['app', Splunk.util.getCurrentApp()].join('/'), {});
        } 
    }
});
