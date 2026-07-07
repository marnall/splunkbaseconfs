# Splunk/RSA Netwitness Device Monitoring
# Version : 0.9.1
# Date: 05 Jul 2022
#
# written by Rui Ataide <rataide+splunkapps@gmail.com>
# This software is provided "as is" without express or implied warranty or support

 === Splunk for RSA Netwitness Administration ===

 This Splunk app will connect to a RSA Netwitness Devices via REST API.
 It will poll the RSA Netwitness device(s) regularly to collect device stats.

 It will also accept NextGen device logs forwarded via Syslog and sourcetype "netwitness_log".

 To install:
   - Extract to $SPLUNK_HOME/etc/apps/
   - Reconfigure as per below
   - Restart Splunk

 The following Splunk search will provide any relevant error logs for this app:

   index=_* nwadmin.py sourcetype="splunkd"

 Make sure the REST interface is enabled on your RSA Netwitness device.
 **NOTE: SSL access to the REST interface currently requires the use of a hack**
 Please see http://splunk-base.splunk.com/answers/40255/does-splunk-for-netwitness-support-ssl-access-to-the-rest-api for more details

 To troubleshoot connections to your RSA Netwitness device use, you can use any browser.

 The configuration of log portion of this app is based on Splunk's native configuration settings. There's an example below but it won't
 necessarily apply to all environments. The only mandatory setting is "sourcetype=netwitness_log". For mode details see the How-to PDF.

  # [monitor:///var/log/netwitness.log]
  # sourcetype = netwitness_log


 Configure the following variables in nwadmin.conf.
 Make sure you place it in <app>/local/nwadmin.conf to avoid overwrite during app upgrades:

  # [<unique reference used for logging of app messages>]
  # protocol=(http|https)
  # server=<ip/hostname of device>
  # port=<device port>
  # type=(appliance|broker|concentrator|decoder)
  # username=<username>
  # password=<password>

 You can have as many of these instances as needed, normally two per device (appliance + service) as per example below:

[decoder-12]
protocol=http
server=192.168.1.12
port=50104
type=decoder
username=admin
password=netwitness

[appliance-12]
protocol=http
server=192.168.1.12
port=50106
type=appliance
username=admin
password=netwitness

 For more examples see nwadmin.conf in $APP_HOME/default/
