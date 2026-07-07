[xmatters]

param.endpoint_url = <string>
* xMatters Web Service URL for the Splunk Alert form

param.xMuser = <string>
* REST Web Services user for authenticating to xMatters

param.priority = <string>
* The Priority to assign to the xMatters Event. Valid values are HIGH, MEDIUM and LOW.

param.app = <string>
* Name of the app containing the search

param.cron.schedule = <string>
* Cron schedule for the app

param.description = <string>
* Description of the search

param.name = <string>
* Name of the search

param.next_scheduled_time = <string>
* The next time the search runs

param.owner = <string>
* Owner of the search

param.results_link = <string>
* Link to the search results

param.search = <string>
* The actual search

param.trigger.date = <string>
* The date that triggers the alert

param.trigger.time = <string>
* The scheduled time the alert runs

param.type = <string>
* Run as alert, report, view, search command

param.view_link = <string>
* Link to view the saved report (Dropped in 6.3? SPL-97162)

param.alert.expires = <string>
* Time the alert expires

param.result.source = <string>
* Source entry from the result

param.result.host = <string>
* Host entry from the result

param.result.sourcetype = <string>
* Source Type entry from the result

param.result.splunk_server = <string>
* Splunk Server from the result

python.version = <string>
* Python version used in this integration (pre Splunk 10.2)

python.required = <string>
* Python version used in this integration (after Splunk 10.2)
