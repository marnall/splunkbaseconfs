pi-healthCollector is the app that needs to be installed on the Splunk Universal Forwarder for ARM

Copy pi-healthCollector.tar.gz archive to the Raspberry Pi to the /tmp directory using scp (or other file transfer program, I use puTTY pscp). SSH must be enabled on your Raspberry Pi for this to work.

pscp $SPLUNK_HOME$/etc/apps/piHealth/resources/pi-healthCollector.tar.gz pi@nnn.nnn.nnn.nnn:/tmp

Where nnn.nnn.nnn.nnn is the IP address of your Raspberry Pi.

Log into your Raspberry Pi as "pi" and elevate your session to root.

pi@RaspberryPi ~ $ sudo -s

cd to /tmp and extract the pi-healthCollector app into the Splunk Universal Forwarder for ARM.

root@RaspberryPi:/home/pi# tar -xvf /tmp/pi-healthCollector.tar.gz -C /opt/splunkforwarder/etc/apps

Using nano edit the /opt/splunkforwarder/etc/apps/pi-healthCollector/default/outputs.confof the pi-healthCollector app update the tcpout stanza to where you want the Splunk Universal Forwarder for ARM to send the Log/Event data.

root@RaspberryPi:/home/pi# nano /opt/splunkforwarder/etc/apps/pi-healthCollector/default/outputs.conf

[tcpout]
defaultGroup=indexer
# default
[tcpout:indexer]
server=xxx.xxx.xxx.xxx:9997

Where xxx.xxx.xxx.xxx is the IP of your indexer/heavy forwarder. It is assumed you are using the standard port of TCP 9997. If not, change this too.

Reboot your Raspberry Pi to end your session. The Splunk Universal Forwarder for ARM should start automatically and the pi-healthCollector app along with it.

root@RaspberryPi:/home/pi# reboot

Log into your Splunk Enterprise System and access pi health.
If you go directly to the Pi Health dashboard and set the Time Range picker to any of the realtime options you should be able to see data flowing into Splunk.

