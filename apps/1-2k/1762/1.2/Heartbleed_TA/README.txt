## A Splunk Heartbleed Test Command ##

This CIM-Compliant Technology Add-on (TA-Heartbleed) contains a new heartbleedtest command that can be used to check your internal infrastructure and external websites for the recently announced Heartbleed vulnerability. 

Upon invoking the command on your Splunk search results, it will run a check against provided host/port values and return a new field, named vulnerable, that will state whether the host values are vulnerable to heartbleed or not.


## How to Use the Command ##

The command is invoked as follows:

| heartbleedtest serverfield=[serverfield] portfield=[portfield] timeout=[int] poolsize=[int]

Note: fieldvalue, port and timeout are optional. Here are the defaults when they are not specified:
serverfield = dest, portfield = port, timeout = 3, poolsize = 10

The serverfield field contains host values (e.g. google.com, yahoo.com, myserver.company.com)
The portfield contains port numbers (e.g. 443, 8000)
Timeout is declared as an integer
Poolsize is how many concurrent threads the command uses (e.g. the default of 10 means that it can check 10 hosts at once)

**Note: Increasing the poolsize will allow you to check more hosts at once, but will also increase memory utilisation as a result.


## Example Searches ##

MySplunkSearch | heartbleedtest serverfield=dest portfield=port timeout=3 poolsize=10 | table dest port vulnerable

These are actually the default variables and we do not actually need to declare them – we are doing so here for illustrative purposes. This will run the heartbleed test on using the default serverfield of dest, the default portfield of port, the default timeout of 3 seconds and the default poolsize of 10. It will tabulate the results and tell you if any dest values are vulnerable.

MySplunkSearch | heartbleedtest serverfield=myHostField portfield=myPortField timeout=10 poolsize=100 | table myHostField myPortField vulnerable

This will run the heartbleed test on a serverfield of myHostField, a portfield of myPortField, a timeout of 10 seconds and a poolsize of 100 threads. It will tabulate the results and tell you if any myHostField values are vulnerable.


## Installation ##

To install the command – download the TA, then install into Splunk as you would do any other app and you should be all set. The command is set to be global, so should work from any of your existing apps.

For support, feedback, questions, concerns – feel free to contact us: support<AT>discoveredintelligence.ca
