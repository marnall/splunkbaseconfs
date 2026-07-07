# Upgrade Planner for Splunk Add-on for Windows

# This app is based pramarily on this link:
# https://docs.splunk.com/Documentation/WindowsAddOn/6.0.0/User/Upgrade

# It tells you everything that you need to know to ensure that
# you do not experience breakage/outage when upgrading to v5 or v6
# of the "Splunk Add-on for Windows" (AKA "Splunk_TA_windows").

# 1: Deploy app to your Monitoring Console
# 2: Follow the suggestions in the first 2 panels to clear the other panels.
# 3: Upgrade the apps.
# 4: PROFIT!

### Perrequisites

The pre-requisites for the add-on are as follows;

```
All Nodes: Splunk version 6.6 or higher
```

### Installing & Deploying the App

Installation instructions are as follows;
1) Ensure that Splunk everywhere is updated to Splunk version 6.0 or later.
Deploying to earlier versions is silly because Splunk_TA_windows v5*+
is not compatible for those versions.
2) Deploy app.
3) Use the dashboards to make changes to ensure a clean upgrde.
4) Upgrade the Splunk_TA_windows app.

```
Splunk Monitoring Console:
App works best on Monitoring Console but you should run it on every search head.
```

### Testing & Troubleshooting

This app consists of 1 dashboard and it either works or doesn't (it will).

## Authors

* **Gregg Woodcock** - Woodcock@Splunxter.com
