[command://<name>]

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* command_name = {encrypted:somekey}

*command name , environment variables in the format $VARIABLE$ can be included and they will be substituted ie: $SPLUNK_HOME$
command_name= <value>

*command args, environment variables in the format $VARIABLE$ can be included and they will be substituted ie: $SPLUNK_HOME$
command_args= <value>

*whether or not command output is streaming or not
streaming_output = <value>

*in seconds
execution_interval= <value>

*Python classname of custom command output handler
output_handler= <value>

*Command output handler arguments string ,  key=value,key2=value2
output_handler_args= <value>

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
activation_key = <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/commandmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
