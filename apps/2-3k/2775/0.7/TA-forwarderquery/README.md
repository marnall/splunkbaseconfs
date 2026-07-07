**Author:**

**Owner:**

**Sourcetypes:**

* vendor:product
* vendor:product:subtype

**Supported Product(s):**

* a
* b

**Add-on Version:**

* x.y.z

**Supported CIM Version:**

* 4.4

**Supported CIM Data Models:**

* Authentication
* x
* y

**Add-on contains:**

* Search-Time Configuration
* Index-Time Configuration
* Parsing-Time Configuration
* Input-Time Configuration

**Additional Notes:**

* x

* Serverclasses and app->serverclasses

Template settings for classes for assigning the correct apps

[serverClass:All Linux Machines]
blacklist.0 = mysplunkserverpattern*
machineTypesFilter = linux-x86_64
whitelist.0 = *

[serverClass:All Windows Machines]
machineTypesFilter = windows-intel,windows-x64,
whitelist.0 = *