# ![App icon](/static/app/radware_cwaf_enrichment/appIcon.png) SplunkApp for Radware Cloud WAF Enrichment

Welcome to the SplunkApp for Radware Cloud WAF Enrichment.

This app provides an API integration with the Radware Cloud WAF Rest API to enrich your Splunk data with additional
information about objects in Radware Cloud WAF. This can be helpful in correlating logs from WAF and other sources with metadata that is not available in the log stream.

The app includes a set of commands that can be used to import data from the API into Splunk KV Store. This data can then be used to enrich your data using the `lookup` command.

Some base transforms are included to demonstrate how to use the data within a lookup. Feel free to configure your own lookups.

Currently, the app supports the following objects from Radware Cloud WAF:
* `applications` - List of applications in the tenant from /v1/gms/applications

Using the `radwarecwafimportremote` command, you can import all objects from the API into Splunk KV Store.
This import will also clean up any objects that are no longer in the API.

Using `radwarecwaflistremote` you can list all objects in a given class (e.g. applications) directly from the Remote API. Use this sparingly as it will execute a full export on every execution. Use the import option when data needs to be accessed frequently.

*This SplunkApp is not written by Radware or Splunk*

### Requirements
* Splunk 8.1.0 or later - or SplunkCloud
* Install on SearchHead

### Permissions
Configuring the applications is restricted to administrators or those with the `admin_all_objects` capability.

Permissions for the app have been configured in a pre-packaged role called `radware_cwaf_enrichment_admin`.
In addition to the custom permissions, the role also includes the `list_storage_passwords` capability which is required to access API credentials dutring execution.

## Generating Commands

### Remote Actions

* radwarecwaflistremote - List all remote objects in a given class (e.g. applications)
* radwarecwafimportremote - Import all remote objects in a given class (e.g. applications) into Splunk KV Store

## Configuration

* `radware_cwaf_enrichment.conf` - Contains the configuration for the app. Use the provided SplunkWeb GUI for easier
  management.

### Settings

* `log_level`   - The log level for the app. Valid values are `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`
* `object_list` - A comma-separated list of objects to collect from the API. Valid values are `applications`
* `use_proxy`   - Whether to use a proxy to connect to the API. Valid values are `true` or `false`
* `proxy_host`  - The host of the proxy to use. Only used if `use_proxy` is set to `true`
* `proxy_port`  - The port of the proxy to use. Only used if `use_proxy` is set to `true`
* `proxy_user`  - The username for the proxy. Only used if `use_proxy` is set to `true`
* `proxy_pass`  - The password for the proxy. Only used if `use_proxy` is set to `true`

### Credentials

Credentials are stored as multi-value settings inside the configuration file.
The Setup interface in Splunk Web is the easiest way to configure credentials.

* `credential.[index].name`         - The friendly name connection.
* `credential.[index].username`     - The username for the API.
* `credential.[index].password`     - Stores a pointer to a storage-passwords object. e.g. credential-2-password:mock_user_radware_prod11sss:
* `credential.[index].password_set` - If a password exists in the passwords.conf file this should be set to 1.
* `credential.[index].tenant_id`    - The Radware GUID of the tenant for this connection

Note: Passwords are stored passwords.conf file. The password is encrypted using the Splunk key and follows the format
`credential:credential-[credentialindex]-password:[username]:`

### Mock Mode.
This app include a mocking mode which will provide fake data for testing purposes.
To use the mock-data and avoid hitting the API, set the username for a credential to start with `mock_` and the app will use the mock data. 