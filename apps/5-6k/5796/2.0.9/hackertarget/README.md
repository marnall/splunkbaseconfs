# HackerTarget

Publisher: Splunk <br>
Connector Version: 2.0.9 <br>
Product Vendor: HackerTarget <br>
Product Name: HackerTarget <br>
Minimum Product Version: 5.1.0

This app supports executing investigative actions to analyze a host

### Configuration variables

This table lists the configuration variables required to operate HackerTarget. These variables are specified when configuring a HackerTarget asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | optional | string | Base URL |
**api_key** | optional | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[get headers](#action-get-headers) - Get HTTP Headers from a URL <br>
[get links](#action-get-links) - Get HTTP Links from a URL <br>
[traceroute domain](#action-traceroute-domain) - Traceroute to a domain <br>
[traceroute ip](#action-traceroute-ip) - Traceoute to an IP <br>
[reverse domain](#action-reverse-domain) - Find IPs that resolve to this domain <br>
[reverse ip](#action-reverse-ip) - Find domains that resolve to this IP <br>
[whois ip](#action-whois-ip) - Execute a whois lookup on the given IP <br>
[whois domain](#action-whois-domain) - Execute a whois lookup on the given domain <br>
[ping domain](#action-ping-domain) - Ping a domain <br>
[ping ip](#action-ping-ip) - Ping an IP <br>
[geolocate ip](#action-geolocate-ip) - Geolocate an IP <br>
[geolocate domain](#action-geolocate-domain) - Geolocate a domain

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get headers'

Get HTTP Headers from a URL

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL ie. http://www.hackertarget.com | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | https://www.hackertarget.com |
action_result.data.\*.headers.\*.Accept-Ranges | string | | none |
action_result.data.\*.headers.\*.Age | string | | |
action_result.data.\*.headers.\*.Alt-Svc | string | | quic=:443; ma=2592000; v=44,43,39 |
action_result.data.\*.headers.\*.Cache-Control | string | | private, max-age=0 |
action_result.data.\*.headers.\*.Content-Encoding | string | | |
action_result.data.\*.headers.\*.Content-Length | string | | |
action_result.data.\*.headers.\*.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.headers.\*.Date | string | | Thu, 31 Jan 2019 05:55:18 GMT |
action_result.data.\*.headers.\*.Expires | string | | -1 |
action_result.data.\*.headers.\*.Last-Modified | string | | |
action_result.data.\*.headers.\*.Location | string | `url` | |
action_result.data.\*.headers.\*.P3P | string | | CP=This is not a P3P policy! See g.co/p3phelp for more info. |
action_result.data.\*.headers.\*.Server | string | | gws |
action_result.data.\*.headers.\*.Set-Cookie | string | | NID=158=HccET5f97JkzpL1ECD07_6PAgubd6rrnh_035wU92T_I21UT4OEGFcPhYog7JSFQ0Ob1TRCaajWLQ_96mELMVQMxj-2b6kY1yOfo9pX6t2oSv-1T1XzgtEgeFDSePBNskd1OCo_yfjzTaQdBTEYKR7kNRifN80NjxCv0mW4pW5I; expires=Fri, 02-Aug-2019 05:55:18 GMT; path=/; domain=.hackertarget.com; HttpOnly |
action_result.data.\*.headers.\*.Strict-Transport-Security | string | | max-age=31536000 |
action_result.data.\*.headers.\*.Transfer-Encoding | string | | chunked |
action_result.data.\*.headers.\*.Vary | string | | Accept-Encoding |
action_result.data.\*.headers.\*.X-Cache | string | | |
action_result.data.\*.headers.\*.X-Frame-Options | string | | SAMEORIGIN |
action_result.data.\*.headers.\*.X-XSS-Protection | string | | 1; mode=block |
action_result.data.\*.headers.\*.http_version | string | | 1.1 |
action_result.data.\*.headers.\*.response_code | string | | 200 |
action_result.data.\*.raw | string | | HTTP/1.1 200 OK
Date: Thu, 31 Jan 2019 05:55:18 GMT
Expires: -1
Cache-Control: private, max-age=0
Content-Type: text/html; charset=UTF-8
Strict-Transport-Security: max-age=31536000
P3P: CP=This is not a P3P policy! See g.co/p3phelp for more info.
Server: gws
X-XSS-Protection: 1; mode=block
X-Frame-Options: SAMEORIGIN
Set-Cookie: 1P_JAR=2019-01-31-05; expires=Sat, 02-Mar-2019 05:55:18 GMT; path=/; domain=hackertarget.com
Set-Cookie: NID=158=HccET5f97JkzpL1ECD07_6PAgubd6rrnh_035wU92T_I21UT4OEGFcPhYog7JSFQ0Ob1TRCaajWLQ_96mELMVQMxj-2b6kY1yOfo9pX6t2oSv-1T1XzgtEgeFDSePBNskd1OCo_yfjzTaQdBTEYKR7kNRifN80NjxCv0mW4pW5I; expires=Fri, 02-Aug-2019 05:55:18 GMT; path=/; domain=.hackertarget.com; HttpOnly
Transfer-Encoding: chunked
Alt-Svc: quic=:443; ma=2592000; v=44,43,39
Accept-Ranges: none
Vary: Accept-Encoding |
action_result.summary.header_count | numeric | | 1 |
action_result.message | string | | Header count: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get links'

Get HTTP Links from a URL

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL ie. http://www.hackertarget.com | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | https://www.google.com |
action_result.data.\*.raw | string | `url` | https://www.google.com/imghp?hl=en&tab=wi https://maps.google.com/maps?hl=en&tab=wl https://play.google.com/?hl=en&tab=w8 https://www.youtube.com/?gl=US&tab=w1 https://news.google.com/nwshp?hl=en&tab=wn https://mail.google.com/mail/?tab=wm https://drive.google.com/?tab=wo https://www.google.com/intl/en/about/products?tab=wh http://www.google.com/history/optout?hl=en https://www.google.com/preferences?hl=en https://accounts.google.com/ServiceLogin?hl=en&passive=true&continue=https://www.google.com/ https://www.google.com/images/branding/googlelogo/1x/googlelogo_white_background_color_272x92dp.png https://www.google.com/advanced_search?hl=en&authuser=0 https://www.google.com/language_tools?hl=en&authuser=0 https://www.google.com/intl/en/ads/ https://www.google.com/services/ https://plus.google.com/116899029375914044550 https://www.google.com/intl/en/about.html https://www.google.com/intl/en/policies/privacy/ https://www.google.com/intl/en/policies/terms/ |
action_result.data.\*.urls.\*.url | string | `url` | https://www.google.com/imghp?hl=en&tab=wi |
action_result.summary.total_urls | numeric | | 20 |
action_result.message | string | | Total urls: 20 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'traceroute domain'

Traceroute to a domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Host FQDN ie. www.hackertarget.com | string | `url` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `url` `domain` | google.com |
action_result.data.\*.hop.\*.avg | string | | |
action_result.data.\*.hop.\*.best | string | | |
action_result.data.\*.hop.\*.hop | string | | |
action_result.data.\*.hop.\*.host | string | `domain` `ip` | |
action_result.data.\*.hop.\*.last | string | | |
action_result.data.\*.hop.\*.loss | string | | |
action_result.data.\*.hop.\*.raw | string | | |
action_result.data.\*.hop.\*.sent | string | | |
action_result.data.\*.hop.\*.stdev | string | | |
action_result.data.\*.hop.\*.worst | string | | |
action_result.data.\*.hop.1.avg | string | | 1.0 |
action_result.data.\*.hop.1.best | string | | 1.0 |
action_result.data.\*.hop.1.hop | string | | 1 |
action_result.data.\*.hop.1.host | string | | 2600:3c00::e6c7:22ff:fe10:9cc1 |
action_result.data.\*.hop.1.last | string | | 1.0 |
action_result.data.\*.hop.1.loss | string | | 0.0% |
action_result.data.\*.hop.1.raw | string | | 1.|-- 2600:3c00::e6c7:22ff:fe10:9cc1 0.0% 3 1.0 1.0 1.0 1.0 0.0 |
action_result.data.\*.hop.1.sent | string | | 3 |
action_result.data.\*.hop.1.stdev | string | | 0.0 |
action_result.data.\*.hop.1.worst | string | | 1.0 |
action_result.data.\*.hop.2.avg | string | | 6.4 |
action_result.data.\*.hop.2.best | string | | 1.1 |
action_result.data.\*.hop.2.hop | string | | 2 |
action_result.data.\*.hop.2.host | string | | 2600:3c00:2222:18::1 |
action_result.data.\*.hop.2.last | string | | 3.5 |
action_result.data.\*.hop.2.loss | string | | 0.0% |
action_result.data.\*.hop.2.raw | string | | 2.|-- 2600:3c00:2222:18::1 0.0% 3 3.5 6.4 1.1 14.7 7.3 |
action_result.data.\*.hop.2.sent | string | | 3 |
action_result.data.\*.hop.2.stdev | string | | 7.3 |
action_result.data.\*.hop.2.worst | string | | 14.7 |
action_result.data.\*.hop.3.avg | string | | 0.8 |
action_result.data.\*.hop.3.best | string | | 0.7 |
action_result.data.\*.hop.3.hop | string | | 3 |
action_result.data.\*.hop.3.host | string | | 2600:3c00:2222:10::1 |
action_result.data.\*.hop.3.last | string | | 0.9 |
action_result.data.\*.hop.3.loss | string | | 0.0% |
action_result.data.\*.hop.3.raw | string | | 3.|-- 2600:3c00:2222:10::1 0.0% 3 0.9 0.8 0.7 0.9 0.1 |
action_result.data.\*.hop.3.sent | string | | 3 |
action_result.data.\*.hop.3.stdev | string | | 0.1 |
action_result.data.\*.hop.3.worst | string | | 0.9 |
action_result.data.\*.hop.4.avg | string | | 1.6 |
action_result.data.\*.hop.4.best | string | | 1.3 |
action_result.data.\*.hop.4.hop | string | | 4 |
action_result.data.\*.hop.4.host | string | | eqix-da1.google.com |
action_result.data.\*.hop.4.last | string | | 2.1 |
action_result.data.\*.hop.4.loss | string | | 0.0% |
action_result.data.\*.hop.4.raw | string | | 4.|-- eqix-da1.google.com 0.0% 3 2.1 1.6 1.3 2.1 0.4 |
action_result.data.\*.hop.4.sent | string | | 3 |
action_result.data.\*.hop.4.stdev | string | | 0.4 |
action_result.data.\*.hop.4.worst | string | | 2.1 |
action_result.data.\*.hop.5.avg | string | | 2.6 |
action_result.data.\*.hop.5.best | string | | 2.3 |
action_result.data.\*.hop.5.hop | string | | 5 |
action_result.data.\*.hop.5.host | string | | 2001:4860:0:e02::1 |
action_result.data.\*.hop.5.last | string | | 2.3 |
action_result.data.\*.hop.5.loss | string | | 0.0% |
action_result.data.\*.hop.5.raw | string | | 5.|-- 2001:4860:0:e02::1 0.0% 3 2.3 2.6 2.3 3.2 0.5 |
action_result.data.\*.hop.5.sent | string | | 3 |
action_result.data.\*.hop.5.stdev | string | | 0.5 |
action_result.data.\*.hop.5.worst | string | | 3.2 |
action_result.data.\*.hop.6.avg | string | | 1.6 |
action_result.data.\*.hop.6.best | string | | 1.5 |
action_result.data.\*.hop.6.hop | string | | 6 |
action_result.data.\*.hop.6.host | string | | 2001:4860:0:1::124b |
action_result.data.\*.hop.6.last | string | | 1.5 |
action_result.data.\*.hop.6.loss | string | | 0.0% |
action_result.data.\*.hop.6.raw | string | | 6.|-- 2001:4860:0:1::124b 0.0% 3 1.5 1.6 1.5 1.8 0.2 |
action_result.data.\*.hop.6.sent | string | | 3 |
action_result.data.\*.hop.6.stdev | string | | 0.2 |
action_result.data.\*.hop.6.worst | string | | 1.8 |
action_result.data.\*.hop.7.avg | string | | 1.5 |
action_result.data.\*.hop.7.best | string | | 1.3 |
action_result.data.\*.hop.7.hop | string | | 7 |
action_result.data.\*.hop.7.host | string | | dfw25s27-in-x0e.1e100.net |
action_result.data.\*.hop.7.last | string | | 1.3 |
action_result.data.\*.hop.7.loss | string | | 0.0% |
action_result.data.\*.hop.7.raw | string | | 7.|-- dfw25s27-in-x0e.1e100.net 0.0% 3 1.3 1.5 1.3 1.8 0.2 |
action_result.data.\*.hop.7.sent | string | | 3 |
action_result.data.\*.hop.7.stdev | string | | 0.2 |
action_result.data.\*.hop.7.worst | string | | 1.8 |
action_result.data.\*.raw | string | | Start: 2019-01-31T05:34:17+0000 HOST: web01 Loss% Snt Last Avg Best Wrst StDev 1.|-- 2600:3c00::e6c7:22ff:fe10:9cc1 0.0% 3 1.0 1.0 1.0 1.0 0.0 2.|-- 2600:3c00:2222:18::1 0.0% 3 3.5 6.4 1.1 14.7 7.3 3.|-- 2600:3c00:2222:10::1 0.0% 3 0.9 0.8 0.7 0.9 0.1 4.|-- eqix-da1.google.com 0.0% 3 2.1 1.6 1.3 2.1 0.4 5.|-- 2001:4860:0:e02::1 0.0% 3 2.3 2.6 2.3 3.2 0.5 6.|-- 2001:4860:0:1::124b 0.0% 3 1.5 1.6 1.5 1.8 0.2 7.|-- dfw25s27-in-x0e.1e100.net 0.0% 3 1.3 1.5 1.3 1.8 0.2 |
action_result.summary.total_hops | numeric | | 7 |
action_result.message | string | | Total hops: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'traceroute ip'

Traceoute to an IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | Host ip | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 45.23.78.36 |
action_result.data.\*.hop.\*.avg | string | | |
action_result.data.\*.hop.\*.best | string | | |
action_result.data.\*.hop.\*.hop | string | | |
action_result.data.\*.hop.\*.host | string | `domain` `ip` | |
action_result.data.\*.hop.\*.last | string | | |
action_result.data.\*.hop.\*.loss | string | | |
action_result.data.\*.hop.\*.raw | string | | |
action_result.data.\*.hop.\*.sent | string | | |
action_result.data.\*.hop.\*.stdev | string | | |
action_result.data.\*.hop.\*.worst | string | | |
action_result.data.\*.hop.1.avg | string | | 0.0 |
action_result.data.\*.hop.1.best | string | | 0.0 |
action_result.data.\*.hop.1.hop | string | | 1 |
action_result.data.\*.hop.1.host | string | | ??? |
action_result.data.\*.hop.1.last | string | | 0.0 |
action_result.data.\*.hop.1.loss | string | | 100.0 |
action_result.data.\*.hop.1.raw | string | | 15.|-- ??? 100.0 3 0.0 0.0 0.0 0.0 0.0 |
action_result.data.\*.hop.1.sent | string | | 3 |
action_result.data.\*.hop.1.stdev | string | | 0.0 |
action_result.data.\*.hop.1.worst | string | | 0.0 |
action_result.data.\*.hop.2.avg | string | | 2.9 |
action_result.data.\*.hop.2.best | string | | 0.9 |
action_result.data.\*.hop.2.hop | string | | 2 |
action_result.data.\*.hop.2.host | string | `ip` | 45.79.12.0 |
action_result.data.\*.hop.2.last | string | | 5.6 |
action_result.data.\*.hop.2.loss | string | | 0.0% |
action_result.data.\*.hop.2.raw | string | | 2.|-- 45.79.12.0 0.0% 3 5.6 2.9 0.9 5.6 2.4 |
action_result.data.\*.hop.2.sent | string | | 3 |
action_result.data.\*.hop.2.stdev | string | | 2.4 |
action_result.data.\*.hop.2.worst | string | | 5.6 |
action_result.data.\*.hop.3.avg | string | | 5.1 |
action_result.data.\*.hop.3.best | string | | 0.9 |
action_result.data.\*.hop.3.hop | string | | 3 |
action_result.data.\*.hop.3.host | string | `ip` | 45.79.12.9 |
action_result.data.\*.hop.3.last | string | | 7.0 |
action_result.data.\*.hop.3.loss | string | | 0.0% |
action_result.data.\*.hop.3.raw | string | | 3.|-- 45.79.12.9 0.0% 3 7.0 5.1 0.9 7.4 3.6 |
action_result.data.\*.hop.3.sent | string | | 3 |
action_result.data.\*.hop.3.stdev | string | | 3.6 |
action_result.data.\*.hop.3.worst | string | | 7.4 |
action_result.data.\*.hop.4.avg | string | | 0.9 |
action_result.data.\*.hop.4.best | string | | 0.9 |
action_result.data.\*.hop.4.hop | string | | 4 |
action_result.data.\*.hop.4.host | string | | dls-b22-link.telia.net |
action_result.data.\*.hop.4.last | string | | 1.0 |
action_result.data.\*.hop.4.loss | string | | 0.0% |
action_result.data.\*.hop.4.raw | string | | 4.|-- dls-b22-link.telia.net 0.0% 3 1.0 0.9 0.9 1.0 0.0 |
action_result.data.\*.hop.4.sent | string | | 3 |
action_result.data.\*.hop.4.stdev | string | | 0.0 |
action_result.data.\*.hop.4.worst | string | | 1.0 |
action_result.data.\*.hop.5.avg | string | | 2.8 |
action_result.data.\*.hop.5.best | string | | 1.2 |
action_result.data.\*.hop.5.hop | string | | 5 |
action_result.data.\*.hop.5.host | string | | dls-b21-link.telia.net |
action_result.data.\*.hop.5.last | string | | 1.6 |
action_result.data.\*.hop.5.loss | string | | 0.0% |
action_result.data.\*.hop.5.raw | string | | 5.|-- dls-b21-link.telia.net 0.0% 3 1.6 2.8 1.2 5.6 2.4 |
action_result.data.\*.hop.5.sent | string | | 3 |
action_result.data.\*.hop.5.stdev | string | | 2.4 |
action_result.data.\*.hop.5.worst | string | | 5.6 |
action_result.data.\*.hop.6.avg | string | | 3.1 |
action_result.data.\*.hop.6.best | string | | 2.5 |
action_result.data.\*.hop.6.hop | string | | 6 |
action_result.data.\*.hop.6.host | string | `ip` | 192.205.37.49 |
action_result.data.\*.hop.6.last | string | | 3.6 |
action_result.data.\*.hop.6.loss | string | | 0.0% |
action_result.data.\*.hop.6.raw | string | | 6.|-- 192.205.37.49 0.0% 3 3.6 3.1 2.5 3.6 0.5 |
action_result.data.\*.hop.6.sent | string | | 3 |
action_result.data.\*.hop.6.stdev | string | | 0.5 |
action_result.data.\*.hop.6.worst | string | | 3.6 |
action_result.data.\*.hop.7.avg | string | | 28.9 |
action_result.data.\*.hop.7.best | string | | 27.9 |
action_result.data.\*.hop.7.hop | string | | 7 |
action_result.data.\*.hop.7.host | string | | cr2.dlstx.ip.att.net |
action_result.data.\*.hop.7.last | string | | 29.8 |
action_result.data.\*.hop.7.loss | string | | 0.0% |
action_result.data.\*.hop.7.raw | string | | 7.|-- cr2.dlstx.ip.att.net 0.0% 3 29.8 28.9 27.9 29.8 1.0 |
action_result.data.\*.hop.7.sent | string | | 3 |
action_result.data.\*.hop.7.stdev | string | | 1.0 |
action_result.data.\*.hop.7.worst | string | | 29.8 |
action_result.data.\*.hop.8.avg | string | | 27.8 |
action_result.data.\*.hop.8.best | string | | 26.9 |
action_result.data.\*.hop.8.hop | string | | 8 |
action_result.data.\*.hop.8.host | string | | attga21crs.ip.att.net |
action_result.data.\*.hop.8.last | string | | 28.1 |
action_result.data.\*.hop.8.loss | string | | 0.0% |
action_result.data.\*.hop.8.raw | string | | 8.|-- attga21crs.ip.att.net 0.0% 3 28.1 27.8 26.9 28.6 0.9 |
action_result.data.\*.hop.8.sent | string | | 3 |
action_result.data.\*.hop.8.stdev | string | | 0.9 |
action_result.data.\*.hop.8.worst | string | | 28.6 |
action_result.data.\*.hop.9.avg | string | | 28.7 |
action_result.data.\*.hop.9.best | string | | 26.7 |
action_result.data.\*.hop.9.hop | string | | 9 |
action_result.data.\*.hop.9.host | string | | cr2.attga.ip.att.net |
action_result.data.\*.hop.9.last | string | | 28.1 |
action_result.data.\*.hop.9.loss | string | | 0.0% |
action_result.data.\*.hop.9.raw | string | | 9.|-- cr2.attga.ip.att.net 0.0% 3 28.1 28.7 26.7 31.3 2.3 |
action_result.data.\*.hop.9.sent | string | | 3 |
action_result.data.\*.hop.9.stdev | string | | 2.3 |
action_result.data.\*.hop.9.worst | string | | 31.3 |
action_result.data.\*.raw | string | | Start: 2019-01-31T05:41:59+0000 HOST: web01 Loss% Snt Last Avg Best Wrst StDev 1.|-- 45.79.12.201 0.0% 3 1.0 0.8 0.6 1.0 0.2 2.|-- 45.79.12.0 0.0% 3 5.6 2.9 0.9 5.6 2.4 3.|-- 45.79.12.9 0.0% 3 7.0 5.1 0.9 7.4 3.6 4.|-- dls-b22-link.telia.net 0.0% 3 1.0 0.9 0.9 1.0 0.0 5.|-- dls-b21-link.telia.net 0.0% 3 1.6 2.8 1.2 5.6 2.4 6.|-- 192.205.37.49 0.0% 3 3.6 3.1 2.5 3.6 0.5 7.|-- cr2.dlstx.ip.att.net 0.0% 3 29.8 28.9 27.9 29.8 1.0 8.|-- attga21crs.ip.att.net 0.0% 3 28.1 27.8 26.9 28.6 0.9 9.|-- cr2.attga.ip.att.net 0.0% 3 28.1 28.7 26.7 31.3 2.3 10.|-- 12.122.154.133 0.0% 3 24.0 25.6 24.0 26.9 1.5 11.|-- ??? 100.0 3 0.0 0.0 0.0 0.0 0.0 12.|-- ??? 100.0 3 0.0 0.0 0.0 0.0 0.0 13.|-- 99.144.25.247 0.0% 3 25.0 24.8 24.6 25.0 0.2 14.|-- 104-186-20-69.lightspeed.chrlnc.sbcglobal.net 0.0% 3 25.3 25.5 25.3 25.9 0.3 15.|-- ??? 100.0 3 0.0 0.0 0.0 0.0 0.0 |
action_result.summary.total_hops | numeric | | 9 |
action_result.message | string | | Total hops: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reverse domain'

Find IPs that resolve to this domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `url` `domain` `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `url` `domain` `host name` | splunk.com |
action_result.data.\*.domain_names.\*.domain | string | `domain` | ip1.splunk.com |
action_result.data.\*.domain_names.\*.ip_addresses | string | `ip` | 204.107.141.245 |
action_result.data.\*.domain_names.\*.ip_count | numeric | | 1 |
action_result.data.\*.ip_addresses.\*.domain_count | numeric | | |
action_result.data.\*.ip_addresses.\*.ip_address | string | | |
action_result.data.\*.raw | string | | host-240.splunk.com,204.107.141.240 sv5vcse01.splunk.com,204.107.141.75 host-241.splunk.com,204.107.141.241 ip1.splunk.com,66.92.1.154 host-242.splunk.com,204.107.141.242 host-243.splunk.com,204.107.141.243 host-244.splunk.com,204.107.141.244 host-245.splunk.com,204.107.141.245 host-246.splunk.com,204.107.141.246 merge.splunk.com,204.107.141.32 exsso.staging.splunk.com,204.107.141.26 mail.splunk.com,206.80.3.69 206.80.3.70 206.80.3.67 206.80.3.68 204.107.141.23 206.80.3.66 66.92.1.49 pfe111-ca-1.mail.splunk.com,64.78.52.101 pfe111-ca-2.mail.splunk.com,64.78.52.102 pfe111-va-3.mail.splunk.com,199.193.202.12 out.east.mail.splunk.com,199.193.200.71 199.193.200.35 199.193.200.70 out.west.mail.splunk.com,64.78.52.96 crashplan.splunk.com,204.107.141.25 exsso.splunk.com,204.107.141.24 jss.splunk.com,204.107.141.110 splunkbot.splunk.com,23.21.104.28 eg0.sv.splunk.com,206.51.38.108 |
action_result.summary | string | | |
action_result.summary.total_domains | numeric | `domain` | 22 |
action_result.summary.total_ips | numeric | | 30 |
action_result.message | string | | Total ips: 30, Total domains: 22 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reverse ip'

Find domains that resolve to this IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 2.2.2.2 |
action_result.data.\*.domain | string | `ip` `domain` | splunk.com |
action_result.data.\*.ip_addresses.\*.domain_count | numeric | | |
action_result.data.\*.ip_addresses.\*.ip_address | string | | |
action_result.data.\*.raw | string | | |
action_result.summary.total_domains | numeric | `domain` | 458 |
action_result.summary.total_ips | numeric | | |
action_result.message | string | | Total domains: 458 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'whois ip'

Execute a whois lookup on the given IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 8.8.8.8 |
action_result.data.\*.Address | string | | 1600 Amphitheatre Parkway |
action_result.data.\*.CIDR | string | | 8.8.8.0/24 |
action_result.data.\*.City | string | | Mountain View |
action_result.data.\*.Comment | string | | The Google Team |
action_result.data.\*.Country | string | | US |
action_result.data.\*.NetHandle | string | | NET-8-8-8-0-1 |
action_result.data.\*.NetName | string | | LVLT-GOGL-8-8-8 |
action_result.data.\*.NetRange | string | | 8.8.8.0 - 8.8.8.255 |
action_result.data.\*.NetType | string | | Reallocated |
action_result.data.\*.OrgAbuseEmail | string | `email` | network-abuse@google.com |
action_result.data.\*.OrgAbuseHandle | string | | ABUSE5250-ARIN |
action_result.data.\*.OrgAbuseName | string | | Abuse |
action_result.data.\*.OrgAbusePhone | string | | +1-650-253-0000 |
action_result.data.\*.OrgAbuseRef | string | `url` | https://rdap.arin.net/registry/entity/ABUSE5250-ARIN |
action_result.data.\*.OrgId | string | | GOGL |
action_result.data.\*.OrgNOCEmail | string | `email` | |
action_result.data.\*.OrgNOCHandle | string | | |
action_result.data.\*.OrgNOCName | string | | |
action_result.data.\*.OrgNOCPhone | string | | |
action_result.data.\*.OrgNOCRef | string | | |
action_result.data.\*.OrgName | string | | Google LLC |
action_result.data.\*.OrgTechEmail | string | `email` | arin-contact@google.com |
action_result.data.\*.OrgTechHandle | string | | ZG39-ARIN |
action_result.data.\*.OrgTechName | string | | Google LLC |
action_result.data.\*.OrgTechPhone | string | | +1-650-253-0000 |
action_result.data.\*.OrgTechRef | string | `url` | https://rdap.arin.net/registry/entity/ZG39-ARIN |
action_result.data.\*.Organization | string | | Google LLC (GOGL) |
action_result.data.\*.OriginAS | string | | |
action_result.data.\*.Parent | string | | LVLT-ORG-8-8 (NET-8-0-0-0-1) |
action_result.data.\*.PostalCode | string | | 94043 |
action_result.data.\*.Ref | string | `url` | https://rdap.arin.net/registry/entity/GOGL |
action_result.data.\*.RegDate | string | | 2000-03-30 |
action_result.data.\*.StateProv | string | | CA |
action_result.data.\*.Updated | string | | 2018-10-24 |
action_result.data.\*.raw | string | | # # ARIN WHOIS data and services are subject to the Terms of Use # available at: https://www.arin.net/whois_tou.html # # If you see inaccuracies in the results, please report at # https://www.arin.net/resources/whois_reporting/index.html # # Copyright 1997-2019, American Registry for Internet Numbers, Ltd. # # start NetRange: 8.0.0.0 - 8.127.255.255 CIDR: 8.0.0.0/9 NetName: LVLT-ORG-8-8 NetHandle: NET-8-0-0-0-1 Parent: NET8 (NET-8-0-0-0-0) NetType: Direct Allocation OriginAS: Organization: Level 3 Parent, LLC (LPL-141) RegDate: 1992-12-01 Updated: 2018-04-23 Ref: https://rdap.arin.net/registry/ip/8.0.0.0 OrgName: Level 3 Parent, LLC OrgId: LPL-141 Address: 100 CenturyLink Drive City: Monroe StateProv: LA PostalCode: 71203 Country: US RegDate: 2018-02-06 Updated: 2018-02-22 Ref: https://rdap.arin.net/registry/entity/LPL-141 OrgTechHandle: IPADD5-ARIN OrgTechName: ipaddressing OrgTechPhone: +1-877-453-8353 OrgTechEmail: ipaddressing@level3.com OrgTechRef: https://rdap.arin.net/registry/entity/IPADD5-ARIN OrgAbuseHandle: IPADD5-ARIN OrgAbuseName: ipaddressing OrgAbusePhone: +1-877-453-8353 OrgAbuseEmail: ipaddressing@level3.com OrgAbuseRef: https://rdap.arin.net/registry/entity/IPADD5-ARIN # end # start NetRange: 8.8.8.0 - 8.8.8.255 CIDR: 8.8.8.0/24 NetName: LVLT-GOGL-8-8-8 NetHandle: NET-8-8-8-0-1 Parent: LVLT-ORG-8-8 (NET-8-0-0-0-1) NetType: Reallocated OriginAS: Organization: Google LLC (GOGL) RegDate: 2014-03-14 Updated: 2014-03-14 Ref: https://rdap.arin.net/registry/ip/8.8.8.0 OrgName: Google LLC OrgId: GOGL Address: 1600 Amphitheatre Parkway City: Mountain View StateProv: CA PostalCode: 94043 Country: US RegDate: 2000-03-30 Updated: 2018-10-24 Comment: Please note that the recommended way to file abuse complaints are located in the following links. Comment: Comment: To report abuse and illegal activity: https://www.google.com/contact/ Comment: Comment: For legal requests: http://support.google.com/legal Comment: Comment: Regards, Comment: The Google Team Ref: https://rdap.arin.net/registry/entity/GOGL OrgTechHandle: ZG39-ARIN OrgTechName: Google LLC OrgTechPhone: +1-650-253-0000 OrgTechEmail: arin-contact@google.com OrgTechRef: https://rdap.arin.net/registry/entity/ZG39-ARIN OrgAbuseHandle: ABUSE5250-ARIN OrgAbuseName: Abuse OrgAbusePhone: +1-650-253-0000 OrgAbuseEmail: network-abuse@google.com OrgAbuseRef: https://rdap.arin.net/registry/entity/ABUSE5250-ARIN # end # # ARIN WHOIS data and services are subject to the Terms of Use # available at: https://www.arin.net/whois_tou.html # # If you see inaccuracies in the results, please report at # https://www.arin.net/resources/whois_reporting/index.html # # Copyright 1997-2019, American Registry for Internet Numbers, Ltd. # |
action_result.summary | string | | |
action_result.summary.CIDR | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'whois domain'

Execute a whois lookup on the given domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | phantom.us |
action_result.data.\*.>>>\_Last_update_of_WHOIS_database | string | | 2019-01-30T09:44:52Z \<<< |
action_result.data.\*.>>>\_Last_update_of_whois_database | string | | |
action_result.data.\*.Admin_Application_Purpose | string | | P1 |
action_result.data.\*.Admin_City | string | | San Francisco |
action_result.data.\*.Admin_Country | string | | US |
action_result.data.\*.Admin_Email | string | `email` | domains@splunk.com |
action_result.data.\*.Admin_Name | string | | Domain Administrator |
action_result.data.\*.Admin_Nexus_Category | string | | C21 |
action_result.data.\*.Admin_Organization | string | | Splunk Operations |
action_result.data.\*.Admin_Phone | string | | +1.4158488400 |
action_result.data.\*.Admin_Postal_Code | string | | 94107 |
action_result.data.\*.Admin_State/Province | string | | CA |
action_result.data.\*.Admin_Street | string | | 270 Brannan Street |
action_result.data.\*.Creation_Date | string | | 2013-08-22T18:03:33Z |
action_result.data.\*.DNSSEC | string | | unsigned |
action_result.data.\*.Domain_Name | string | `domain` | phantom.us |
action_result.data.\*.Domain_Status | string | `domain` | clientUpdateProhibited https://icann.org/epp#clientUpdateProhibited |
action_result.data.\*.Expiration_Date | string | | |
action_result.data.\*.NOTICE | string | | |
action_result.data.\*.Name_Server | string | | ns2.markmonitor.com |
action_result.data.\*.Please_note | string | | |
action_result.data.\*.Referral_URL | string | `url` | |
action_result.data.\*.Registrant_Application_Purpose | string | | P1 |
action_result.data.\*.Registrant_City | string | | San Francisco |
action_result.data.\*.Registrant_Country | string | | US |
action_result.data.\*.Registrant_Email | string | `email` | domains@splunk.com |
action_result.data.\*.Registrant_Name | string | | Domain Administrator |
action_result.data.\*.Registrant_Nexus_Category | string | | C21 |
action_result.data.\*.Registrant_Organization | string | | Splunk Operations |
action_result.data.\*.Registrant_Phone | string | | +1.4158488400 |
action_result.data.\*.Registrant_Postal_Code | string | | 94107 |
action_result.data.\*.Registrant_State/Province | string | | CA |
action_result.data.\*.Registrant_Street | string | | 270 Brannan Street |
action_result.data.\*.Registrar | string | | MarkMonitor, Inc. |
action_result.data.\*.Registrar_Abuse_Contact_Email | string | `email` | abusecomplaints@markmonitor.com |
action_result.data.\*.Registrar_Abuse_Contact_Phone | string | | +1.2083895740 |
action_result.data.\*.Registrar_IANA_ID | string | | 292 |
action_result.data.\*.Registrar_URL | string | `url` | www.markmonitor.com |
action_result.data.\*.Registrar_WHOIS_Server | string | | |
action_result.data.\*.Registry_Admin_ID | string | | C41246181-US |
action_result.data.\*.Registry_Domain_ID | string | `domain` | D41640468-US |
action_result.data.\*.Registry_Expiry_Date | string | | 2021-08-21T23:59:59Z |
action_result.data.\*.Registry_Registrant_ID | string | | C41246181-US |
action_result.data.\*.Registry_Tech_ID | string | | C41246181-US |
action_result.data.\*.Sponsoring_Registrar_IANA_ID | string | | |
action_result.data.\*.Status | string | | |
action_result.data.\*.Tech_Application_Purpose | string | | P1 |
action_result.data.\*.Tech_City | string | | San Francisco |
action_result.data.\*.Tech_Country | string | | US |
action_result.data.\*.Tech_Email | string | `email` | domains@splunk.com |
action_result.data.\*.Tech_Name | string | | Domain Administrator |
action_result.data.\*.Tech_Nexus_Category | string | | C21 |
action_result.data.\*.Tech_Organization | string | | Splunk Operations |
action_result.data.\*.Tech_Phone | string | | +1.4158488400 |
action_result.data.\*.Tech_Postal_Code | string | | 94107 |
action_result.data.\*.Tech_State/Province | string | | CA |
action_result.data.\*.Tech_Street | string | | 270 Brannan Street |
action_result.data.\*.URL_of_the_ICANN_Whois_Inaccuracy_Complaint_Form | string | `url` | https://www.icann.org/wicf/ |
action_result.data.\*.Updated_Date | string | | 2018-10-14T17:56:49Z |
action_result.data.\*.Whois_Server | string | | |
action_result.data.\*.raw | string | | Domain Name: phantom.us Registry Domain ID: D41640468-US Registrar WHOIS Server: Registrar URL: www.markmonitor.com Updated Date: 2018-10-14T17:56:49Z Creation Date: 2013-08-22T18:03:33Z Registry Expiry Date: 2021-08-21T23:59:59Z Registrar: MarkMonitor, Inc. Registrar IANA ID: 292 Registrar Abuse Contact Email: abusecomplaints@markmonitor.com Registrar Abuse Contact Phone: +1.2083895740 Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited Domain Status: clientUpdateProhibited https://icann.org/epp#clientUpdateProhibited Registry Registrant ID: C41246181-US Registrant Name: Domain Administrator Registrant Organization: Splunk Operations Registrant Street: 270 Brannan Street Registrant Street: Registrant Street: Registrant City: San Francisco Registrant State/Province: CA Registrant Postal Code: 94107 Registrant Country: US Registrant Phone: +1.4158488400 Registrant Phone Ext: Registrant Fax: Registrant Fax Ext: Registrant Email: domains@splunk.com Registrant Application Purpose: P1 Registrant Nexus Category: C21 Registry Admin ID: C41246181-US Admin Name: Domain Administrator Admin Organization: Splunk Operations Admin Street: 270 Brannan Street Admin Street: Admin Street: Admin City: San Francisco Admin State/Province: CA Admin Postal Code: 94107 Admin Country: US Admin Phone: +1.4158488400 Admin Phone Ext: Admin Fax: Admin Fax Ext: Admin Email: domains@splunk.com Admin Application Purpose: P1 Admin Nexus Category: C21 Registry Tech ID: C41246181-US Tech Name: Domain Administrator Tech Organization: Splunk Operations Tech Street: 270 Brannan Street Tech Street: Tech Street: Tech City: San Francisco Tech State/Province: CA Tech Postal Code: 94107 Tech Country: US Tech Phone: +1.4158488400 Tech Phone Ext: Tech Fax: Tech Fax Ext: Tech Email: domains@splunk.com Tech Application Purpose: P1 Tech Nexus Category: C21 Name Server: ns3.markmonitor.com Name Server: ns7.markmonitor.com Name Server: ns5.markmonitor.com Name Server: ns1.markmonitor.com Name Server: ns6.markmonitor.com Name Server: ns4.markmonitor.com Name Server: ns2.markmonitor.com DNSSEC: unsigned URL of the ICANN Whois Inaccuracy Complaint Form: https://www.icann.org/wicf/ >>> Last update of WHOIS database: 2019-01-30T09:44:52Z \<<< For more information on Whois status codes, please visit https://icann.org/epp |
action_result.summary | string | | |
action_result.summary.Domain | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ping domain'

Ping a domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Host FQDN such as www.hackertarget.com | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | google.com |
action_result.data.\*.sent | string | | |
action_result.data.\*.failed | string | | |
action_result.data.\*.succeeded | string | | |
action_result.data.\*.raw | string | | Starting Nping 0.7.70 ( https://nmap.org/nping ) at 2019-01-31 07:46 UTC SENT (0.0091s) ICMP [104.237.144.6 > 172.217.10.110 Echo request (type=8/code=0) id=667 seq=1] IP [ttl=64 id=40823 iplen=28 ] RCVD (0.2114s) ICMP [172.217.10.110 > 104.237.144.6 Echo reply (type=0/code=0) id=667 seq=1] IP [ttl=58 id=0 iplen=28 ] SENT (1.0095s) ICMP [104.237.144.6 > 172.217.10.110 Echo request (type=8/code=0) id=667 seq=3] IP [ttl=64 id=40823 iplen=28 ] RCVD (1.0274s) ICMP [172.217.10.110 > 104.237.144.6 Echo reply (type=0/code=0) id=667 seq=3] IP [ttl=58 id=0 iplen=28 ] SENT (2.0107s) ICMP [104.237.144.6 > 172.217.10.110 Echo request (type=8/code=0) id=667 seq=3] IP [ttl=64 id=40823 iplen=28 ] RCVD (2.0474s) ICMP [172.217.10.110 > 104.237.144.6 Echo reply (type=0/code=0) id=667 seq=3] IP [ttl=58 id=0 iplen=28 ] SENT (3.0115s) ICMP [104.237.144.6 > 172.217.10.110 Echo request (type=8/code=0) id=667 seq=4] IP [ttl=64 id=40823 iplen=28 ] RCVD (3.0673s) ICMP [172.217.10.110 > 104.237.144.6 Echo reply (type=0/code=0) id=667 seq=4] IP [ttl=58 id=0 iplen=28 ] Max rtt: 202.319ms | Min rtt: 18.054ms | Avg rtt: 78.107ms Raw packets sent: 4 (112B) | Rcvd: 4 (184B) | Lost: 0 (0.00%) Nping done: 1 IP address pinged in 3.07 seconds |
action_result.summary | string | | |
action_result.summary.failed | string | | |
action_result.summary.received | string | | |
action_result.summary.sent | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ping ip'

Ping an IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | Host ip | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 8.8.8.8 |
action_result.data.\*.sent | string | | |
action_result.data.\*.failed | string | | |
action_result.data.\*.succeeded | string | | |
action_result.data.\*.raw | string | | Starting Nping 0.7.70 ( https://nmap.org/nping ) at 2019-01-31 07:48 UTC SENT (0.0045s) ICMP [104.237.144.6 > 8.8.8.8 Echo request (type=8/code=0) id=54952 seq=2] IP [ttl=64 id=33659 iplen=28 ] RCVD (0.2052s) ICMP [8.8.8.8 > 104.237.144.6 Echo reply (type=0/code=0) id=54952 seq=2] IP [ttl=124 id=59028 iplen=28 ] SENT (1.0045s) ICMP [104.237.144.6 > 8.8.8.8 Echo request (type=8/code=0) id=54952 seq=3] IP [ttl=64 id=33659 iplen=28 ] RCVD (1.0212s) ICMP [8.8.8.8 > 104.237.144.6 Echo reply (type=0/code=0) id=54952 seq=3] IP [ttl=124 id=59332 iplen=28 ] SENT (2.0065s) ICMP [104.237.144.6 > 8.8.8.8 Echo request (type=8/code=0) id=54952 seq=3] IP [ttl=64 id=33659 iplen=28 ] RCVD (2.0411s) ICMP [8.8.8.8 > 104.237.144.6 Echo reply (type=0/code=0) id=54952 seq=3] IP [ttl=124 id=60050 iplen=28 ] SENT (3.0082s) ICMP [104.237.144.6 > 8.8.8.8 Echo request (type=8/code=0) id=54952 seq=4] IP [ttl=64 id=33659 iplen=28 ] RCVD (3.0612s) ICMP [8.8.8.8 > 104.237.144.6 Echo reply (type=0/code=0) id=54952 seq=4] IP [ttl=124 id=60422 iplen=28 ] Max rtt: 200.698ms | Min rtt: 16.681ms | Avg rtt: 76.145ms Raw packets sent: 4 (112B) | Rcvd: 4 (184B) | Lost: 0 (0.00%) Nping done: 1 IP address pinged in 3.06 seconds |
action_result.summary | string | | |
action_result.summary.failed | string | | |
action_result.summary.received | string | | |
action_result.summary.sent | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'geolocate ip'

Geolocate an IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | Host ip | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 1.101.103.48 8.8.8.8 |
action_result.data.\*.city_name | string | | |
action_result.data.\*.country_name | string | | United States |
action_result.data.\*.ip | string | `ip` | 1.101.103.48 8.8.8.8 |
action_result.data.\*.latitude | string | | 37.5112 37.751 |
action_result.data.\*.longitude | string | | 126.9741 -97.822 |
action_result.data.\*.raw | string | | IP Address: 1.101.103.48 Country: Republic of Korea State: City: Latitude: 37.5112 Longitude: 126.9741 IP Address: 8.8.8.8 Country: United States State: City: Latitude: 37.751 Longitude: -97.822 |
action_result.data.\*.state_name | string | | |
action_result.summary | string | | |
action_result.summary.latitude | string | | |
action_result.summary.longitude | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'geolocate domain'

Geolocate a domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Host fqdn ie. www.hackertarget.com | string | `url` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `url` `domain` | google.com |
action_result.data.\*.city_name | string | | Bluffdale |
action_result.data.\*.country_name | string | | United States |
action_result.data.\*.ip | string | `ip` | 216.58.217.110 |
action_result.data.\*.latitude | string | | 40.4954 |
action_result.data.\*.longitude | string | | -111.9444 |
action_result.data.\*.raw | string | | IP Address: 216.58.217.110 Country: United States State: Utah City: Bluffdale Latitude: 40.4954 Longitude: -111.9444 |
action_result.data.\*.state_name | string | | Utah |
action_result.summary | string | | |
action_result.summary.latitude | string | | |
action_result.summary.longitude | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
