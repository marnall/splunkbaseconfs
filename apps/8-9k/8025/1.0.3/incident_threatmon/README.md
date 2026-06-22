

# incident_threatmon

Splunk Add-on for ingesting and managing Threatmon incidents.


## Features
- Modular Input: Fetches incidents from Threatmon API with pagination and checkpointing
- Dashboard: Lists and visualizes Threatmon incidents
- Search command: Update incident status via Threatmon API
- Workflow actions: Change incident status directly from Splunk UI


## Quick start
1. Install into `$SPLUNK_HOME/etc/apps/incident_threatmon` and restart Splunk.
2. Configure data input in Splunk UI (see `default/inputs.conf`).
3. Use dashboard to view incidents.
4. Use workflow actions or search command to update incident status.

## Splunkbase Requirements
- Supported Splunk versions: 8.x, 9.x
- Supported platforms: Linux, Windows
- Python version: 3.x
- Permissions: read, write


## API Requirements
- API URL: `https://external.threatmonit.io/api/threatmon/external/v1`
- API Key: Obtain from Threatmon portal


## Data Model
Fields: `alarmCode`, `title`, `description`, `severity`, `status`, `alarmDate`, ...


## Status Update
Use the search command `threatmonsetstatus` or workflow action to update status:
```
| threatmonsetstatus alarm_id=<alarmCode> status=Resolved api_url=<API_URL> api_key=<API_KEY>
```
