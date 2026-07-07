## Introduction

This application exists to automate the data rebalance process on indexer clusters. The data rebalance will only trigger if the search factor is currently met.

## Installation
This application only needs to be installed on a cluster manager, it is not useful on any other instance.

Note this app is not designed to work with Splunk cloud.

## Usage
The following parameters exist:
`threshold` - this is a number between 0.1 and 1.0, known as the "Threshold" in the Splunk Data Rebalance UI. If not set this defaults to 0.9.
`max_runtime` - this is "Max Runtime" in the UI, measured in minutes, this defaults to unlimited.
`target_index` - the Splunk Data Rebalance UI has a dropdown with a list of indexes, this allows you to target a singular index for a rebalance, this is the name of the index.
`searchable` - this is the searchable option for a standard data rebalance, is it recommended to not use this option for SmartStore clusters. Defaults to False.
`debug` - this enables extra logging from the modular input, defaults to False.
`usage_based` - this enables the new usage-based data rebalance option in 9.3, in 9.3 this can only be triggered from the CLI, more details below.
`excess_buckets` - this is the equivalent of Indexes -> Bucket Status -> Indexes With Excess Buckets -> Remove All Excess Buckets (if a target_index is not specified), if a target_index is specified than it will remove the buckets on the target index.

### Example configuration
```
[auto_data_rebalance://example]
threshold = 0.9
max_runtime = 60
target_index = _internal
searchable = True
debug = True
interval = 33 6 * * *
```

The above example would run the auto_data_rebalance everyday at 6:33AM on the _internal index only with a rebalance_threshold of 0.9, a maximum runtime of 60 minutes and in searchable mode
This example also enables all debug logging, a more typical use case might be:
```
[auto_data_rebalance://example]
threshold = 0.95
max_runtime = 60
interval = 33 6 * * *
```

searchable and debug will both default to False, the threshold if not specified will use 0.9 and runtime will not be limited unless specified.

## Usage-based data rebalancing
If you are running Splunk 9.3 or newer you have a new option to consider, usage-based rebalancing:
[Usage based data rebalancing](https://help.splunk.com/en/splunk-enterprise/administer/manage-indexers-and-indexer-clusters/10.0/manage-the-indexer-cluster/rebalance-the-indexer-cluster#id_3f07f54d_f2d0_49e1_8b13_527d3e640007__Rebalance_indexer_cluster_data_based_on_search_usage)

This option will run based on cluster-usage, however, it does not have a searchable mode or a target index, it will rebalance the entire cluster.
To use this option use the parameter:

`usage_based = True`

If not set, this app will default to the standard data rebalance method.

I did find while using the usage_based endpoints that the excess buckets were not removed, or at least not removed as much as I expected, so this argument:

`excess_buckets = True`

Will run an excess bucket removal instead of a data rebalance, you can define 1 input for excess bucket removal and another for rebalancing the data. These operations will conflict so you will need to use different times of the day.
Note that a regular (non-usage) data rebalance does trigger an excess bucket removal, the excess bucket argument will also respect the target_index setting if set.

The usage-based rebalancing focuses on balancing the search workload by moving heavily searched buckets between peer nodes. The primary goal is to improve search performance.

### When using usage-based data rebalancing, do I need a non-usage based data rebalance?
The short answer is, yes, you likely want to run both at different times.

The standard data rebalance clears all excess buckets and attempts to even the bucket count between all search peers, which helps to ensure a more even disk usage among peers.
The usage-based data rebalance works on the most heavily searched buckets only.

Therefore you might wish to schedule a full data rebalance for a quieter period of time, and perform usage-based rebalancing on a more regular schedule. I run the usage-based rebalance after the normal data rebalance on weekends.

## Troubleshooting
A log file is created in $SPLUNK_HOME/var/log/splunk/auto_data_rebalance.log

You can also enable debug logging if you need to troubleshoot the input

### SSL validation errors
If you see an error such as:
`Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain (_ssl.c:1106)')))`

or you see the response of:
`SSL_Verify_Error`

This simply means that the port 8089 is running an SSL certificate that is not trusted by the default certificate store in use by Splunk's python
You can change `verify=True` to `verify=False` in the bin/auto_data_rebalance.py file and this will bypass SSL validation of your local Splunk instance on port 8089 (note that this comes with a minor security risk)


## Feedback?
Feel free to open an issue on github or use the contact author on the [SplunkBase link](https://splunkbase.splunk.com/app/7969) and I will try to get back to you when possible, thanks!

## Release Notes
### 0.0.8
Adding python.required in `inputs.conf` as requested by splunkbase, this is supported in 10.2 and above. Harmless warning messages may occur on older Splunk versions.

Updated Splunk python SDK to 2.1.1

### 0.0.7
Removed from splunkbase, typo in the python.required setting (and this was the only update), replaced by 0.0.8

### 0.0.6
README.md update only

### 0.0.5
Changed label in app.conf to Automatic Data Rebalance, corrected a typo in the description

### 0.0.4
Corrected an error where the threshold would always be set, even if it was unchanged

### 0.0.3
Corrected a typo that would stop this from working as expected if the threshold is not matching the configuration

### 0.0.2
Add AI generated app logo

### 0.0.1
Initial version

