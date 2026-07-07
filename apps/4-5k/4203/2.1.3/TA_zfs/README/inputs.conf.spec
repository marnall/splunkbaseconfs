[zfs_status://<name>]
* Configure an input for collecting from 'zpool status'
python.version = python3

zpool_list = <value>
* A single zpool name or list of zpool names for monitoring. 'ALL__POOLS' will monitor all available pools.

[zfs_iostat://<name>]
* Configure an input for collecting from 'zpool iostat'
python.version = python3

zpool_list = <value>
* A single zpool name or list of zpool names for monitoring. 'ALL__POOLS' will monitor all available pools.

[zfs_iostat_metrics://<name>]
* Configure an input for collecting metrics from 'zpool iostat'
python.version = python3

zpool_list = <value>
* A single zpool name or list of zpool names for monitoring. 'ALL__POOLS' will monitor all available pools.

[zfs_arcstats://<name>]
* Configure an input for collecting from '/proc/spl/kstat/zfs/arcstats'
python.version = python3

filter = <value>
* A regex filter for the values output from '/proc/spl/kstat/zfs/arcstats'. 'ALL__STATS' will monitor all lines of arcstats.

[zfs_arcstats_metrics://<name>]
* Configure an input for collecting metrics from '/proc/spl/kstat/zfs/arcstats'
python.version = python3

filter = <value>
* A regex filter for the values output from '/proc/spl/kstat/zfs/arcstats'. 'ALL__STATS' will monitor all lines of arcstats.
