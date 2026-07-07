##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##

[logging]
loglevel = [DEBUG|INFO|WARNING|ERROR|FATAL]
* log level value
* Default: INFO

[settings_migration]
has_migrated = [0|1]
* whether or not old (< v4.0.0) settings conf is migrated

[inputs_migration]
has_migrated = [0|1]
* whether or not old (< v4.0.0) inputs conf is migrated

[passwords_migration]
has_migrated = [0|1]
* whether or not old (< v4.0.0) passwords conf is migrated

[templates_migration]
has_migrated = [0|1]
* whether or not old (< v4.0.0) templates conf is migrated
