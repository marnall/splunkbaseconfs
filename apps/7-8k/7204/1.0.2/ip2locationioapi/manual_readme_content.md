\[comment\]: # File: manual_readme_content.md
\[comment\]: #
\[comment\]: # Copyright (c) IP2Location.io, 2024
\[comment\]: #
\[comment\]: # Licensed under the Apache License, Version 2.0 (the "License");
\[comment\]: # you may not use this file except in compliance with the License.
\[comment\]: # You may obtain a copy of the License at
\[comment\]: #
\[comment\]: # http://www.apache.org/licenses/LICENSE-2.0
\[comment\]: #
\[comment\]: # Unless required by applicable law or agreed to in writing, software distributed under
\[comment\]: # the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
\[comment\]: # either express or implied. See the License for the specific language governing permissions
\[comment\]: # and limitations under the License.

Query IP geolocation data from IP2Location.io API.

Get free IP2Location.io API from from https://www.ip2location.io/pricing for basic geolocation data.
Below is an example output if you're subscribed to the Security plan.

JSON

<pre>{
	"ip":"8.8.8.8",
	"country_code":"US",
	"country_name":"United States of America",
	"region_name":"California",
	"city_name":"Mountain View",
	"latitude":37.405992,
	"longitude":-122.078515,
	"zip_code":"94043",
	"time_zone":"-07:00",
	"asn":"15169",
	"as":"Google LLC",
	"isp":"Google LLC",
	"domain":"google.com",
	"net_speed":"T1",
	"idd_code":"1",
	"area_code":"650",
	"weather_station_code":"USCA0746",
	"weather_station_name":"Mountain View",
	"mcc":"-",
	"mnc":"-",
	"mobile_brand":"-",
	"elevation":32,
	"usage_type":"DCH",
	"address_type":"Anycast",
	"continent":{
		"name":"North America",
		"code":"NA",
		"hemisphere":["north","west"],
		"translation":{
			"lang":"ko",
			"value":"북아메리카"
		}
	},
	"country":{
		"name":"United States of America",
		"alpha3_code":"USA",
		"numeric_code":840,
		"demonym":"Americans",
		"flag":"https://cdn.ip2location.io/assets/img/flags/us.png",
		"capital":"Washington, D.C.",
		"total_area":9826675,
		"population":331002651,
		"currency":{
			"code":"USD",
			"name":"United States Dollar",
			"symbol":"$"
		},
		"language":{
			"code":"EN",
			"name":"English"
		},
		"tld":"us",
		"translation":{
			"lang":"ko",
			"value":"미국"
		}
	},
	"region":{
		"name":"California",
		"code":"US-CA",
		"translation":{
			"lang":"ko",
			"value":"캘리포니아주"
		}
	},
	"city":{
		"name":"Mountain View",
		"translation":{
			"lang":null,
			"value":null
		}
	},
	"time_zone_info":{
		"olson":"America/Los_Angeles",
		"current_time":"2022-04-18T23:41:57-07:00",
		"gmt_offset":-25200,
		"is_dst":true,
		"sunrise":"06:27",
		"sunset":"19:47"
	},
	"geotargeting":{
		"metro":"807"
	},
	"ads_category":"IAB19",
	"ads_category_name":"Technology & Computing",
	"district":"San Diego County",
	"is_proxy":false,
	"proxy":{
		"last_seen":18,
		"proxy_type":"DCH",
		"threat":"-",
		"provider":"-",
		"is_vpn": false,
        "is_tor": false,
        "is_data_center": true,
        "is_public_proxy": false,
        "is_web_proxy": false,
        "is_web_crawler": false,
        "is_residential_proxy": false,
        "is_spammer": false,
        "is_scanner": false,
        "is_botnet": false
	}
}
</pre>
