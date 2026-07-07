[pubnub://<name>]

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* key = {encrypted:somekey}

*channel to subscribe to
channel= <value>

#subscribe key
key= <value>

*Python classname of custom response handler
response_handler= <value>

*Response Handler arguments string ,  key=value,key2=value2
response_handler_args= <value>

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
activation_key = <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/pubnubmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
