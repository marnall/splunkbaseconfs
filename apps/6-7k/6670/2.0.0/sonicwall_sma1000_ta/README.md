# Requirements

* SMA1000 firmware version 12.4.1 or above.
* Splunk Enterprise version 8.0 or above.

# Add-on Installation

Follow the relevant instructions for your deployment type at https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons

# Data Collection Methods

This add-on implements the following models from the
[Splunk Common Information Model (CIM)](https://docs.splunk.com/Documentation/CIM/4.20.0/User/Overview).

Collected via syslog events:

* Authentication
* Change
* Network Sessions
* Network Traffic

Collected via API polling:

* Performance

# Syslog Inputs

## Configuration in Splunk

### Create a syslog data input

Skip this step if you already have a syslog data input defined in Splunk.

1. Navigate to Settings > Data Inputs > TCP
2. Click 'New Local TCP'
3. Enter the port number you would like Splunk to listen for Syslog messages on (e.g. 514)
4. Click 'Next'
5. Set the Source type to: syslog
6. Optionally select an App Context and Index
7. Click 'Review'
8. Click 'Submit'

### Additional configuration for UDP inputs

If your syslog data input uses UDP transport, additional configuration is required.

First, locate the `inputs.conf` configuration file that your input is defined in. See the
[Splunk documentation](https://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretofindtheconfigurationfiles)
for more information on locating this file.

After locating your config file, locate the stanza representing your UDP input and add
the following two settings:

```
[udp://514]
...
no_priority_stripping = true
no_appending_timestamp = true
```

## Configuration on the SMA1000 device(s)

For each SMA1000 device you wish to monitor:

1. Navigate to Monitoring > Logging > Configure Logging (on CMS, Management Server > Monitor > Logging > Configure Logging)
2. Under 'Syslog Configuration', add an entry for your Splunk syslog input
3. Click 'Save'
4. Apply pending changes

Optionally enable accounting records in any realms where you want to monitor user sessions:

1. Navigate to User Access > Realms (on CMS, Managed Appliances > Configure > Define Policy > Realms)
2. Click on the realm name
3. Click the 'Enable accounting records' checkbox
4. Click 'Save'
5. Apply pending changes
6. On CMS, synchronize policy

# SMA1000 API Polling Inputs

## Configuration in Splunk

1. Navigate to Apps > SonicWall SMA1000 Technical Add-on for Splunk
2. For each SMA1000 device you wish to monitor:
3. 
    1. Click 'New'
    2. Complete the form with the relevant values for your SMA1000 device
    3. Optionally configure the Polling Interval and Index under 'Advanced Settings'
    4. Click 'Save'

# Usage

* Events created or processed by the add-on can be queried with `vendor_product="SonicWall SMA1000"`
* The following models from the [Splunk Common Information Model (CIM)](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Overview) are implemented:
    * [Authentication](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Authentication)
    * [Change](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Change)
    * [Network Sessions](https://docs.splunk.com/Documentation/CIM/5.0.0/User/NetworkSessions)
    * [Network Traffic](https://docs.splunk.com/Documentation/CIM/5.0.0/User/NetworkTraffic)
    * [Performance](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Performance)
* Review the provided reports for example usage