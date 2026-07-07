# Splunk API alerts

Splunk API Alerts is a Splunk [custom alert actions application](https://docs.splunk.com/Documentation/Splunk/8.0.3/AdvancedDev/ModAlertsIntro).

This application can be added to an alert trigger action in order to send the alert content over HTTP(s) to the specified url. Splunk already provides a webhook feature to send alert content over HTTP, however, unlike this app, Splunk feature does not allow to:

* Send POST HTTP requests
* Add custom authorization headers
* Add an UUID linked to each alert for alert traceability throughout the pipeline

## HOWTO

### Trigger api_alert app in alert

`APi alert` app can be added as a new alert trigger action.

### Configuration

| Name                       | Description |
| -------------------------- |------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Server URL                  | URL where to send the alert content                                                                                                                                                                                                        |
| Authorization header value | This value will be added in Authorization HTTP header with the following format: `Authorization: {header_value}`. This field supports all [authentication types](http://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml). |

Example header values:

* `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOjEwLCJpYXQiOjE1ODk4OTM2MzJ9.BmDHmP0XRVrRQmMGJnhA8vPYj9LS7Kuf2aiRxvt4akk`
* `Basic dGVzdDp0ZXN0`

These parameters can be configured globally in `Settings > Alert Actions > Setup HTTP request notification` (Splunk URL: `/manager/api_alerts/apps/local/api_alerts/setup?action=edit`).

It is also possible to override global configuration for each alert in trigger actions section when editing an alert.

### HTTP format

#### Headers

Main headers:
* Authorization: filled with configuration value
* X-Request-Id: alert tracking UUID

```
POST /alert HTTP/1.1
Accept-Encoding: identity
Content-Length: 295
User-Agent: Python-urllib/3.7
Authorization: Basic dGVzdDp0ZXN0
Content-Type: application/json
X-Request-Id: d958278b-c7f4-460d-abe9-ec0119491d18
Connection: close
```

#### Body

The following fields are sent for each alert:
  * search_name: alert name
  * search_query: alert query
  * result: search query result 

```
{
  "search_name": "Test alert",
  "search_query": "search index=\"_internal\" | head 10  | table _time, index, status, host, sourcetype, component",
  "result": {
    "_time": "1619423628.562",
    "index": "_internal",
    "status": "200",
    "host": "d1f5fc48dd30",
    "sourcetype": "splunkd_access",
    "component": ""
  }
}
```

## App Logs

### Find api-alerts app logs
Application logs are stored in internal index and can be found with the following query:
  * `index="_internal" action=api_alerts`


### Log fields

| Field | Values                                 | Description                                                                                                                                  |
| --------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| action    | api_alerts                            | Action name, here the application name                                                                                                       |
| severity  | ["debug", "info", "error", "critical"] | cf. below                                                                                                                                    |
| uuid      |                                        | Each alert that triggers this application gets an UUID that will allow to trace this alert through the entire alert pipeline. |
| msg       | N/A                                    | Log message from python script                                                                                                               |

Example log:

```log
06-15-2020 13:45:01.691 +0000 ERROR sendmodalert - action=api_alerts STDERR -  severity="INFO" uuid="033150b7-1ea4-4d50-9f51-fe5af2f07801" msg="Calling url='http://172.17.0.3:8080/alert' with body='{"obj": {"search_query": "search index=_* | table _time host| head 2", "result": {"host": "14343b6bbcbe", "_time": "1592227992"}, "search_name": "Test alert"}}'"
```

#### **Severity**

Logs severity level follow Python's [guidelines](https://docs.python.org/3/howto/logging.html):
  * debug/info : everything working as expected, useful for debug.
  * error : An error occured for this alert, it might be a temporary error (temporary network error) or linked to this alert (format error, etc.).
  * critical : The application can't send an alert and future alerts won't work either until a manual action is performed (wrong authentication token, wrong url, etc.).

## Contribute

Code will soon be available on Github.

## License

[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)