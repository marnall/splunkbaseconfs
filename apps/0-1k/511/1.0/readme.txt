1. What is this?

A simple python script to read and dump RRD databases.
Each RRD record is output in a format like

2010-11-22 10:23:39 tx=443.2 rx=100

where "2010-11-22 10:23:39" is a timestamp, "tx" and "rx"
are series name, "443.2" and "100" are values.

i.e. each event is in a following format:

%Y-%m-%d %H:%M:%S series1=value1 series2=value2 ...


2. System requirements

* Python 2.6 or later (Python 3 is not supported)
* pyrrd (http://code.google.com/p/pyrrd/) 0.0.7 or later
* Splunk 4.x
* Linux (tested on Debian 6.0)


3. Usage

Set up scripted inputs with readrrd.sh.
Make sure you specify a full path to a RRD file to be read as the first argument of the script.

Example input.conf:

[script://$SPLUNK_HOME/etc/apps/search/bin/readrrd.sh /var/lib/collectd/rrd/localhost/interface/if_octets-eth0.rrd]
interval = 600
sourcetype = collectd
source = readrrd.sh
disabled = false


4. License
New BSD License


5. Contact

If you have questions, feel free to contact the author.

Kohei Takeda (takedaku@nttdata.co.jp)

System Platforms Sector
NTT DATA Corporation

