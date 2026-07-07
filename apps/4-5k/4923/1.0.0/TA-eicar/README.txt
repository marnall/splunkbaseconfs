# README.txt

# TA-eicar
### Description
App randomly places the EICAR test file on common malware locations on the Linux file system and logs it's change out. This is helpful in testing your blue team detection on the Linux platform. 

### Installation/Platform
Splunk 7.3.1 tested

Create an index
Set index on inputs.conf and macros.conf
Install on Universal Forwarders, restart
Install on Heavy Forwarders, restart.
Install on Indexers, restart.
Install on Search heads, restart. 

### Usage
This app adds tags for malware but unless you need them they should be disabled so the test does not populate any models you were not expecting. 

### History
3.13.2020.1 - daniel, initial version

### Credits
Daniel Wilson <daniel.p.wilson@live.com>

### License
None

### TO DO/BUGS
1) Check if the directories exists to fail cleaner
2) Add Windows support since folks seem to want that
