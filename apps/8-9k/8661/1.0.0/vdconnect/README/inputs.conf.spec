#
# VDConnect Modular Input Specification
# This file defines all configurable parameters for the vdconnect input type.
#

[vdconnect://<name>]

# ─── CONNECTION SETTINGS ─────────────────────────────────────────────────────
db_type = <value>
* The type of vector database to connect to.
* Supported values: milvus, pinecone, weaviate, chromadb, qdrant, pgvector
* Required.

host = <value>
* The hostname, IP address, or endpoint of the vector database.
* For Pinecone: use the environment name (e.g., us-east-1-aws).
* For pgvector: use the PostgreSQL hostname.
* Required.

port = <value>
* The port number of the vector database.
* Defaults: milvus=19530, pinecone=443, weaviate=8080, chromadb=8000, qdrant=6333, pgvector=5432
* Required.

python.version = [python3|python3.7|python3.9]
* For Python scripts only, the version of Python that the script supports. [cite: 7]
* The Splunk platform uses the specified version of Python to run the modular input script. [cite: 9]
* This setting ensures compatibility with modern Splunk environments. [cite: 11]
* Required.

# ─── AUTHENTICATION ──────────────────────────────────────────────────────────
auth_type = <value>
* Authentication method.
* Supported values: api_key, basic, token, none
* Default: api_key

api_key = <value>
* API key for authentication.
* Used when auth_type = api_key.
* For Pinecone: your Pinecone API key.
* For ChromaDB: the server API key if auth is enabled.
* Optional (depends on auth_type).

username = <value>
* Username for basic authentication.
* Used when auth_type = basic.
* For pgvector: the PostgreSQL username.
* For Weaviate: OIDC username if applicable.
* Optional (depends on auth_type).

password = <value>
* Password for basic authentication.
* Used when auth_type = basic.
* For pgvector: the PostgreSQL password.
* Optional (depends on auth_type).

token = <value>
* Bearer token for authentication.
* Used when auth_type = token.
* For Milvus: the Milvus token.
* Optional (depends on auth_type).

# ─── SSL/TLS ─────────────────────────────────────────────────────────────────
use_ssl = <bool>
* Enable SSL/TLS encryption for the connection.
* Default: false

verify_ssl = <bool>
* Whether to verify the SSL certificate of the remote server.
* Default: true

ca_cert_path = <value>
* Path to a custom CA certificate file for SSL verification.
* Optional.

client_cert_path = <value>
* Path to a client certificate file for mutual TLS.
* Optional.

client_key_path = <value>
* Path to a client private key file for mutual TLS.
* Optional.

# ─── COLLECTION / DATA SOURCE ────────────────────────────────────────────────
collection_name = <value>
* The name of the collection, index, or class to query.
* Milvus: collection name
* Pinecone: index name
* Weaviate: class name
* ChromaDB: collection name
* Qdrant: collection name
* pgvector: table name
* Required.

database_name = <value>
* The name of the database (if applicable).
* For pgvector: the PostgreSQL database name.
* For Milvus: the database name (default: "default").
* Optional.

# ─── QUERY CONFIGURATION ─────────────────────────────────────────────────────
output_fields = <value>
* Comma-separated list of metadata fields to extract from each record.
* Example: log_text, timestamp, severity, source, hostname
* Use * to extract all available metadata fields.
* Default: *

filter_expr = <value>
* A filter expression to apply when querying the vector database.
* Milvus: boolean expression (e.g., severity == "ERROR")
* Pinecone: metadata filter JSON (e.g., {"severity": {"$eq": "ERROR"}})
* Weaviate: where filter in JSON format
* ChromaDB: where filter in JSON format
* Qdrant: filter in JSON format
* pgvector: SQL WHERE clause (e.g., severity = 'ERROR')
* Optional. If not set, all records are collected.

max_rows = <value>
* Maximum number of records to retrieve per collection cycle.
* Default: 10000

# ─── COLLECTION MODE ─────────────────────────────────────────────────────────
collection_mode = <value>
* How data is collected from the vector database.
* Supported values:
*   rising_column  — Incremental collection using a rising column (recommended).
*   batch          — Full collection each interval (use with caution on large collections).
*   tail           — Continuously poll for new records since last checkpoint.
* Default: rising_column

rising_column = <value>
* The name of the field used as the rising column for incremental collection.
* This field must be monotonically increasing (e.g., a timestamp or auto-increment ID).
* Used when collection_mode = rising_column or tail.
* Example: timestamp, created_at, id, _version
* Required when collection_mode = rising_column.

rising_column_type = <value>
* The data type of the rising column.
* Supported values: timestamp, integer, string
* Default: timestamp

checkpoint_key = <value>
* A unique key used to store the checkpoint for this input.
* If not specified, the input stanza name is used.
* Optional.

# ─── SCHEDULING ──────────────────────────────────────────────────────────────
interval = <value>
* The polling interval in seconds.
* How often VDConnect queries the vector database for new records.
* Default: 300

# ─── SPLUNK INDEX SETTINGS ───────────────────────────────────────────────────
index = <value>
* The Splunk index where collected events will be stored.
* Default: main

sourcetype = <value>
* The sourcetype assigned to collected events.
* Default: vdconnect:logs

source = <value>
* The source field value assigned to collected events.
* Default: vdconnect://<db_type>/<collection_name>

# ─── ADVANCED ────────────────────────────────────────────────────────────────
batch_size = <value>
* Number of records to fetch per API call / page.
* Used for pagination when querying large collections.
* Default: 1000

connection_timeout = <value>
* Connection timeout in seconds.
* Default: 30

query_timeout = <value>
* Query timeout in seconds.
* Default: 120

retry_count = <value>
* Number of retry attempts on transient failures.
* Default: 3

retry_delay = <value>
* Delay in seconds between retry attempts.
* Default: 5

include_vector = <bool>
* Whether to include the vector embedding data in collected events.
* Warning: embeddings are large and will significantly increase data volume.
* Default: false

timestamp_field = <value>
* The metadata field to use as the event timestamp in Splunk.
* If not set, the current collection time is used.
* Default: timestamp

timestamp_format = <value>
* The format of the timestamp field.
* Uses Python strftime format.
* Default: %Y-%m-%dT%H:%M:%S

disabled = <bool>
* Whether this input is disabled.
* Default: false
