# README.txt

# TA-GetNetAdaptor
### Description
Executes a powershell script to pull in the interface status of the server. 

### Installation/Platform
Splunk 8.0.2 tested

Create an index
Set index on inputs.conf
Set interval you want to collect in inputs.conf
Tune Timezone another elements as needed in props.conf
Install on Universal Forwarders, restart (eventbreaker needs set)
Install on Heavy Forwarders, restart.(props.conf needs work)
Install on Indexers, restart.  (props.conf needs work)
Not needed on a search heads (no search time knowledge in version 1.0.0)

### Usage
New new tags or eventtypes are added. 

### History
4.18.2020.1 - daniel, added CIM and tags. 
3.13.2020.1 - daniel, initial version

### Credits
Daniel Wilson <daniel.p.wilson@live.com>

### License
None

### TO DO/BUGS

