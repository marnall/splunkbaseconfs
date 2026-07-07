# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.10.1] 2023-01-11
* More descriptive and actionable error message when Error

## [0.10.0] 2021-07-15
* Upgrade dependencies (dateutil, splunklib, IPy)
* Make it python 2/3 compatible
* Compatibility with Splunk 8
* Drop Splunk 7.x or earlier supoort

## [0.9.0] 2020-01-31
* Bug fixes

## [0.8.0] 2018-05-22
* Improve operation of `investigatefilter` search command

## [0.7.9] 2018-05-22
* Compatibility with Splunk 7

## [0.6.5] 2018-02-05
* Exclusion list feature added
* Umbrella Top 1 Million Limit feature added

## [0.6.2] 2017-04-24
* Encrypt proxy credentials

## [0.6.1] 2017-03-28
* Fix get api key

## [0.6.0] 2017-03-28
* Saving the api key encrypted, as per Splunk's SOP.
* Reading report as a stream instead of loading all into memory.
* Fix proxy use in investigate filter. 

## [0.5.3] 2017-03-06
* Added authentication to proxy (http only).
* Added max threat score.
* Added ttl statistics.

## [0.5.2] 2017-02-23
* Added support for nonstandard Splunk host and ports
* Fixed app context to ensure app runs in correct context. 
* Added more logging statements. 

## [0.5.1] 2017-01-19
* It is no longer necessary to specify a username/password to use the Investigate
  add-on.

## [0.5.0] 2017-01-05
* Added the `investigatefilter` search command. See the README for more detail.
* Added the ability to use a proxy to query the Investigate API. It can be
  configured in the setup page.
* Added log rotation and size limits for the various logs that the add-on keeps.

## [0.4.0] 2016-12-12
* Added KV store pruning. You can now manage the maximum size of the Investigate
  add-on's KV stores, either by time or by row size. See the updated README
  for more detail.
* Branding changes. The app's color is now blue, and is now referred to as
  "Cisco Umbrella Investigate".
* Fixed a bug where some row entries were skipped entirely, due to missing fields
  in the response from the API.

## [0.3.0] 2016-11-21

### IP and file hash data
In addition to domain/host names, the add-on now also queries the Investigate
API for IP addresses and file hashes. You can set up your saved search so that
it extracts domains, IP addresses, and hashes (in the form of a hex representation
of a MD5, SHA1, or SHA256 hash) into their own fields. Then in the setup page of
the Investigate add-on, you can add each field you wish to query the Investigate API
for in the "Fields" box, in a comma-separated format, e.g.

```
cs_host, cs_hash
```

#### KV Store Collections names have changed
Now that there are multiple KV store collections, the naming convention for the
collections have changed. Previously, the name of the collection for domain data
was called `opendns_investigate_store` and the lookup was called
`opendns_investigate_lookup`. These have been renamed to both be called
`investigate_domains`. See the updated `README` for more detail on the other KV
store collections. If you are upgrading, in order to avoid having a dangling
KV store collection, **we recommend first uninstalling the Investigate Add-on before
upgrading**.
