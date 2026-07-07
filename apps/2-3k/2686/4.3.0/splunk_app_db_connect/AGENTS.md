## Overview

This is the Splunk app package directory for DB Connect. Its contents follow the standard Splunk app
anatomy and are what gets installed into `$SPLUNK_HOME/etc/apps/splunk_app_db_connect/`. During
build, files are copied to `stage/` and packaged into the final `.tgz`.

## Directory Structure

| Directory                                                         | Purpose                                                          |
|-------------------------------------------------------------------|------------------------------------------------------------------|
| `appserver/`                                                      | Frontend UI (React components, templates, styles)                |
| `bin/`                                                            | Python scripts, Java entry points, and the `dbx2` Python package |
| `config/`                                                         | Logging configurations for Java servers                          |
| `default/`                                                        | Splunk configuration files (`.conf`)                             |
| `metadata/`                                                       | Splunk permission metadata (`default.meta`)                      |
| `README/`                                                         | Splunk spec files for custom conf files                          |
| `static/`                                                         | App icon and images                                              |
| `locale/`                                                         | i18n message catalogs                                            |
| `certs/`                                                          | Certificate files                                                |
| `drivers/`                                                        | JDBC driver storage                                              |
| `tools/`                                                          | Troubleshooting tools                                            |
| `darwin_x86_64/`, `linux_x86/`, `windows_x86/`, `windows_x86_64/` | Platform-specific binaries                                       |

## Python Layer (`bin/`)

### Entry Points

- `dbx_db_input.py` / `dbx_db_output.py` - Splunk modular input/output handlers
- `dbxquery_bridge.py` - Bridge between Splunk search commands and the Java Query Server
- `dbx_connection_diag.py` - Connection diagnostics
- `dbx_diag.py` - General diagnostics
- `alert_output.py` - Alert action output handler
- `command.sh` / `dbxquery.sh` - Shell launchers for Java processes
- `java_home_detector2.py` / `jre_validator2.py` - JDK detection and validation

### `dbx2/` Package

Core Python package that acts as proxy/middleware between Splunk and the Java backend.

- `configuration_provider.py` - Reads Splunk conf files
- `task_server_configuration_provider.py` - Task Server config
- `query_server_configuration_provider.py` - Query Server config
- `logger.py` / `logger_factory.py` / `logger_provider.py` - Logging setup
- `dbx_logging_formatter.py` - Structured log formatting
- `jvm_options.py` - JVM option management
- `rest/` - Splunk REST API handlers:
    - `proxy.py` - Forwards requests from Splunk REST API to Java Task Server
    - `health_check.py` - Health check endpoint
    - `loglevel.py` - Runtime log level control
    - `settings.py` - Settings management
    - `component.py` / `component_status.py` - Component status tracking
- `splunk_client/` - Splunk API client helpers:
    - `splunk_service_factory.py` - Splunk SDK service creation
    - `shc_cluster_captain_info.py` / `shc_cluster_config.py` - SHC captain detection
    - `api_config.py` - API configuration
    - Entity models: `connection_entity.py`, `identity_entity.py`, `lookup_entity.py`, etc.

### Unit Tests

Located in `../test/unit_test/`. Run with:

```sh
PYTHONPATH=$PWD/package/bin/:$PWD/test/lib py.test test/unit_test/
# Runs: `yarn adapter-unit-tests` (from repo root)
```

## Configuration Files (`default/`)

### Custom DBX Configurations

| File                          | Purpose                                            | Editable via UI |
|-------------------------------|----------------------------------------------------|-----------------|
| `identities.conf`             | Database credentials (encrypted via Bouncy Castle) | Yes             |
| `db_connections.conf`         | Database connections                               | Yes             |
| `db_inputs.conf`              | Data ingestion inputs                              | Yes             |
| `db_input_templates.conf`     | Preconfigured input queries per DB engine          | No              |
| `db_connection_types.conf`    | Supported connection types and defaults            | No              |
| `dbx-jdbc-addons.conf`        | JDBC drivers available on Splunkbase               | No              |
| `dbx_settings.conf`           | Timeouts, cluster, telemetry, HEC, deny lists      | Partially       |
| `dbx-migration.conf`          | Migration types and status                         | No              |
| `dbx_logging.conf`            | Python logging configuration                       | Yes (via UI)    |
| `dbx-embedding-services.conf` | Embedding service configurations                   | -               |

### Standard Splunk Configurations

`app.conf`, `authorize.conf` (RBAC), `restmap.conf` (REST endpoint -> capability mapping),
`commands.conf` (search commands: dbxquery, dbxlookup, dbxoutput), `inputs.conf` (modular inputs:
server, dbxquery), `props.conf`, `macros.conf`, `savedsearches.conf`, `searchbnf.conf`, `web.conf`,
`server.conf`, `alert_actions.conf`, `datamodels.conf`, `checklist.conf`

## Logging Configuration (`config/`)

- `dbx_task_server.yml` - Logback config for the Task Server (server.jar)
- `command_logback.xml` - Logback config for the Query Server (dbxquery.jar / command.jar)
- `dbxquery_server.yml` - Query Server configuration
- `kerberos_client.conf` - Kerberos authentication config

Log levels use system variables and can be changed at runtime through the UI.

## Splunk Views (`default/data/ui/views/`)

- `data_lab.xml` - Inputs, Outputs, Lookups management
- `configuration.xml` - Identities, Connections, Settings, Keystore, Drivers
- `ftr.xml` - First Time Run wizard
- `db_health.xml`, `input_health.xml`, `input_performance.xml` - Monitoring dashboards

## Access Control

Splunk DB Connect leverages Splunk's built-in Role-Based Access Control (RBAC):

1. Roles and capabilities defined in `default/authorize.conf`
2. `default/restmap.conf` maps capabilities to read/write access on `.conf` files and REST API
   endpoints

## Code Style

Python files follow Black formatting (line-length=120, targets py37/py39):

```sh
python -m black <file> --check --diff
python -m black <file>
```
