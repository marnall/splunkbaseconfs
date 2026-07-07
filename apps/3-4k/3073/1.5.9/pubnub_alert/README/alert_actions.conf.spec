[pubnub]

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* param.pubkey = {encrypted:somekey}


param.pubkey = <string>
param.subkey = <string>

param.activationkey = <string>
* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

param.log_level = <string>
* Modular Alert script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/pubnubalert_app_modularalert.log , defaults to 'INFO'