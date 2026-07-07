Splunk GUI for SysStat

The Splunk GUI for SysStat provides visualization of the system activity collected with the sysstat package.

Prerequisites:
  1. Splunk 6/7/8
  2. Modern Linux Distribution:
    - RedHat/CentOS 5/6/7
    - Debian 7/8/9
    - Ubuntu 14+
  3. systat package 

Installation:

1. install the sysstat package

   RPM-based distros (Redhat, CentOS):
     yum install sysstat

   DPKG-based distros (Debian, Ubuntu):
     apt-get install sysstat

2. Decrease the interval between samples and enable collection of all information.

   Redhat, Centos:
     Edit /etc/cron.d/sysstat and change 
       */10 * * * * root /usr/lib64/sa/sa1 -S DISK 1 1
     to:
       * * * * * root /usr/lib64/sa/sa1 -S XALL 1 1


   Debian, Ubuntu:
     Edit /etc/cron.d/sysstat and change
       5-55/10 * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1
     to:
       * * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1 

     Edit /etc/default/sysstat and change
       ENABLED="false"
     to
       ENABLED="true"

     Edit /etc/sysstat/sysstat and change
       SADC_OPTIONS="-S DISK"
     to
       SADC_OPTIONS="-S XALL"

3. Install splunk.

4. Install this app.

Troubleshooting:

If there is no or wrong output:
1. check /opt/splunk/var/log/splunk/splunkd.log
2. run /opt/splunk/etc/apps/Sysstat/bin/sadf.sh manually
3. search via Splunk UI "sourcetype=sysstat"


Contact:

  splunk@compek.net


