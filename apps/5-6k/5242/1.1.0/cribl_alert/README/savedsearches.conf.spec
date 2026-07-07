# Cribl Modular Alert

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* action.cribl.param.authtoken = {encrypted:somekey}

action.cribl = [0|1]

action.cribl.param.host = <string>
action.cribl.param.port = <string>
action.cribl.param.authtoken = <string>
action.cribl.param.fieldlist = <string>
action.cribl.param.maxpostevents = <string>
