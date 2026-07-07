SA-Hydra
----------------------------------------
	Author: Splunk
	Version: 4.3.0
	commands: aggregatefields
	Details:
			This supporting Add-on Collects API based data from vCenter/ONTAP servers and schedules jobs from the Scheduler and assigns it to run the worker processes on each data collection node.
	Has index-time operations: False

Using this Add-on:
----------------------------------------
	Configuration: Manual
	Ports for automatic configuration: None


	Usage of Example Hydra Worker and Example Hydra Scheduler modular input stanzas mentioned in inputs.conf

	[example_hydra_worker://<name>]
	capabilities = <value>
	* this is the comma delimited list of actions that the worker can perform (job types)
	log_level = <value>
	* the level at which the worker will log data.
	duration = <value>
	* the minimum time between runs of the input should it exit for some reason

	[example_hydra_scheduler://<name>]
	* the scheduler should only exist once
	log_level = <value>
	* the level at which the scheduler will log data.
	duration = <value>
	* the minimum time between runs of the input should it exit for some reason


Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
