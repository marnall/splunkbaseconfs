This app is used to call auditreduce and praudit on an interval and to cache the timeranges for the query. This way you can run the script and not get duplicate results. The first time it runs it will start from Jan 1, 2000 or you can supply an earliest argument in the config file.

The app also supports a sinkhole for audit logs. Any audit logs placed in the sinkhole are run through auditreduce and praudit then the logs are removed. WARNING, the script will delete any files placed in the sinkhole. If you do not want them deleted please copy in symlinks.

To install, place the bsm directory in $SPLUNK_HOME/etc/apps and restart splunk.
There are a handful of useful options in the bsm.conf file.

Its often useful to test ouside of splunk to make sure the script works.
To do this you need to set SPLUNK_HOME.
 export SPLUNK_HOME=your_splunk_install_location
Then
 cd $SPLUNK_HOME/etc/apps/bsm
 python bin/bsmping.py --noCache=True

The above should spit audit logs


The python script will read config files in either etc/apps/bsm/local/bsm.conf or etc/apps/bsm/default/bsm.conf.
To protect your config changes from upgrade do not edit the config file in default but instead copy the default/bsm.conf
to local/bsm.conf and make your changes there. The script will treat the copy in local with precedence.

See default/bsm.conf for possible configuration changes.
No changes are required to if you want raw formatting of events.

Send questions or bugs to Stephan Buys <issupport@exponant.com>

With Permission from Original App author:
Erik Swan (erik@splunk.com)

