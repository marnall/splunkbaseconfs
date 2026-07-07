# Spur context API App by GoAhead

## Introduction

Spur context API App is Spur.us context API(v2) wrapper for retrieving the attribute of IP intelligence data like AS, ISP, geolocation, VPN, proxy, tor etc. 
This App requests to "https://api.spur.us/v2/context/".
The API Key is needed for utilize.

## Installation

The Spur context API Key is needed to utilize this App. (ref: https://spur.us/products/context-api/)
1. Install this App package
2. Set up the API Key on the App Setup Page. 
4. Restarting splunk search head instance may be sometimes possibly needed for activating these custom search commands and loading this app's icon. 

Note: App Install user needs "admin_all_objects" privilege and Splunk search users need "list_storage_passwords" privilege in order to utilize "Secret storage".

## Usage

1. **spurapigen**
    - GeneratingCommand as Spur.us context API(v2) wrapper.
    - Options (Please refer to Spur API docs for detail.)
        - **ip** (Required)   :  String of IP address (v4 or v6)
    - Output field name
        - ALL output names are the same to the API Schema's response fields with a prefix of "Spur_".
    - Example  
        - ` | spurapigen ip="8.8.8.8"`

2. **spurapi**
    - StreamingCommand to append the attribute of IP intelligence data.
    - Options
        - **ip_field** (Required):  Target field name of IP address (v4 or v6)
        - **apisaver**           :(Optional) API amount saver, **default: true**. This app raises exception if the amoount of your events passed to this command are over 50. Please set "apisaver=false" explicitly to avoid this limit.
    - Output field name
        - ALL output names are the following to the API Schema's response fields with a prefix of "Spur_".
    - Example  
        - `...| fields ipfield | spurapi ip_field=ipfield`

3. **spurapiremain**
    - GeneratingCommand to append the api status for checking the remain amount.
    - Output field name
        - ALL output names are the following to the API Schema's response fields with a prefix of "Spur_".
    - Example  
        - ` | spurapiremain`

Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. 

Some errors are dumped to the command result fields and the command exception will be dumped in search.log.
Especially, Request URL string and its HTTP response code will be dumped in search.log for debugging.

## Spur API Docs

- [Spur context API v2 Schema](https://spur.us/2021/11/announcing-the-ip-context-v2-schema/)

## Included 3rd party's additional import modules

None

## Similar Splunk App

None (as long as our research)


## Attention to begin to use this app

We are not responsible for charges due to Spur context API consumption or disadvantages due to using up the monthly limit quota.

## Support

Splunk 9.x or later

## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2025 GoAhead Inc.
