# Swimlane Splunk Add-on

Swimlane's adaptive response action creates Swimlane cases that are pre-populated with Splunk alert and notable event data. Swimlane then automatically applies workflow, automation and orchestration to the cases, enriching them and performing actions against any third-party systems. This includes initiating additional Splunk searches and updating notable events in Splunk.

Additionally, this add-on includes the command Splunk "pushtoswimlane" which allows to create a Splunk workflow action and send an event.

For additional assistance, please contact support@swimlane.com.

## Configuration

You can send alert data to up to three separate Swimlane instances with each action. This allows you to conveniently push to production, staging, and development instances with one action.

### Global Configuration

Define the connection info and credentials for your Swimlane instances in Global Configuration.

1. In the top left corner of the Splunk interface, click the **app** dropdown menu and select **Swimlane**.

2. This opens the configuration page, where you define the host, username, and password for up to three Swimlane instances.

### Alert Configuration

1. Once you have created an alert, go to the alert page and click **Edit** (next to the **Actions** field).

2. At the bottom of the window, select **Add Actions** -> **Push Alerts to Swimlane**, then fill out the
fields appropriately.

  Setup instructions for `Custom Field Mappings`, `Automappings` and `Extra Fields` are in the next section

### Mapping configuration

Use `Automapping` for the initial setup.

1. In the Swimlane application, create a JSON field with the *field key* `splunkrawjson` and a multi-line text field with the *field key* `splunkfieldlist`. Additionally, you can add a multi-line text field with the *field key* `splunkalertname` and/or `splunksearchname`.

  These two fields can be used to see the data being pushed to Swimlane.

2. Trigger the alert so that the action runs. Then, check Swimlane to make sure records were created in
the desired application.

  If no records were created, check the logs (described in the **Logging** section below) to debug.

3. Open one of the records that was created in Swimlane.  The fields in `splunkfieldlist` are the fields that are available for mapping.  You can use `splunkrawjson` to see the value each field contains.

4. For each field that you want to push to Swimlane, use either `Automappings` or `Custom Field Mappings` as described below.

#### Automapping

If you use `automapping`, Splunk fields will populate a Swimlane field with the same field key (if it exists). Swimlane recommends that you map this way since you can still display the information however you want in Swimlane by setting the field display name.

#### Custom Field Mappings

If you cannot set the Swimlane field key to match the Splunk field, you can use `Custom Field Mappings` to match Splunk fields to Swimlane fields. `Custom Field Mappings` is a JSON dictionary where the *keys* are splunk field names and the *values* are Swimlane field keys.  

For example:

```JSON
{
  "Splunk field name 1": "Swimlane field key 1",
  "Splunk field name 2": "Swimlane field key 2"
}
```

#### Extra Fields Input Mapping

In some scenarios, you may want to send information to Swimlane that is not contained in the alert return.
Additional information can be sent using the Extra Fields input. The input must be valid JSON. Only keys that exists in the Swimlane application will be sent. For example:

```JSON
{
    "Swimlane field 1": "$controller$",
    "Swimlane field 2": "Some static value"
}
```

**Note:** All Swimlane field types are supported and Splunk fields containing lists will be translated into list fields in Swimlane.

### 'pushtoswimlane' Command

In certain scenarios, you might want to use the custom command 'pushtoswimlane' to send an event to Swimlane. An example scenario for this is when you are creating a custom workflow action.

Possible parameters:

```
--sw_target_config | Required. Possible values are prod, staging or dev
--sw_appname | Required. Swimlane application name in the host
--sw_pushmethod | Defaults to add. Possible values are add or addupdate
--sw_updatekey | Optional. In case of using the pushmethod 'addupdate', records in swimlane will be looked using this key
--sw_custommapping | Optional. See custom mapping section
--sw_sendevent | Defaults to True. True or False. If true, the eventid parameter must be provided
--eventid | Optional. Required when sw_sendevent is True. The event ID to be sent
--connection_timeout | Optional. Defaults to 60 seconds.
--sw_extrafields | Optional. See custom mapping section
```

Examples:

Add an event:
```
| pushtoswimlane  --sw_target_config=prod --sw_appname=Splunk --eventid=$event_id$
```

Add or update an event:

```
| pushtoswimlane  --sw_target_config=staging --sw_appname=Splunk --sw_sendevent=True --sw_pushmethod=addupdate --sw_updatekey=rule_id --eventid=$event_id$ --sw_extrafields="{\"test_extra_field\":\"this is the value\"}"
```

Add without sending the event:

```
| pushtoswimlane  --sw_target_config=dev --sw_appname=Splunk --sw_sendevent=False --sw_pushmethod=add --eventid=$event_id$ --sw_extrafields="{\"test_extra_field\":\"this is the value\", \"another_field\":\"this is another value\"}" --sw_custommapping="{\"splunk_field\":\"swimlane_field\"}"
```

The query the addon uses to search for the event is the following:

```
search `notable_by_id( + event_id + )` | search NOT `suppression` | head 1 | fields *)
```


### Create a Workflow Action With the 'pushtoswimlane' Command

Use the custom command 'pushtoswimlane' to create a workflow action and avoid having to trigger an adaptive response action when you want to send a notable event to Swimlane

From **Settings,** select **Fields,** then **Workflow actions** and finally, **New Workflow Action.**

The inputs listed below must have the following configuration:

```
Action type: search
Search string: Swimlane 'pushtoswimlane' command. Ex: | pushtoswimlane  --sw_target_config=prod --sw_appname=Splunk --eventid=$event_id$
Run in app: search

```

## Logging

This Splunk add-on provides granularity over the amount of information it logs. To find logs for this add-on, either search directly for them in Splunk, or access the log file on the Splunk instance. To find them in the Splunk search, use the following search string:

For alert actions:

`index=_internal OR index=cim_modactions OR index=* source="*push_alerts_to_swimlane_modalert.log"`

For Commands:

`index=_internal OR index=cim_modactions OR index=* source="*pushtoswimlane_command.log"`

To access the log file directly:

`{Splunk root folder}/var/log/splunk/push_alerts_to_swimlane_modalert.log`
or
`{Splunk root folder}/var/log/splunk/pushtoswimlane_command.log`

If multiple executions happen concurrently, you can distinguish which log message belongs to which execution using the `pid` logged in each message.

To find the general logs that Splunk generates, navigate to **Settings,** **Alert actions,** and then click **View log events** for the **Push Events to Swimlane** action.

## Limitations and Recommendations

There are a few known limitations that might occur, especially after upgrading the Swimlane TA from 1.x to 2.x.

**Note:** In order to upgrade from Splunk from 7.X to 8.X, you will be required to upgrade Swimlane TA.

After upgrading Splunk to version 8.X, you are required to upgrade Swimlane TA to version 2.x. In order to avoid possible errors, it is important to do a clean uninstall and install of the Swimlane TA and not simply use the upgrade feature within Splunk.

### Errors Related to Python 2

In general, we have seen Python 2 related errors occurring because of a corrupted environment.

Here are some examples:

`ModularActionException: Invalid parameter for adhoc modular action`

  This error is generated because of corrupted config files. Even when the .conf files seem correct, after utilizing the upgrade feature, some files might linger behind and will be executed by Splunk, instead of the correct and new ones.

`TA hangs when using makejson instead of mkjson`

  This error happens when the environment is corrupt after an unsuccessfully upgrade of the Swimlane TA. Splunk is using files from the previous version and running some files using Python 2.7 instead of the default version of 3.6

`Missing Python Libraries`

  While the Swimlane TA has safeguards against missing libraries just in case, it is possible that after a major upgrade the platform does not detect them. Errors relating to importing Python 2 libraries (e.g. Urllib2) are a common signal of a corrupt environment.

### Splunk Version 8.2.2

Splunk version 8.2.2 has the following bug:

Error: `pendulum.tz.zoneinfo.exceptions.InvalidTimezone: Invalid timezone "/etc/localtime"`

This bug renders the Swimlane TA incompatible with version 8.2.2 as it uses the timezone OS dependencies within its code.

Splunk version 8.2.2 is built using Red Hat's "ubi-minimal:8.4-210" version. Version "ubi-minimal:8.4-210" contains a [bug](https://bugzilla.redhat.com/show_bug.cgi?id=1903219) where the `tzdata` package gets installed, but the `/usr/share/zoneinfo` folder does not get correctly deployed.

Splunk fixed this issue in [version 8.2.3](https://github.com/splunk/docker-splunk/blob/a7d8ac2002b142dea597ca94559b20f9cc8a4bd1/base/redhat-8/install.sh#L37). Upgrading to 8.2.3 or downgrading away from 8.2.2 will fix this error.

### Guidelines When Doing a Major Upgrade

Major upgrades have a chance of leaving behind configuration files that Splunk will attempt to pick up later. This causes a set of issues, mostly relating to Python 2 or task execution in general.

The following steps are guidelines as to what constitutes a clean uninstall and later install:

1. Stop all alerts that are using any Swimlane actions.

2. All Swimlane TA directories must be completely deleted to avoid lingering configuration files that get picked up by Splunk later on.

3. Restart Splunk or at least Splunk Search Heads.

4. Install the new Swimlane TA version.

5. Delete all alerts using the old Swimlane TA.

6. Configure new Splunk alerts to use the new Swimlane TA.
