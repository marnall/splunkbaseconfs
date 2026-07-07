# threatdb

RST Cloud Threat Database Add-on for Splunk


## Prerequisites

1. Install Redis (http://redis.io/) on Splunk Search Head (or other server) to store IP reputation data
2. To run lookup command install some libraries on Splunk Search Head:

```
$ wget https://bootstrap.pypa.io/get-pip.py
$ python get-pip.py
$ sudo pip install redis 
$ sudo pip install netaddr
```

3. All Python modules will be installed on your local Python instance, but not in Splunk Python instance
4. Open $SPLUNK_HOME/etc/apps/threatDB/bin and edit this lines, if needed

redisworker.py 
```
sys.path.append("/usr/local/lib/python2.7/dist-packages") # Path to redis-py module
redis_server = '127.0.0.1'
redis_port = 6379
```

threat_flushdb.py
```
redis_server = '127.0.0.1'
redis_port = 6379
```

threatuploader.py
```
redis_server = '127.0.0.1'
redis_port = 6379
```

start_threatupload.sh
```
base_dir=/opt/splunk/bin/scripts/threatDB
python_bindir=/usr/bin
```

5. Database must be accessed from Splunk Search Head 

## Getting Started

1. Create the directory to store feeds:

```
$ mkdir -p /tmp/threatsupload
```

2. Modify /etc/crontab to create an update job (update once peer day, in database entry TTL = 48 hours):

```
2 0 * * * root $SPLUNK_HOME/etc/apps/threatDB/bin/start_threatupload.sh /tmp/threatsupload
```
root is an example here. In production environment you can use any user account.


## Usage

1. To start on Search app:
 
```
| lookup local=true lookupthreat clientip
```
local - needed to start scripts only on Splunk Head Search, but not on Indexers

2. To parse script output you can use the macros:

```
| `threatDB(clientip)`
```

## License
threatdb is released under the [MIT License](MIT-LICENSE) by RST Cloud (https://www.rstcloud.net)
