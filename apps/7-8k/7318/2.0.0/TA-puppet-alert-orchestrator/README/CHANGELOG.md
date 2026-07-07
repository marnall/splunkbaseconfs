# Release Notes

### Puppet Alert Orchestrator add-on for Splunk

## Version 2.0.0

**Breaking Changes**:

  * This release no longer uses the Splunk Add-on Builder (AOB) framework. The add-on has been fully migrated to the [Splunk UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/).
  * The `ConfigMigrationHandler` has been removed. Existing credential store entries must be re-entered after upgrading from v1.x.
  * The `aob_py3/` vendored Python library directory has been removed. Runtime dependencies are now installed into `lib/` at build time via pip.

**New Features**:

  * **Verify SSL Certificate**: New optional setting in the Add-on Settings tab to enable SSL certificate verification for connections to Puppet Enterprise. Disabled by default to support self-signed certificates common in PE installations.

**Fixes**:

  * Fixed `is not ''` comparisons across all alert action helper and action files, which caused `SyntaxWarning` errors and script failures on newer versions of Splunk.
  * Alert action forms now correctly pre-populate default values: `puppet_environment` defaults to `production` and `action_target` defaults to `$result.host$`.

## Version 1.0.1

**Fixes**:

  * Updated add-on for compatibility with [Splunk Add-on Builder v4.2.0](https://splunkbase.splunk.com/app/2962).

## Version 1.0.0

**Breaking Changes**:

  * This release of the Puppet Alert Orchestrator add-on for Splunk no longer utilizes Splunk's Python2 SDK. As such this version will only work on Splunk Enterprise 8.x+ and Splunk Cloud.
  * Removed a number of "Add-on settings" that were already configurable within the actions.
  * "Run a Bolt Task" is now "Run a Puppet Task".

**New Features**:

  * **Orchestrator Actions**:
    * All new dashboard powered by a custom input which uses the configured account credentials to query PE for Plans and Tasks available to that particular RBAC user.
      * By default the custom input script only checks for actions available in the `production` environment.
  * Added "Run a Puppet Plan" **Action**.
    * New action added that allows user to trigger Puppet Plans. When configuring the action, the Plan name is populated with the same data as the Orchestrator Actions dashboard.
  * "Run a Puppet Task" **Action**.
    *  When configuring the action, the Task name is populated with the same data as the Orchestrator Actions dashboard.

---

### Puppet Alert Actions

## Version 0.6.0

**Fixes**:

  * In a distributed Splunk installation, settings specific to this add-on were not properly replicated across the cluster. This release adds a default `server.conf` file with an `[shclustering]` stanza to ensure the proper settings are replicated.

## Version 0.5.0

**Notes**:

  * This is an initial release of the Puppet Alert Actions App. This contains just the alert actions needed to retrieve detailed reports or run tasks in Puppet Enterprise. This App is only for Puppet Enterprise users.
