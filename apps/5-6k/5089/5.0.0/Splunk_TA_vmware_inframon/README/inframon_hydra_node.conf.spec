# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# This file contains possible attributes and values for configuring 
# worker processes and options for VMware vSphere data collection.
#
##########INTERNAL USE ONLY##########

[<DCN URL>]
capabilities = <value>
* This is the comma-delimited list of actions that the worker can perform.

log_level = <value>
* The level at which the worker will log data.

heads = <value>
* This value indicates number of enabled worker processes on a DCN.

pool_name = <value>
* This value shows the pool name of the vcenter.

user = admin
* This value indicates the username with which vcenter is configured.

addon_validation = <value>
* This is the value for add-on validation on DCN.
* <value> = 1 indicates that all the necessary add-ons are present on DCN.
* <value> = 0 indicates that either necessary add-ons are not present on DCN or DCN is not reachable from scheduler.

credential_validation = <value>
* This is the value for credential validation on DCN.
* <value> = 1 indicates that DCN is reachable from scheduler and provided credentials for DCN is correct.
* <value> = 0 indicates that either DCN is not reachable from scheduler or provided credentials for DCN is incorrect.

host = <value>
* This value contains the URL of DCN. It is same as stanza name.

last_connectivity_checked = <value>
* This value indicates the time when vcenter connectivity was last checked by scheduler.
