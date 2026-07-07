# Splunk/RSA Netwitness Device Monitoring
# Version : 1.0.0
# Date: 11 Jul 2023
#
# written by Netwitness

 === NetWitness Device Stats App for Splunk ===

 This Splunk app will connect to a RSA Netwitness Devices via REST API.
 It will poll the RSA Netwitness device(s) regularly to collect device stats.

 To install:
   - Extract to $SPLUNK_HOME/etc/apps/
   - Reconfigure as per below
   - Restart Splunk

 The following Splunk search will provide any relevant error logs for this app:

   index=_* nwadmin.py sourcetype="splunkd"

 Make sure the REST interface is enabled on your Netwitness device.

 Configure the following variables in nwadmin.conf.
 Make sure you place it in <app>/local/nwadmin.conf to avoid overwrite during app upgrades:

  # [<unique reference used for logging of app messages>]
  # protocol=(http|https)
  # server=<ip/hostname of device>
  # port=<device port>
  # type=(appliance|broker|concentrator|decoder)
  # username=<username>

 You can have as many of these instances as needed, normally two per device (appliance + service) as per example below:

[decoder-12]
protocol=http
server=192.168.1.12
port=50104
type=decoder
username=admin

[appliance-12]
protocol=http
server=192.168.1.12
port=50106
type=appliance
username=admin

 For more examples see nwadmin.conf in $APP_HOME/default/
