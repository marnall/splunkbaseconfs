# pi Temperature Monitoring app

This app will index and present temperature data from a raspberry pi using the Dallas DS18B20 temperature sensors.

# Getting Started

## Prep

First you will need a Raspberry Pi and the DS18B20 sensor(s). I suggest reading this article: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing?view=all

Once you have used the test python script to see temperature data per the Adafruit instructions you are ready to use this app.

## Prep the UF

This app will require the install of a Splunk Universal Forwarder on the Raspberry Pi. 

This is how I did it.

1. Download and scp over the Splunk Universal Forwarder app for the Pi
    a. https://apps.splunk.com/app/1611/
2. Untar the UF in the /tmp dir
    a. tar zxvf forwarder-for-linux-arm-raspberry-pi_10.tgz 
3. Move to /opt/
    a. sudo mv splunkforwarder/ /opt/
4. Create splunk user and assign home dir.
    a. sudo adduser splunk --home /opt/splunkforwarder
5. Own the directory correctly. 
    a. cd /opt/
    b. sudo chown -R splunk:splunk splunkforwarder/
6. Start the UF.
    a. sudo su - splunk
    b. ~/bin/splunk start
7. Set Splunk to start on boot.
    a. sudo /opt/splunkforwarder/bin/splunk enable boot-start -user splunk
8. Send UF data to your main Splunk Indexer.
    a. ~bin/splunk add forward-server <indexer>:9997 -auth admin:changeme


## New Install of the piTemp App

This section is to install on a centralized splunk setup.

1. Copy this app directory into $SPLUNK_HOME/etc/apps/ location.  Or install via Splunk UI (recommended).
2. Look at file default/props.conf for any edits.
3. Restart the Splunk server.
4. Install the TA app onto your raspberry pi running the splunk UF.
    a. The TA is under the appserver/addons/ directory.
5. Update the lookup table to map a friendly name to your sensors in lookups/.
    a. lookups/probenames.csv
    b. You will need to know the ID numbers of your sensors.


## Distributed HA Splunk environment

For those who are running a distributed Splunk design or HA: ie separate forwarders, search heads, indexers, etc... Please follow these directions.  Depending on your design YMMV.  Please see this link for more instructions:  [http://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons]

1. Install this app on your Search Head(s) and Indexer(s).



## Upgrading this app

1. Run the upgrade via the Splunk App management UI.
2. Restart Splunk.


# Notes

Temperature data will be stored into the main index of splunk. It will be set to sourcetype "piTemp".

Example log format is:
> 2015-01-28 14:16:40.749933 raspberrypi get_temp.py[20202]: sensor=28-000005abea5d, temp_c=18.0, temp_f=64.4, temp_raw=18000.0


# What's in 1.0.1!

 - Minor, very minor, updates.


# What's in 1.0!

New app!

- Works with Splunk 6.0 and up.
- TA for the pi.

