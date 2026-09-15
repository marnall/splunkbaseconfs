[bifrost]
db_path = <string>
* Full path to Bifrost logs.db SQLite file
* Leave blank if using PostgreSQL

pg_host = <string>
* PostgreSQL host (e.g. localhost or 192.168.1.10)
* If set, PostgreSQL backend is used instead of SQLite

pg_port = <integer>
* PostgreSQL port. Default: 5432

pg_database = <string>
* PostgreSQL database name. Default: bifrost

pg_user = <string>
* PostgreSQL username

pg_password = <string>
* PostgreSQL password

index = <string>
* Splunk index. Default: llmgateway

interval = <integer>
* Poll interval in seconds. Default: 30

batch_size = <integer>
* Max records per poll. Default: 500
