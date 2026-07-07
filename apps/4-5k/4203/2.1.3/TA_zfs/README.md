# ZFS Add-On for Splunk

ZFS storage pools maintain themselves very isolated from the host OS, making generic unix commands such as df, du, iostat, and others questionable at best. Further, the provided zfs utilities are oriented
 towards human readable output rather than machine parsable output.
This Add-On is intended to address both of these monitoring issues with minimal dependancies. Built using zfsutils, Splunk Modular Inputs, JSON, and Python.


### Prerequisites

The pre-requisites for the add-on are as follows;

* Indexers: None
* Search Heads: None
* Heavy Forwarders (gateway): None
* Heavy Forwarders (endpoint): zfsutils
* Universal Forwarders (endpoint): python2, zfsutils


### Installing & Deploying the Add-On

Installation instructions are as follows;
1) Carefully review README.txt, README/inputs.conf.spec, and default/inputs.conf.
2) Create your own indexes to send data from this Add-On into. This Add-On does not create or ship any by default.
3) Create a local/inputs.conf with the inputs you desire togged on (disabled = false)
4) Add a zpool_list (space delimited) or a filter entry to each input as necessary. Review README/inputs.conf.spec for more information.
5) Follow the steps below for deployment

* Splunk Indexers:
    * Add-on should be installed on Indexers to properly set the timestamp rules. Deploy using master-apps (clustered) or directly in apps (unclustered).
* Splunk Search Heads:
    * Add-on should be installed on Search Heads to properly enable JSON parsing.
* Splunk Heavy Forwarders (gateway):
    * Add-on should be installed on Heavy Forwarders to properly set the timestamp rules. Deploy directly in apps.
* Splunk Heavy Forwarders (endpoint):
    * Add-on should be installed on Heavy forwarders and inputs.conf modified to README/inputs.conf.spec and default/inputs.conf specifications. Deploy directly in apps.
* Splunk Universal Forwarders (endpoint):
    * Add-on should be installed on Universal forwarders and inputs.conf modified to README/inputs.conf.spec and default/inputs.conf specifications. Deploy directly in apps.


### Upgrading from Version 1
This latest iteration of the ZFS Add-On for Splunk involves some breaking changes to zfs_status. 
In the past, zfs_status was specifically targetted at "post scrub" output from "zpool status".
This new version is generic, and is intended to cover **all** outputs from "zpool status", so the field language that was specific to the scrub operation is gone.
To migrate, you will have to either rewrite old search-artifacts that targetted these fields, or deploy Version 1 zfs_status and Version 2 side by side.
I encourage you to "rip off the bandaid" in this case. The new version is vastly superior for operational visibility.


### Testing & Troubleshooting

There are several moving parts to this add-on. If you run into issues check the following;

```
splunkd.log in search or at $SPLUNK_HOME/var/log/splunk/splunkd.log
splunk cmd splunkd print-modinput-config myscheme mystanza
splunk cmd splunkd print-modinput-config --debug myscheme mystanza
splunk cmd splunkd print-modinput-config myscheme mystanza | python /path/to/script/in/question.py
```


## Authors

* **Matt Wirth** - *Initial work* - mwirth@splunk.com
* **Brian Ó Donnell** - *regex fixes* - @bodonne2


## Git Repo

https://gitlab.com/_mwirth/zfs-add-on-for-splunk
