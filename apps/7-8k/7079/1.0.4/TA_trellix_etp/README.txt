Technical Add-on Trellix (FireEye) ETP 

# Overview
Technical Add-on Trellix ETP fetch the data from Trellix ETP through their API.
This app offers three function, which is Email trace Request, Alert Summary Request and Message File Request.

# Installation
1. Create an OAuth Token (API Key) on Trellix Cloud
    - [Configuring API keys](https://docs.trellix.com/bundle/etp_api/page/UUID-ad973817-809e-50ea-668d-9419b73ba84b.html)
    - Required entitlements
        - etp.alerts.read
        - etp.email_trace.read
2. Go to TA Trellix ETP App
    - Apps -> TA Trellix ETP -> Configuration -> Add-on Settings
3. Select the region instance and set the OAuth Token.

# Configuration of Add-on Settings
|  Fileds  | Description | 
| ----     | ---- | 
|  Trellix API Key | - Set your API key | 
|  ETP Service Region  | - Set your ETP Reagion. |
|  SSL Verify Enable  | - If checked, this app verifies SSL certificates for every HTTPS requests. In Splunk Cloud, this is forced enabled. |

# Features 
This app supports 2 modular inputs and 3 custom search commands.

|  Type  |  Features | Description | 
| ---- | ---- | ---- |
|  Modular input  |  Alert Summary  | Regular input for Alert Summary |
|  Modular input  |  Email Trace  | Regular input for Email Trace |
|  Custom search command  |  etpemailtrace  | Command for Email Trace Request |
|  Custom search command  |  etpalert  | Command for Alert Summary Request |
|  Custom search command  |  etpmsgfile  | Command for Message File Request |

# Modular input
From input tab of App, can add new input.
To use input, need to create index first.

## Alert Summary input
- This input fetches 100 data every interval.

|  Fileds  | Description | 
| ----     | ---- | 
|  From Last Modified On  | - This app can fetch the data from the datetime you set.<br> - Please set the datetime as ISO format. <br> - If not set, use current time.| 
|  Time Lag Guard  |  - There is a time lag between last modified timestamp of a data and DB insertion timestamp of a data on Trellix. <br> - This option is for the lag.<br> - Recommend to set `5~10` minutes. If 5 is set, this input fetch the data until about 5 minutes ago.  |

## Email Trace input
- At first time of configured, this input fetches data from current time or `last Modified DateTime` field value.
- And it continues to fetch data until next interval.

|  Fileds  | Description | 
| ----     | ---- | 
|  has Attachmen  | - If checked, only fetch data with Attachment. | 
|  last Modified DateTime  | - This app can fetch the data from the datetime you set.<br> - Please set the datetime as ISO format.<br> - If not set, use current time. |
|  from Email  |  - Filter from email address. <br>- If `co.jp` is set, this app can fetch only the data sent from `co.jp`.<br>- If you want to multiple data from, use `;` for a separation keyword.<br>  - e.g. `co.jp;hoge.com`<br>  - Note that only 10 keyword are allowed because of API specification. |
|  from Email Filter  | - Use with `from Email` field. <br>- If you want to exclude specific data from, choose `not in`. |
|  status  | - Filter email status. |
|  status Filter  | - Use with `status` field.<br>- If you want to exclude specific status data, choose `not in`. |
|  Time Lag Guard  |  - There is a time lag between last modified timestamp of a data and DB insertion timestamp of a data on Trellix.<br>- This option is for the lag.<br>- Recommend to set `5~10` minutes. If 5 is set, this input fetch the data until about 5 minutes ago. |

# Custom search command 
There are three commands. 

## etpemailtrace (Email Trace Request)
- This is a Generating Command.
- Returns a list of messages that include specified message attributes that are accessible in the ETP portal. 

|  Options  | Description | 
| ----     | ---- | 
|  subject  | any keyword | 
|  at_verdict  | fail or Pass | 
|  to_accepted_dt  | ISO format. If not set, use a time picker. | 
|  from_accepted_dt  | ISO format. If not set, use a time picker. | 
|  to_email  | any keyword | 
|  from_email  | any keyword | 

- Example
```
| etpemailtrace subject=hoge at_verdict=fail from_accepted_dt="2022-04-22T00:00:00" to_accepted_dt="2022-04-22T16:00:00" to_email="co.jp"
| spath input=_raw
```
- Note
    - This command get max 10000 message attributes.

## etpalert (Alert Summary Request)
- This is a Generating Command.
- Gets a list of advanced threat alerts in summary format.

|  Options  | Description | 
| ----     | ---- | 
|  from_last_modified_on  | ISO format. If not set, use a time picker. | 
|  email_status  | "quarantined", "released", "deleted", "bcc: dropped", "delivered (retroactive)" or "dropped (oob retroactive)" | 

- Example
```
| etpalert from_last_modified_on="2022-04-20T00:00:00"    email_status="bcc: dropped"
| spath input=_raw
``` 
- Note
    - This command get max 10000 alert summaries.

## etpmsgfile (Message File Request)
- This is a Streaming Command.
- Retrieves the email file in plain text format for the given message ID. 

|  Options  | Description | 
| ----     | ---- | 
|  legacy_id  | number | 
|  etp_message_id  | message id | 
|  from_last_modified_on  |ISO format. if not set, use a time picker. | 

- Example 1
```
| makeresults
| etpmsgfile legacy_id=130477116 from_last_modified_on="2022-04-29T00:00:00"
```
- Example 2
```
| makeresults 
| eval legacy_id = "130477116"
| eval from_last_modified_on = "2022-04-29T00:00:00"
| etpmsgfile
```
- Example 3
```
| makeresults
| etpmsgfile etp_message_id=CXXXXXXXXXX
```
- Example 4
```
| makeresults
| eval etp_message_id = "CXXXXXXXXXX"
| etpmsgfile
```

# API Access control
## REST API concurrency
The following text brings from this article. Please read this for more details.
- [REST API concurrency](https://docs.trellix.com/ja-JP/bundle/etp_api/page/UUID-ad973817-809e-50ea-668d-9419b73ba84b_4.html#idm45624908965008)


Email Cloud REST APIs have a rate limit of 60 requests per minute per API route (/trace, /alert, and /quarantine) for every customer.

This means, in 1 minute, a customer can make:
- 60 requests to Trace APIs (parallel or sequential)
- 60 requests to Alert APIs (parallel or sequential)
- 60 requests to Quarantine APIs (parallel or sequential)

Within the minute, the 61st request to any of these APIs would throw a rate limit exceeded error.

The rate limit applies to the customer as a whole. This means that if the customer has multiple admin users who have generated API Keys, the rate limit is applicable at the customer level and not per API key.


# Debug
- Please check the internal log.
```
index=_internal source="*trellix_etp*" NOT "__init__"

# old version
index=_internal source="*fireeye_etp*" NOT "__init__"
```
