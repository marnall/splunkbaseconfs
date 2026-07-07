# Lookout Mobile Threat Defense for Splunk

Integrate Lookout Mobile Threat Defense telemetry into Splunk SIEM.

## 1.x to 2.0 Migration

As the 2.0 version of the Lookout Mobile Threat Defense Splunk plugin is a completely app, re-designed from the ground up, there isn't an automatic process
for upgrading 1.x versions of the plugin to the new 2.0 version.

### Migration Process

_Base assumption_: Customer has version 1.5.1 (latest) of the now legacy plugin installed and functioning normally.

1. From the Splunk web console home page, click the `Find More Apps` button at the bottom of the left hand menu.
1. Type `Lookout Mobile Threat Defense for Splunk` in the search bar. This should display one Lookout application as the legacy version will be hidden from the Splunkbase store.
1. Follow the installation prompts. No reboot is required on installing the 2.0 app.
1. Now you should see two applications installed labeled `Lookout Mobile Threat Defense for Splunk`. From the Manage Apps page you can see that the 1.5.1 version is named `Lookout_Mobile_Security_Splunk_App` and the new 2.0.0 version is named `lookout_mobile_threat_defense_for_splunk`.
1. Open the 2.0.0 application and configure connection(s) to duplicate all existing 1.5.1 connections.
1. Start the new connector with stream position set to `now`. This will result in each new lookout event being duplicated in Splunk. Events can be differenciated by the `source` field, new events will come in with `source=lookout_v2`.
1. Once Satisfied that the new connector is producing events, switch any `source` based alerts, dashboards, etc. from `source=lookout` to `source=lookout_v2`
1. With all Splunk alerts, dashboards, etc. transfered over to `lookout_v2`, feel free to uninstall the 1.5.1 version of the plugin.

# Binary File Declaration
bin/lib/charset_normalizer/md__mypyc.cpython-39-x86_64-linux-gnu.so: Adding this to skip appinspect's source check as this file comes from
a dependency not in our control
