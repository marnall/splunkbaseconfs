# Copyright (C) 2013-2019 Splunk Inc. All Rights Reserved.

[<name>]
* This determines a project named <name>.

packages = <list of apps>
* REQUIRED.
* Set a comma-delimited list of apps which the project will span.
* A wildcard setting '*' will select all apps. This means the project will span all data.
* Defaults to empty string.
