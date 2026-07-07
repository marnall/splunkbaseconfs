# Instructions

## Prerequisites

Before installing this app, you should ensure you running Splunk 8 or higher, as it is only compatible with Python 3.

## Install

This app should be installed only on a Splunk Search Head. You will not need to restart Splunk after installing the app.

## Configuration 

There is no additional configuration necessary for this app.

## Usage

This app provides a custom search command, `semvercmp`, which can be invoked as follows:

```
... | semvercmp outputfield=semver_result actual_version minimum_version_for_success
```

This will add a `semver_result` field to events with the following values:

  * If `actual_version` is greater than `minimum_version_for_success`, the value is 1
  * If `actual_version` is less than `minimum_version_for_success`, the value is -1
  * If `actual_version` is equal to `minimum_version_for_success`, the value is 0

# Known Issues

There are no known issues at this time. 

# Upgrade

No special instructions for upgrading this app to a newer version.

# Help

While this app is not formally supported, the developer can be reached at smcmaster@splunk.com (OR in splunk-usergroups slack, @iamthemcmaster). Responses are made on a best effort basis. Feedback is always welcome and appreciated!

Learn more about splunk-usergroups slack here: https://docs.splunk.com/Documentation/Community/current/community/Chat#Join_us_on_Slack