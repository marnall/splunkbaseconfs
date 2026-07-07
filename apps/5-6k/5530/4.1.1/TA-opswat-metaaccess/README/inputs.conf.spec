[metaaccess_api://<name>]
global_account = Select the account to use.
api_endpoint = Provide the API endpoint as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
http_request_method = Select the HTTP request method to use for the selected API endpoint.
body = Optional: Provide an additional filter in JSON format as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.

[metaaccess_logs://<name>]
global_account = Select the account to use.
api_endpoint = Provide the API endpoint as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
event_category = Select the category for log collection
start_date = Provide how many days prior to today that you need to collect logs. Default value is 7, max value is 30.
filter = Optional: Provide an additional filter in JSON format as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.

[metaaccess_device_logs://<name>]
global_account = Select the account to use.
api_endpoint = Provide the API endpoint as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
start_date = Provide how many days prior to today that you need to collect logs. Default value is 7, max value is 30.
filter = Optional: Provide an additional filter in JSON format as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
event_trigger = Select the events that will trigger a device details call.
device_details_endpoint = Provide the API endpoint as per the MetaAccess API documentation. The default supported version is 3.2 for Logs.
device_details_body = Optional: Provide additional body parameters in JSON format as per the MetaAccess API documentation.
vulnerabilities_endpoint = Provide the API endpoint as per the MetaAccess API documentation.
vulnerabilities_body = Optional: Provide additional body parameters in JSON format as per the MetaAccess API documentation.
retrieve_device_details = Retrieve Device Details
retrieve_vulnerabilities = Retrieve Device CVEs

[metaaccess_product_reports://<name>]
global_account = Select the account to use.
api_endpoint = Provide the API endpoint as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
start_date = Provide how many days prior to today that you need to collect logs. Default value is 7, max value is 30.
filter = Optional: Provide an additional filter in JSON format as per the MetaAccess API <a href="https://onlinehelp.opswat.com/metaaccess/4.1.2._OAuth_APIs.html" target="_blank">documentation</a>.
retrieve_report_details = Retrieve Report Details
