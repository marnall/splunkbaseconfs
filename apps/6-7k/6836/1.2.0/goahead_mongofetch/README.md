# GoAhead Mongofetch

## Introduction

Mongofetch is a pymongo's client only for retrieving db records from MongoDB.
This never perform `CREATE/UPDATE/DELETE` operation to the target database, except for safe **READ** at the present.
We birth this app because the similar app is so old that it had been archived and hasn't been compatible for Splunk Cloud, in addition, the archived app doesn't cover the connection string format to access any MongoDB. 

## Installation

MongoDB connection string is needed to utilize this App. (ref: https://www.mongodb.com/docs/manual/reference/connection-string/)
If you use user credential in the connection string, we recommend to check that the password is correct and the user privilege is enough to access the `authsource` database.

1. Install this App package
2. Set up the connection string on the App Setup Page. 
3. Restarting splunk search head instance may be sometimes possibly needed for activating these custom search commands and loading this app's icon. 

Note: App Install user needs "admin_all_objects" privilege and Splunk search users need "list_storage_passwords" privilege in order to utilize "Secret storage".

## Usage

1. **mongocheck**
    - GeneratingCommand to show PyMongo Client's connection status by calling server_info() to the target MongoDB. The connection error will be shown if it has a problem like authentification fail.
    - Output field name
        - *client*, *server_info* and *connection_status* under *_raw* field.
    - Example   
        - ` | mongocheck"`

2. **mongolist**
    - GeneratingCommand to list the accessible database and tables of target MongoDB.
    - Options
        - **show_count** (Optional)   :  add record count for each database and table which the user can read. False by default.
    - Output field name
        - following the target mongo database names under *_raw* field.
    - Example  
        - ` | mongolist "`
        - ` | mongolist show_count=True"`

3. **mongofetch**
    - GeneratingCommand to fetch records with `find()` in pymongo by database, table, query.
    - Options
        - **database** (Required)       : target database name
        - **table** (Required)          : target table name
        - **database** (Required)       : search query with pymongo schema '{}'
        - **dbtimestamp** (Optional)    : timestamp field name of the target mongo record, which is necessary if the query use the timestamp field. "epoc time" value is only available.
    - Output field name
        - following the target mongo database records under *_raw* field.
    - Example  
        - ` | mongofetch database="testdb" table="users" query="{}" `
        - ` | mongofetch database="testdb" table="users" query="{\"$and\":[{\"timestamp\":{\"$gt\":1677633240}},{\"user\":\"alice\"}]}" dbtimestamp=timestamp`
        - ` | mongofetch database="testdb" table="users" query="{'$and':[{'timestamp':{'$gt':1677633240}},{'user':'alice'}]}" dbtimestamp=timestamp`
    - Field Extraction
        - E.g. `spath` command is useful to extract the mongodb's records field.


Command usages are also described in searchbnf.conf, thus you can see it on search window by writing the command name on. 

Some errors are dumped to the command result fields and the command exception will be dumped in search.log.
This App has a custom logger which dump the debug and error logs into "%SPLUNK_HOME%/var/log/splunk/goahead_mongofetch_app.log"
We recommend **mongocheck** command at first to confirm the connection established to your target mongo db.


## Included 3rd party's additional import modules

- pymongo-4.3.3
- dnspython-2.3.0 

## Similar Splunk Apps which we refered.

- [MongoDB Commands](https://classic.splunkbase.splunk.com/app/3644/) (App, *archived*)
- - not able to use MongoDB connection string format on Mongocheck's initial release date.
- - not compatible to SplunkCloud on Mongocheck's initial release date.

## Standalone python client

- [MongoDB_client](https://github.com/Tatsuya-hasegawa/MongoDB_client)
- - using the almost same algorizm and functions. It may be useful for testing or as your onsite gadjet.

## Support

Splunk 9.x or later

## License

[APACHE LICENSE, VERSION 2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Copyright

Copyright 2025 GoAhead Inc.
