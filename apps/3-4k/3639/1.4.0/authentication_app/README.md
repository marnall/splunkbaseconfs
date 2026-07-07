# Authentication App for Splunk

## Deprecation Warning!!!
__This app has been deprecated. There will be no new development or bug fixes. It has been replaced by the [Aplura Authentication App for Splunk](https://splunkbase.splunk.com/app/4227/).__

## Overview
Most sourcetypes contain authentication events of some sort. This app provides Splunk dashboards, forms, and reports which can be used to explore your authentication events across your different sourcetypes.

To do this, the app relies on the Splunk Common Information Model (CIM) for authentication events. This means that the app can report on any authentication data, as long as it has been on-boarded properly, and is available through the [Authentication data model](http://docs.splunk.com/Documentation/CIM/latest/User/Authentication).

## A note on Splunk Data Model Acceleration and Disk Space
This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

## A note on the Splunk Common Information Model
As mentioned above, the app uses the CIM for authentication events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

## Available Dashboards

### Overview
Provides a starting point for exploring your authentication events. Most panels will drill-down to other pages in the application.

### User Profile
A view based on a single user's authentication activity.

### Source Profile
Authentication events which appear to come from a single source.

### Destination Profile
Authentication events where users are authenticating against the same destination.

### App Profile
Panels which focus on events which all are from the same application (win:local, ssh, vpn, etc).

### Action Profile
A view based in the action ("success", "failure", "unknown") from the authentication event.

### Default Authentication
Reports on default authentication occurring in the environment. See the `Customization` section of this document for more information about how this dashboard can be customized for your deployment.

### Privileged Authentication
Reports on privileged authentication occurring in the environment. See the `Customization` section of this document for more information about how this dashboard can be customized for your deployment.

### Authentication Search (Advanced)
A form for finding events based on various field values.

### Authentication Geography (Advanced)
People like maps. This dashboard needs more development.

### Sourcetypes (Advanced)
Information about the sourcetypes which are present in the accelerated data.


## Prerequisites

### Splunk Versions
This app has been tested with Splunk versions 6.6. This app should be installed on the same search head on which the Authentication data model has been accelerated.

### Splunk Common Information Model Add-on
This app depends on data models included in the Splunk Common Information Model Add-on, specifically the "Authentication" data model. Please review the information on [installing and using the Splunk Common Information Model Add-on](http://docs.splunk.com/Documentation/CIM/latest/User/Install) and information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.8 of the CIM add-on.

### Data model Acceleration on the Authentication data model
In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the `Authentication` data model must be accelerated. Information on how to enable acceleration for the `Authentication` data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

## Installation
This app should be installed on a search head where the `Authentication` data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

### Simple Installation Process
1. Make sure the field extractions and tags on your authentication events are correct.
2. Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).
4. Install the Authentication App for Splunk.
5. Enable accelerations on the `Authentication` data model (skip if you are installing on an ES search head).
6. Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

## Customization
There are two macros which may be customized to help this app fit into your environment, and make use of other lookups (possibly the ones from the Splunk App for Enterprise Security). In both of these cases, the result is that the search in the macro should output a `user` field which contains the users appropriate for your environment.

### authentication\_default\_users\_lookup
Used for the `Default Authentication` dashboard. This list was put together from multiple sources, and may not contain all of the default users which may be available in your environment.

### authentication\_priv\_users\_lookup
Used for the `Privileged Authentication` dashboard. This list was put together from multiple sources, and may not contain all of the privileged users which may be available in your environment.

### If you want to customize the lookups
I strongly suggest that if you want to use customized versions of these lookups, you create new configurations for additional lookups, rather than editing the `.csv` files included in the app. Splunk lookup files are not upgrade safe, so future versions of the app will contain lookup files which may overwrite your customizations.

## About support for this app
Support for this app is provided on a best-effort basis. We have released this app for free, and want to help solve issues, and add features, but we also have day-jobs. The Github repo to report issues can be found [here](https://github.com/automine/authentication_app).

Need help? Use the Splunk community resources! I can be found on many of them:

* [Splunk Answers](https://answers.splunk.com/)
* [#splunk on Efnet IRC](https://wiki.splunk.com/Community:IRC)
* [Splunk Slack channel](http://splunk402.com/chat/)

## References

### Splunk Common Information Model
* [Splunk Common Information Model Add-on Docs](http://docs.splunk.com/Documentation/CIM/latest/User/Overview)
* [Splunk Common Information Model add-on Authentication data model](http://http://docs.splunk.com/documentation/cim/latest/user/Authentication)

### Downloads
* Splunk Common Information Model Add-on Download: <https://apps.splunk.com/app/1621/>

## Credits
This app was created by David Shpritz of [Aplura, LLC.](http://www.aplura.com/)

## Release history

### v1.4
* Added deprecation warning and link to replacement.

### v1.3
* Changed search on the geography page to respect the time picker (thanks mattymo!)

### v1.2
* Converted event views at the bottom of profile pages to use tstats-based searches instead of raw events
* Converted Authentication Search panel to use the `from` command instead of `datamodel`

### v1.1
* Fixed to the geography page

### v1.0
Initial release
