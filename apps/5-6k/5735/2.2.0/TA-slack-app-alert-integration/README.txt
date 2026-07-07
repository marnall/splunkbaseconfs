# Slack App Alert Integration

## Introduction

The Slack App Alert Integration TA is meant to integrate with Slack Apps, the new way
of communicating with Slack in favor of the deprecated Incoming Webhooks integration.
The Incoming Webhooks integration allows sending messages to multiple channels which
is highly flexible. A Slack App has to join a channel before it can post messages in it,
but using the correct configuration in combination with this TA, a Slack App can join a
channel if needed and post messages to it with customized bot name and emoji icon.

## Prerequisites

An installed Slack App in your Slack Workspace:

- Create an App. The app needs a channel to post to, but this is irrelevant for integrating
with the TA, so choose any channel you like.
- Configure the scopes for OAuth & Permissions. Grant the following scopes: channels:join,
channels:read, chat:write, chat:write.customize, groups:read, im:read, incoming-webhook, mpim:read
- Copy the Bot User OAuth Token
- Install the App (if you're not the workspace owner, you probably have to request an install first).

## Installation

Install this TA on your Splunk Search Heads.

## Configuration

After installation of the TA, navigate to the Slack App Alert Integration app in Splunk, and under Add-on Settings, paste the Bot User OAuth token in the Token field. The Base URL can be left as default, provided that your Search Heads have access to it. There is no proxy configuration yet in this version of the TA. Click Save.

When the TA is configured, you can create an alert using the new Slack App Alert Integration alert action, by configuring its fields:

- Channel: the name of the channel to post messages to (without leading #)
- Emoji: optional icon to use (like :exclamation: or :alien:)
- Bot username: the name that will be used by the Slack App to post the messages with.
- Message: the content to post
- Auto-join channel: Either True (default) or False. If true, the App will be automatically added to the channel (only if needed).
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-slack-app-alert-integration/bin/ta_slack_app_alert_integration/aob_py3/setuptools/gui.exe: this file does not require any source code
