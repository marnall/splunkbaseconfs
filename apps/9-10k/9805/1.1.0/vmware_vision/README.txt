VMware Vision for Splunk 1.1.0

VMware syslog activity, VM changes and CIM Authentication / Change mappings.
Install this app on the search head. Use TA-vmware-vision on raw parsing tiers.

Read README/docs/INSTALLATION.md for setup and README/docs/CIM.md for CIM.
Native VMware operation names use vmware_action. Review custom searches and
rebuild enabled data-model summaries when upgrading from versions before 1.1.0.

No inputs, index definitions, scheduled alerts or API polling are enabled.
Last observed VM state is based on recorded events, not live inventory.

Copyright 2026 Majid Ershadi. Licensed under Apache License 2.0.
