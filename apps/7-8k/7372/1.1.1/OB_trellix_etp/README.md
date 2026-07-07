# OB_Trellix_ETP
* 관련 일감: https://redmine.openbase.co.kr/issues/9377

* Splunk app 다운로드: https://splunkbase.splunk.com/app/7372
-----------------------
### Splunk app 업로드

* 코드 수정 후 압축 방법
1. Linux 환경에서 OB_trellix_etp 압축 해제
2. OB_trellix_etp 디렉터리로 진입
3. 아래 파일 및 디렉터리 삭제
    - idea
    - splunkbase.manifest
    - app.manifest
4. 실행 권한 삭제 (※OB_trellix_etp 디렉토리 내부에서 실행)
    - find . -type f ! -name "*.sh" -exec chmod 644 {} \\;
5. 상위 디렉터리로 이동 후 압축 진행
    - COPYFILE_DISABLE=1 tar --format ustar -cvzf {압축 파일 이름} {압축 대상 디렉터리}
      - ex) COPYFILE_DISABLE=1 tar --format ustar -cvzf ob_trellix_etp_105.tar.gz OB_trellix_etp

* 업로드 전 Splunk app 테스트 API: https://dev.splunk.com/enterprise/docs/developapps/testvalidate/appinspect/useappinspectapi#Import-the-Splunk-AppInspect-scripts-into-Postman

-----------------------
### Python SDK 업데이트
* 교체 대상 라이브러리리
  - splunklib/: Splunk SDK의 핵심 모듈
  - splunk_sdk-x.x.x.dist-info/: 현재 설치된 Splunk SDK의 버전 및 메타데이터 정보

* 교체 방법 (예시: 1.6.18 -> 2.0.2)
1. lib 디렉터리에서 splunk_sdk-1.6.18.dist-info 디렉터리 확인 (이전 버전임을 확인)
2. splunklib, splunk_sdk-1.6.18.dist-info 디렉터리 삭제
3. pip로 새 sdk 설치 (pip 버전에 따라 상위 버전의 sdk가 설치되지 않을 수도 있으므로 pip 버전 확인 필요)
    - pip install splunk-sdk==2.0.2 --target=lib
4. lib 디렉터리 내부에 splunklib, splunk_sdk-2.0.2.dist-info 디렉터리 생성 확인
5. 위의 '코드 수정 후 압축방법' 으로 압축 진행 후 업로드 테스트 진행
6. .pyc 파일 등의 문제로 업로드 테스트 실패가 뜰 경우 아래 명령어로 실행 파일 삭제
    - find lib -name "*.pyc" -delete
    - find lib -type d -name "__pycache__" -exec rm -r {} +
-----------------------

Technical Add-on Trellix ETP 

# Overview
Technical Add-on Trellix ETP fetch the data from Trellix ETP through their API.
This app offers three function, which is Email trace Request, Alert Summary Request, Audit Log and Message File Request.


# Installation
1. Create an OAuth Credential on Trellix Cloud
    - [Configuring API Credential](https://uam.ui.trellix.com/clientcreds.html)
    - Required entitlements
		- scope=etp.alrt.ro etp.trce.ro etp.admn.ro
2. Go to Trellix ETP App
    - Apps -> Trellix ETP -> Configuration -> Add-on Settings
3. Select the region instance and set the Credential.

# Configuration of Add-on Settings
|  Fileds  | Description | 
| ----     | ---- | 
|  Trellix IAM Client ID | - Set your Client ID | 
|  Trellix IAM Secret | - Set your Secret | 
|  ETP Service Region  | - Set your ETP Reagion. |
|  SSL Verify Enable  | - If checked, this app verifies SSL certificates for every HTTPS requests. In Splunk Cloud, this is forced enabled. |

# Features 
This app supports 2 modular inputs and 3 custom search commands.

|  Type  |  Features | Description | 
| ---- | ---- | ---- |
|  Modular input  |  Alert Summary  | Regular input for Alert Summary |
|  Modular input  |  Email Trace  | Regular input for Email Trace |
|  Modular input  |  Audit Log  | Regular input for Audit Log |
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

## Audit Log
- At first time of configured, this input fetches data from current time or `last Modified DateTime` field value.
- And it continues to fetch data until next interval.

|  Fileds  | Description | 
| ----     | ---- | 
|  user_email_id  | - 10 entries maximum. use ; to separate. | 


## Change time zone
You can change the time zone when events are stored in splunk.
When you save an event in this app, it displays in KST by default.

default/probs.conf
TZ = Asia/Seoul -> your timezone



## APIs limit

Email Cloud REST APIs have a rate limit of 60 requests per minute per API route (/trace, /alert, and /quarantine) for every customer.

This means, in 1 minute, a customer can make:
- 60 requests to Trace APIs (parallel or sequential)
- 60 requests to Alert APIs (parallel or sequential)
- 60 requests to Quarantine APIs (parallel or sequential)

Within the minute, the 61st request to any of these APIs would throw a rate limit exceeded error.

The rate limit applies to the customer as a whole. This means that if the customer has multiple admin users who have generated API Keys, the rate limit is applicable at the customer level and not per API key.



(Modified by openbase, original autor is Masaki Yoshikawa)
*This app is not developed by Trellix and does not provide official or regular updates.
