The Metrics Add-on for Infrastructure (TA-linux-metrics) can be used on Linux Forwarders to send Operating System metrics to Splunk without using collectd or the HTTP Event Collector (HEC) and it is fully compatible with the "Splunk App for Infrastructure":
https://splunkbase.splunk.com/app/3975/

Note: the output is formatted for multiple-measurement metric data points (Splunk v8.x only) which allows for **significant license savings** as a single metric data point can now contain multiple measurements and dimensions.

One of the most powerful features of the add-on is the ability to add custom dimensions to each metric.

Use the built-in Setup Page to configure the inputs on a Standalone Instance, or use a Deployment Server to push the add-on to your forwarders.

### Compatibility ###

*   Splunk Enterprise v8.x
*   Splunk Universal Forwarder v8.x
*   Splunk App for Infrastructure v2.x
*   Linux: Ubuntu 16.04, Ubuntu 18.04, Ubuntu 20.04, Amazon Linux, CentOS 6, CentOS 7, CentOS 8, RHEL 6, RHEL 7, RHEL 8

### Metrics ###

*   CPU
*   Memory
*   Swap
*   Load
*   Uptime
*   Filesystems
*   Inodes
*   Disk I/O
*   Interfaces
*   Processes

### Custom Dimensions ###

You can configure the following custom dimensions and they will be added to all of the metrics as above:

*   cloud
*   region
*   dc
*   environment

### Installation ###

*   Create a new 'metric' index on your indexer/s, e.g. metrics_linux

Example indexes.conf :-

    [metrics_linux]
    coldPath = $SPLUNK_DB/metrics_linux/colddb
    homePath = $SPLUNK_DB/metrics_linux/db
    thawedPath = $SPLUNK_DB/metrics_linux/thaweddb
    datatype = metric

*   Install the add-on on your Linux servers and enable the inputs. Either use the built-in Setup Page, or copy the input stanzas from the default directory to the local directory (i.e. local/inputs.conf) and enable them as required:
    *   Update: disabled = 0
    *   Update: index = metrics_linux
    *   Note: **DO NOT UPDATE** sourcetype = metrics_csv

*   If you enable process monitoring, configure the relevant processes to monitor for your environment. Copy the stanza from the default directory to the local directory (i.e. local/process_mon.conf) and configure them as required:

            [process_mon]
            allowlist = bash,zsh,sshd,python.*
            blocklist = splunkd

    *   Note: `allowlist` and `blocklist` should be comma separated without spaces

*   Configure the relevant dimensions for your environment. Copy the dimensions from the default directory to the local directory (i.e. local/dims.conf) and configure them as required:
    *   Note: you can set `cloud` to `aws` or `gcp` and the built-in scripts will auto-discover the Region and Availablity Zone of the instance, e.g.

            [all]
            cloud = gcp
        
    *   Shell environment variables are also supported, e.g.
    
            [all]
            environment = $Deploy_Environment
        
    *   Note: the `region` and `dc` do not need to be configured if cloud is aws or gcp, i.e. only set these dimensions if cloud = false

*   Install the "Splunk App for Infrastructure" on your Search Head
    *   **IMPORTANT:** Update the 'sai_metrics_indexes' macro, e.g. index=metrics_linux

        *   https://docs.splunk.com/Documentation/InfraApp/latest/Admin/CustomIndexes#Use_a_custom_metrics_index_in_SAI

### Troubleshooting ###

*   If you don't see any Entities under 'Investigate' in the Splunk App for Infrastructure :-

    *   Update the 'sai_metrics_indexes' macro in the Splunk App for Infrastructure, e.g. index=metrics_linux

*   Error when enabling inputs via the Setup Page:

        Encountered the following error while trying to update: Error while posting to url=/servicesNS/nobody/TA-linux-metrics/data/inputs/script/.%252Fbin%252Fcpu_usage.sh

    *   Create a new 'metric' index before you enable any inputs

*   Run the following search to confirm that metrics are being indexed :-

        | mcatalog values(metric_name)

    *   If no results are found, run the following search and specificy your metrics index, e.g.

            | mcatalog values(metric_name) WHERE index=metrics_linux

    *   Add the 'metrics_linux' index to "Indexes searched by default" :-

        *   https://docs.splunk.com/Documentation/Splunk/latest/Search/Searchindexes#Control_index_access_using_Splunk_Web

*   If you see similar errors to the following in 'splunkd.log' on the forwarder :-

        11-10-2020 16:26:45.553 +1100 WARN  IndexProcessor - The metric name is missing for source=/opt/splunk/etc/apps/TA-linux-metrics/bin/cpu_usage.sh, sourcetype=cpu_usage, host=foo, index=metrics_linux. Metric event data without a metric name is invalid and cannot be indexed. Ensure the input metric data is not malformed. raw=["_time","metric_name:cpu.user","metric_name:cpu.system","metric_name:cpu.nice","metric_name:cpu.idle","metric_name:cpu.wait","metric_name:cpu.interrupt","metric_name:cpu.softirq","metric_name:cpu.steal","model","cloud","region","dc","environment","ip","os","os_version","kernel_version"]

        11-10-2020 16:26:45.553 +1100 WARN  IndexProcessor - The metric value=<unset> is not valid for source=/opt/splunk/etc/apps/TA-linux-metrics/bin/cpu_usage.sh, sourcetype=cpu_usage, host=foo, index=metrics_linux. Metric event data with an invalid metric value cannot be indexed. Ensure the input metric data is not malformed. raw=["_time","metric_name:cpu.user","metric_name:cpu.system","metric_name:cpu.nice","metric_name:cpu.idle","metric_name:cpu.wait","metric_name:cpu.interrupt","metric_name:cpu.softirq","metric_name:cpu.steal","model","cloud","region","dc","environment","ip","os","os_version","kernel_version"]

    *   Ensure that the sourcetype is set to `metrics_csv` and your forwarder is at least v8.x

*   If you have set "allowlist = " to monitor all processes but the "process_usage.sh" script uses 100% CPU and takes a long time to run, you may have hit a $PATH bug in one of your system profile scripts :-

    *   Set the file mode on the script as follows, e.g.

            # sudo chmod 0750 /etc/profile.d/jdk.sh

### Katana1 Built ###

* https://katana1.com

    *   Developers:

        *   Luke Harris (Data Analytics Practice Lead at Katana1)
        *   Chris Barbour (Professional Services Consultant at Katana1)

    *   Contributor:

        *   Robin Pollard (Euroclear)
