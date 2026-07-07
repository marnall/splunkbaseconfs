# btool

btool provides a scripted input that indexes configuration file introspection for your Splunk instance.

## Scripted inputs

### btool.sh

`btool.sh configuration_file [splunk_home] [sudo_user]`

Runs `$splunk_home/bin/splunk btool $configuration_file --debug`, sudoing as the $sudo_user if any.

splunk_home defaults to $SPLUNK_HOME.

If you are running the btool script from one splunk instance against another, then you need to specify splunk_home. 
You'll also want to set a sudo_user (and configure sudoers appropriately) if the foreign splunk instance runs as a 
different user than the calling splunk instance.

## Props

The following fields are extracted
* app_folder (apps, master-apps, slave-apps)
* app (app folder or "system")
* conf (e.g. props.conf)
* SPLUNK_HOME
* stanza

## Deployment

* Deploy to splunk instances that you want to collect configuration information from, and add local/inputs.conf to enable inputs and set index.
* Deploy to indexers receiving events for parsing and extraction props.

## Credits

* Splunk Cloud SRE
* Shaun Butler
* Rob Manevski
* Russell Uman

