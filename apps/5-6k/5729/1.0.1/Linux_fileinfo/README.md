This app permit to get informations ( Rights, Ino, Dev, nLink, uid, gid, size in bytes, modification time, most recent access time, change time ) of a given file, or of all the files of the given directory
Usage in splunk search : 
| fileinfo filepath="/opt/splunk/var/log/splunk/splunkd.log"
| fileinfo filepath="/opt/splunk/var/log/splunk/*.log"
| fileinfo filepath="/opt/splunk/var/log/splunk"

How does it works ?

The search call a python3 script which calls os.stat on the given path, using glob.glob to parse the paths

This is working on splunk 7.x & 8.x, only on linux filesystem.

© 2021 Timoti Prigent

Contact: timoti.prigent@dataklub.com
