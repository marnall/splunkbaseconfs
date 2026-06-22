#!/usr/bin/env python3
# encoding: utf-8
"""
VDConnect for Splunk — Modular Input
=====================================
Collects logs from vector databases and indexes them into Splunk.

Supported databases:
  - Milvus      (pymilvus)
  - Pinecone    (pinecone-client)
  - Weaviate    (weaviate-client)
  - ChromaDB    (chromadb-client)
  - Qdrant      (qdrant-client)
  - pgvector    (psycopg2)
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime, timezone

# Add the app's lib directory to the path for third-party SDK imports
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB_DIR = os.path.join(APP_DIR, "lib")
if os.path.isdir(LIB_DIR):
    sys.path.insert(0, LIB_DIR)

# Splunk SDK
sys.path.insert(0, os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc", "apps",
                                "splunk_sdk", "lib"))
try:
    import splunklib.client as client
    from splunklib.modularinput import (
        Script, Scheme, Argument, Event, EventWriter
    )
    HAS_SPLUNK_SDK = True
except ImportError:
    HAS_SPLUNK_SDK = False


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE CONNECTORS
# ═══════════════════════════════════════════════════════════════════════════════

class BaseConnector:
    """Base class for all vector database connectors."""

    def __init__(self, config):
        self.config = config
        self.host = config.get("host", "localhost")
        self.port = int(config.get("port", "0"))
        self.collection_name = config.get("collection_name", "")
        self.output_fields = self._parse_fields(config.get("output_fields", "*"))
        self.filter_expr = config.get("filter_expr", "")
        self.max_rows = int(config.get("max_rows", "10000"))
        self.batch_size = int(config.get("batch_size", "1000"))
        self.include_vector = config.get("include_vector", "false").lower() == "true"
        self.connection_timeout = int(config.get("connection_timeout", "30"))
        self.query_timeout = int(config.get("query_timeout", "120"))

    def _parse_fields(self, fields_str):
        if fields_str.strip() == "*":
            return None  # All fields
        return [f.strip() for f in fields_str.split(",") if f.strip()]

    def connect(self):
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError

    def fetch_records(self, checkpoint_value=None):
        raise NotImplementedError

    def close(self):
        pass


# ─── MILVUS ──────────────────────────────────────────────────────────────────

class MilvusConnector(BaseConnector):

    def connect(self):
        from pymilvus import connections, Collection
        self._connections = connections
        self._Collection = Collection

        connect_params = {
            "alias": "vdconnect",
            "host": self.host,
            "port": str(self.port),
        }

        # Authentication
        auth_type = self.config.get("auth_type", "none")
        if auth_type == "token":
            connect_params["token"] = self.config.get("token", "")
        elif auth_type == "basic":
            connect_params["user"] = self.config.get("username", "")
            connect_params["password"] = self.config.get("password", "")

        # SSL
        if self.config.get("use_ssl", "false").lower() == "true":
            connect_params["secure"] = True

        connections.connect(**connect_params)

        db_name = self.config.get("database_name", "default")
        self.collection = Collection(self.collection_name, using="vdconnect")
        self.collection.load()

    def test_connection(self):
        self.connect()
        self.collection.num_entities
        self.close()
        return True

    def fetch_records(self, checkpoint_value=None):
        expr = self.filter_expr or ""
        rising_col = self.config.get("rising_column", "")
        mode = self.config.get("collection_mode", "rising_column")

        if mode == "rising_column" and rising_col and checkpoint_value:
            rising_type = self.config.get("rising_column_type", "timestamp")
            if rising_type == "timestamp":
                ckpt_filter = f'{rising_col} > "{checkpoint_value}"'
            elif rising_type == "integer":
                ckpt_filter = f'{rising_col} > {checkpoint_value}'
            else:
                ckpt_filter = f'{rising_col} > "{checkpoint_value}"'
            expr = f"({expr}) and ({ckpt_filter})" if expr else ckpt_filter

        query_params = {
            "expr": expr if expr else "",
            "limit": self.max_rows,
        }
        if self.output_fields:
            query_params["output_fields"] = self.output_fields

        results = self.collection.query(**query_params)
        return results

    def close(self):
        try:
            self._connections.disconnect("vdconnect")
        except Exception:
            pass


# ─── PINECONE ────────────────────────────────────────────────────────────────

class PineconeConnector(BaseConnector):

    def connect(self):
        from pinecone import Pinecone

        api_key = self.config.get("api_key", "")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(self.collection_name)

    def test_connection(self):
        self.connect()
        self.index.describe_index_stats()
        return True

    def fetch_records(self, checkpoint_value=None):
        """
        Pinecone does not support arbitrary scans; we use list + fetch.
        For production, use Pinecone's list endpoint to paginate through IDs.
        """
        records = []

        # List vector IDs (paginated)
        id_list = []
        for ids_page in self.index.list(limit=self.max_rows):
            id_list.extend(ids_page)
            if len(id_list) >= self.max_rows:
                break

        # Fetch vectors with metadata in batches
        for i in range(0, len(id_list), self.batch_size):
            batch_ids = id_list[i:i + self.batch_size]
            fetch_result = self.index.fetch(ids=batch_ids)
            for vid, vdata in fetch_result.get("vectors", {}).items():
                record = {"id": vid}
                if vdata.get("metadata"):
                    record.update(vdata["metadata"])
                if self.include_vector and vdata.get("values"):
                    record["_vector"] = vdata["values"]
                records.append(record)

        return records


# ─── WEAVIATE ────────────────────────────────────────────────────────────────

class WeaviateConnector(BaseConnector):

    def connect(self):
        import weaviate

        auth_type = self.config.get("auth_type", "none")
        scheme = "https" if self.config.get("use_ssl", "false").lower() == "true" else "http"
        url = f"{scheme}://{self.host}:{self.port}"

        auth_config = None
        if auth_type == "api_key":
            auth_config = weaviate.auth.AuthApiKey(api_key=self.config.get("api_key", ""))
        elif auth_type == "basic":
            auth_config = weaviate.auth.AuthClientPassword(
                username=self.config.get("username", ""),
                password=self.config.get("password", "")
            )

        self.client = weaviate.Client(
            url=url,
            auth_client_secret=auth_config,
            timeout_config=(self.connection_timeout, self.query_timeout)
        )

    def test_connection(self):
        self.connect()
        self.client.schema.get()
        return True

    def fetch_records(self, checkpoint_value=None):
        query = self.client.query.get(
            self.collection_name,
            self.output_fields or ["_additional {id}"]
        )

        if self.filter_expr:
            try:
                where_filter = json.loads(self.filter_expr)
                query = query.with_where(where_filter)
            except json.JSONDecodeError:
                pass

        query = query.with_limit(self.max_rows)

        rising_col = self.config.get("rising_column", "")
        if self.config.get("collection_mode") == "rising_column" and rising_col and checkpoint_value:
            where_ckpt = {
                "path": [rising_col],
                "operator": "GreaterThan",
                "valueDate": checkpoint_value
            }
            query = query.with_where(where_ckpt)

        result = query.do()
        data = result.get("data", {}).get("Get", {}).get(self.collection_name, [])
        return data


# ─── CHROMADB ────────────────────────────────────────────────────────────────

class ChromaDBConnector(BaseConnector):

    def connect(self):
        import chromadb

        auth_type = self.config.get("auth_type", "none")
        ssl = self.config.get("use_ssl", "false").lower() == "true"

        settings = chromadb.config.Settings()
        if auth_type == "token":
            settings = chromadb.config.Settings(
                chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
                chroma_client_auth_credentials=self.config.get("token", "")
            )

        self.client = chromadb.HttpClient(
            host=self.host,
            port=self.port,
            ssl=ssl,
            settings=settings
        )
        self.collection = self.client.get_collection(self.collection_name)

    def test_connection(self):
        self.connect()
        self.collection.count()
        return True

    def fetch_records(self, checkpoint_value=None):
        get_params = {"limit": self.max_rows, "include": ["metadatas", "documents"]}

        if self.include_vector:
            get_params["include"].append("embeddings")

        if self.filter_expr:
            try:
                where_filter = json.loads(self.filter_expr)
                get_params["where"] = where_filter
            except json.JSONDecodeError:
                pass

        result = self.collection.get(**get_params)

        records = []
        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])
        documents = result.get("documents", [])

        for i, vid in enumerate(ids):
            record = {"id": vid}
            if metadatas and i < len(metadatas) and metadatas[i]:
                record.update(metadatas[i])
            if documents and i < len(documents) and documents[i]:
                record["document"] = documents[i]
            records.append(record)

        return records


# ─── QDRANT ──────────────────────────────────────────────────────────────────

class QdrantConnector(BaseConnector):

    def connect(self):
        from qdrant_client import QdrantClient

        protocol = "https" if self.config.get("use_ssl", "false").lower() == "true" else "http"
        url = f"{protocol}://{self.host}:{self.port}"

        auth_type = self.config.get("auth_type", "none")
        api_key = self.config.get("api_key", "") if auth_type == "api_key" else None

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=self.connection_timeout
        )

    def test_connection(self):
        self.connect()
        self.client.get_collection(self.collection_name)
        return True

    def fetch_records(self, checkpoint_value=None):
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        scroll_filter = None
        if self.filter_expr:
            try:
                filter_dict = json.loads(self.filter_expr)
                scroll_filter = Filter(**filter_dict)
            except (json.JSONDecodeError, Exception):
                pass

        records = []
        offset = None
        while len(records) < self.max_rows:
            batch_limit = min(self.batch_size, self.max_rows - len(records))
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=batch_limit,
                offset=offset,
                scroll_filter=scroll_filter,
                with_payload=True,
                with_vectors=self.include_vector
            )
            points, next_offset = result
            for point in points:
                record = {"id": str(point.id)}
                if point.payload:
                    record.update(point.payload)
                if self.include_vector and point.vector:
                    record["_vector"] = point.vector
                records.append(record)

            if next_offset is None:
                break
            offset = next_offset

        return records


# ─── PGVECTOR ────────────────────────────────────────────────────────────────

class PgvectorConnector(BaseConnector):

    def connect(self):
        import psycopg2

        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.config.get("database_name", "postgres"),
            user=self.config.get("username", ""),
            password=self.config.get("password", ""),
            connect_timeout=self.connection_timeout,
            sslmode="require" if self.config.get("use_ssl", "false").lower() == "true" else "prefer"
        )

    def test_connection(self):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        self.close()
        return True

    def fetch_records(self, checkpoint_value=None):
        cur = self.conn.cursor()

        # Build column list
        if self.output_fields:
            columns = ", ".join(self.output_fields)
        else:
            columns = "*"

        table = self.collection_name
        conditions = []

        # Filter expression
        if self.filter_expr:
            conditions.append(f"({self.filter_expr})")

        # Rising column checkpoint
        rising_col = self.config.get("rising_column", "")
        mode = self.config.get("collection_mode", "rising_column")
        if mode == "rising_column" and rising_col and checkpoint_value:
            conditions.append(f"{rising_col} > %s")

        where = ""
        params = []
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
            if rising_col and checkpoint_value:
                params.append(checkpoint_value)

        order = ""
        if rising_col:
            order = f"ORDER BY {rising_col} ASC"

        query = f"SELECT {columns} FROM {table} {where} {order} LIMIT %s"
        params.append(self.max_rows)

        cur.execute(query, params)
        col_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()

        records = []
        for row in rows:
            record = {}
            for i, col in enumerate(col_names):
                val = row[i]
                if hasattr(val, "isoformat"):
                    val = val.isoformat()
                elif isinstance(val, (list,)):
                    if not self.include_vector and len(val) > 10:
                        continue  # Skip vector columns
                record[col] = val
            records.append(record)

        return records

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  CONNECTOR FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

CONNECTOR_MAP = {
    "milvus":   MilvusConnector,
    "pinecone": PineconeConnector,
    "weaviate": WeaviateConnector,
    "chromadb": ChromaDBConnector,
    "qdrant":   QdrantConnector,
    "pgvector": PgvectorConnector,
}


def get_connector(config):
    db_type = config.get("db_type", "").lower()
    connector_class = CONNECTOR_MAP.get(db_type)
    if not connector_class:
        raise ValueError(f"Unsupported database type: {db_type}. "
                         f"Supported: {', '.join(CONNECTOR_MAP.keys())}")
    return connector_class(config)


# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKPOINT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CheckpointManager:
    """Manages checkpoints using local files in the checkpoint directory."""

    def __init__(self, checkpoint_dir, input_name):
        self.checkpoint_dir = checkpoint_dir
        self.input_name = self._safe_name(input_name)
        self.filepath = os.path.join(checkpoint_dir, f"{self.input_name}.ckpt")

    @staticmethod
    def _safe_name(name):
        return name.replace("://", "_").replace("/", "_").replace("\\", "_")

    def get(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                return data.get("last_value")
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def save(self, value, row_count=0):
        data = {
            "input_name": self.input_name,
            "last_value": str(value),
            "last_run": datetime.now(timezone.utc).isoformat(),
            "row_count": row_count,
        }
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULAR INPUT SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

SCHEME_XML = """<scheme>
    <title>VDConnect</title>
    <description>Collect logs from vector databases — Milvus, Pinecone, Weaviate, ChromaDB, Qdrant, pgvector</description>
    <use_external_validation>true</use_external_validation>
    <use_single_instance>false</use_single_instance>
    <streaming_mode>xml</streaming_mode>

    <endpoint>
        <args>
            <arg name="db_type">
                <title>Database Type</title>
                <description>Vector database type: milvus, pinecone, weaviate, chromadb, qdrant, pgvector</description>
                <required_on_create>true</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="host">
                <title>Host</title>
                <description>Hostname or IP of the vector database</description>
                <required_on_create>true</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="port">
                <title>Port</title>
                <description>Port number</description>
                <required_on_create>true</required_on_create>
                <data_type>number</data_type>
            </arg>
            <arg name="auth_type">
                <title>Auth Type</title>
                <description>Authentication type: api_key, basic, token, none</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="api_key">
                <title>API Key</title>
                <description>API key for authentication</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="username">
                <title>Username</title>
                <description>Username for basic auth</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="password">
                <title>Password</title>
                <description>Password for basic auth</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="token">
                <title>Token</title>
                <description>Bearer token for authentication</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="use_ssl">
                <title>Use SSL</title>
                <description>Enable SSL/TLS</description>
                <required_on_create>false</required_on_create>
                <data_type>boolean</data_type>
            </arg>
            <arg name="collection_name">
                <title>Collection Name</title>
                <description>Name of the collection/index/class/table to query</description>
                <required_on_create>true</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="database_name">
                <title>Database Name</title>
                <description>Database name (for Milvus/pgvector)</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="output_fields">
                <title>Output Fields</title>
                <description>Comma-separated metadata fields to extract (* for all)</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="filter_expr">
                <title>Filter Expression</title>
                <description>Filter expression for querying</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="max_rows">
                <title>Max Rows</title>
                <description>Max records per collection cycle</description>
                <required_on_create>false</required_on_create>
                <data_type>number</data_type>
            </arg>
            <arg name="collection_mode">
                <title>Collection Mode</title>
                <description>rising_column, batch, or tail</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="rising_column">
                <title>Rising Column</title>
                <description>Field name for incremental collection</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="rising_column_type">
                <title>Rising Column Type</title>
                <description>timestamp, integer, or string</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="batch_size">
                <title>Batch Size</title>
                <description>Records per API page/call</description>
                <required_on_create>false</required_on_create>
                <data_type>number</data_type>
            </arg>
            <arg name="include_vector">
                <title>Include Vector</title>
                <description>Include embedding data in events</description>
                <required_on_create>false</required_on_create>
                <data_type>boolean</data_type>
            </arg>
            <arg name="timestamp_field">
                <title>Timestamp Field</title>
                <description>Metadata field to use as Splunk event time</description>
                <required_on_create>false</required_on_create>
                <data_type>string</data_type>
            </arg>
            <arg name="connection_timeout">
                <title>Connection Timeout</title>
                <description>Connection timeout in seconds</description>
                <required_on_create>false</required_on_create>
                <data_type>number</data_type>
            </arg>
            <arg name="query_timeout">
                <title>Query Timeout</title>
                <description>Query timeout in seconds</description>
                <required_on_create>false</required_on_create>
                <data_type>number</data_type>
            </arg>
        </args>
    </endpoint>
</scheme>"""


def log_event(ew, input_name, db_type, level, message, **extra):
    """Write an internal log event to the vdconnect_internal index."""
    event_data = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "level": level,
        "input_name": input_name,
        "db_type": db_type,
        "message": message,
    }
    event_data.update(extra)

    event = Event()
    event.stanza = input_name
    event.index = "vdconnect_internal"
    event.sourcetype = "vdconnect:internal"
    event.source = f"vdconnect://{db_type}/internal"
    event.data = json.dumps(event_data)
    ew.write_event(event)


def run_collection(ew, input_name, config, checkpoint_dir):
    """Execute one collection cycle for a single input."""

    db_type = config.get("db_type", "unknown")
    start_time = time.time()

    log_event(ew, input_name, db_type, "INFO",
              f"Starting collection cycle for {input_name}")

    # ── Initialize checkpoint ──
    ckpt = CheckpointManager(checkpoint_dir, input_name)
    checkpoint_value = ckpt.get()
    mode = config.get("collection_mode", "rising_column")

    if mode == "batch":
        checkpoint_value = None  # Always full dump

    # ── Connect and fetch ──
    connector = get_connector(config)
    try:
        connector.connect()

        # Test connection first
        log_event(ew, input_name, db_type, "INFO", "connection_test",
                  host=config.get("host"), port=config.get("port"),
                  result="success")

        records = connector.fetch_records(checkpoint_value=checkpoint_value)

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_event(ew, input_name, db_type, "ERROR",
                  f"Collection failed: {str(e)}",
                  duration_ms=duration_ms,
                  traceback=traceback.format_exc())
        return
    finally:
        connector.close()

    # ── Write events ──
    target_index = config.get("index", "vdconnect_logs")
    sourcetype = config.get("sourcetype", f"vdconnect:{db_type}")
    source = config.get("source", f"vdconnect://{db_type}/{config.get('collection_name', '')}")
    ts_field = config.get("timestamp_field", "timestamp")
    rising_col = config.get("rising_column", "")
    latest_value = checkpoint_value

    event_count = 0
    for record in records:
        # Extract timestamp
        event_time = None
        if ts_field and ts_field in record:
            event_time = str(record[ts_field])

        # Track rising column
        if rising_col and rising_col in record:
            val = str(record[rising_col])
            if latest_value is None or val > latest_value:
                latest_value = val

        # Inject metadata
        record["vdconnect_db_type"] = db_type
        record["vdconnect_collection"] = config.get("collection_name", "")
        record["vdconnect_input"] = input_name

        # Write event
        event = Event()
        event.stanza = input_name
        event.index = target_index
        event.sourcetype = sourcetype
        event.source = source
        if event_time:
            event.time = event_time
        event.data = json.dumps(record, default=str)
        ew.write_event(event)
        event_count += 1

    # ── Update checkpoint ──
    if mode in ("rising_column", "tail") and latest_value is not None:
        ckpt.save(latest_value, row_count=event_count)

    duration_ms = int((time.time() - start_time) * 1000)
    log_event(ew, input_name, db_type, "INFO",
              f"collection_complete — {event_count} events in {duration_ms}ms",
              duration_ms=duration_ms,
              row_count=event_count,
              checkpoint_value=str(latest_value) if latest_value else "")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN — Splunk Modular Input Entry Points
# ═══════════════════════════════════════════════════════════════════════════════

def do_scheme():
    """Print the introspection scheme (--scheme)."""
    print(SCHEME_XML)


def do_validate(config_xml):
    """Validate the input configuration (--validate-arguments)."""
    # Parse the config_xml and validate required fields
    import xml.etree.ElementTree as ET
    root = ET.fromstring(config_xml)

    item = root.find(".//item")
    if item is None:
        sys.exit(1)

    params = {}
    for param in item.findall("param"):
        params[param.get("name")] = param.text or ""

    db_type = params.get("db_type", "")
    if db_type not in CONNECTOR_MAP:
        print(f"<error><message>Unsupported db_type: {db_type}. "
              f"Must be one of: {', '.join(CONNECTOR_MAP.keys())}</message></error>")
        sys.exit(1)

    if not params.get("host"):
        print("<error><message>Host is required</message></error>")
        sys.exit(1)

    if not params.get("collection_name"):
        print("<error><message>Collection name is required</message></error>")
        sys.exit(1)


def do_run():
    """
    Main execution mode — stream data.
    Reads XML config from stdin and runs the collection.
    """
    import xml.etree.ElementTree as ET

    config_xml = sys.stdin.read()
    root = ET.fromstring(config_xml)

    # Get checkpoint dir
    checkpoint_dir = root.findtext(".//checkpoint_dir",
                                   default="/tmp/vdconnect_checkpoints")

    # Get session key for Splunk API access
    session_key = root.findtext(".//session_key", default="")

    # Iterate over each input stanza
    for item in root.findall(".//item"):
        input_name = item.get("name", "unknown")
        config = {}

        for param in item.findall("param"):
            name = param.get("name")
            value = param.text or ""
            config[name] = value

        # Create a simple EventWriter to stdout
        ew = SimpleEventWriter()

        try:
            run_collection(ew, input_name, config, checkpoint_dir)
        except Exception as e:
            log_event(ew, input_name, config.get("db_type", "unknown"),
                      "ERROR", f"Fatal error: {str(e)}",
                      traceback=traceback.format_exc())


class SimpleEventWriter:
    """Writes events as XML to stdout for splunkd to consume."""

    def __init__(self):
        self._started = False

    def _start(self):
        if not self._started:
            sys.stdout.write("<stream>\n")
            self._started = True

    def write_event(self, event):
        self._start()
        sys.stdout.write("<event")
        if hasattr(event, "stanza") and event.stanza:
            sys.stdout.write(f' stanza="{event.stanza}"')
        sys.stdout.write(">\n")

        if hasattr(event, "time") and event.time:
            sys.stdout.write(f"  <time>{event.time}</time>\n")
        if hasattr(event, "index") and event.index:
            sys.stdout.write(f"  <index>{event.index}</index>\n")
        if hasattr(event, "sourcetype") and event.sourcetype:
            sys.stdout.write(f"  <sourcetype>{event.sourcetype}</sourcetype>\n")
        if hasattr(event, "source") and event.source:
            sys.stdout.write(f"  <source>{event.source}</source>\n")

        data = event.data if hasattr(event, "data") else ""
        # Escape XML special chars
        data = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        sys.stdout.write(f"  <data>{data}</data>\n")
        sys.stdout.write("</event>\n")
        sys.stdout.flush()

    def close(self):
        if self._started:
            sys.stdout.write("</stream>\n")
            sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            config_str = sys.stdin.read()
            do_validate(config_str)
        else:
            do_run()
    else:
        do_run()
