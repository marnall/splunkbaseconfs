# GetDiag App for Splunk

## Overview
The **GetDiag App** provides a comprehensive solution for managing and requesting diagnostic information within Splunk. Users can directly request diagnostics from remote machines by providing the machine's hostname, IP address, or GUID through the **Configuration Dashboard**. The app also enables listing, downloading, uploading, and deleting diagnostics via a user-friendly **Diag List Dashboard**.

This app integrates custom REST endpoints (`getdiag` and `uploaddiag`) for seamless communication and operation.

Additionally, the lightweight **GetDiag Add-On** is included for deployment on remote machines to facilitate diagnostics collection.

## Features
### REST Endpoints
- **`getdiag`**: Handles fetching diagnostic files from specified remote machines.
- **`uploaddiag`**: Facilitates uploading diagnostic files to Splunk.

### Custom Commands
- **`getdiaginfo`**: Lists all diagnostic files and supports deletion.
- **`setupdiag`**: Configures diagnostics retrieval from remote machines.
- **`requestdiag`**: Sends requests for diagnostics from specified remote machines.

### Dashboards
1. **Diag List Dashboard**:
   - Displays available diagnostic files with the following details:
     - Hostname
     - UUID
     - Submission date
   - Supports actions via buttons:
     - **Download**: Retrieve diagnostic files.
     - **Delete**: Remove files from the directory.
     - **Send to Case**: Forward diagnostic files for case management.
   - Automatically updates the list of diagnostics.
   
2. **Configuration Dashboard**:
   - Allows users to request diagnostics directly by entering one or more hostnames, server names, IPs, or GUIDs.
   - Provides a simple interface for initiating diagnostic file generation.

## Installation
1. Clone or download the app into your `$SPLUNK_HOME/etc/apps/` directory.
2. Restart your Splunk instance to apply changes.

### Deploying the Add-On
1. Navigate to the `data/getdiag_addon/` folder.
2. Deploy this folder to the target machines using your preferred deployment method (e.g., Splunk Deployment Server, manual distribution).
3. Ensure the `inputs.conf` in the add-on is properly configured on the target machines.

## Usage
### REST Endpoints
1. Use the `/getdiag` endpoint to fetch diagnostics from remote machines.
2. Use the `/uploaddiag` endpoint to upload diagnostics back to Splunk.

### Custom Commands
1. Use the `| getdiaginfo` command in the Splunk Search interface to list and manage diagnostic files.
2. Use the `| setupdiag` and `| requestdiag` commands to configure and request diagnostics from remote machines.

### Dashboards
1. Navigate to the **Diag List Dashboard** to:
   - View available diagnostics.
   - Perform actions like **Download**, **Delete**, and **Send to Case**.
2. Use the **Configuration Dashboard** to:
   - Enter the hostname, IP, or GUID of remote machines and request diagnostics directly.

## File Structure
```plaintext
GETDIAG/
├── appserver/
│   ├── static/
│   │   ├── diag/                  # Directory for diag files (ignored by Git)
│   │   ├── get_diag_configuration.js # JavaScript for configuration dashboard
│   │   ├── table_button.js        # JavaScript for action buttons
│   │   └── table_decorations.css  # Styles for the dashboard
├── bin/
│   ├── __pycache__/               # Python cache files
│   ├── splunklib/                 # Splunk SDK dependencies
│   ├── getdiag_import.py          # Import-related functionality
│   ├── getdiag.py                 # REST endpoint for fetching diagnostics
│   ├── getdiaginfo.py             # Command to fetch diag information
│   ├── requestdiag.py             # Command to request diagnostics from a remote machine
│   ├── setupdiag.py               # Command to configure diagnostics retrieval
│   ├── uploaddiag.py              # REST endpoint for handling diag uploads
│   ├── upload_diag_linux.py       # Command to upload diag files for Linux
│   └── utils.py                   # Utility functions
├── data/
│   └── getdiag_addon/             # Add-on app to be deployed to target machines
│       ├── bin/                   # Add-on related scripts
│       └── default/
│           └── inputs.conf        # Add-on input configurations
├── default/
│   ├── app.conf                   # App configuration
│   ├── commands.conf              # Custom commands configuration
│   ├── restmap.conf               # REST API mappings for endpoints
│   ├── searchbnf.conf             # Search commands definitions
│   └── web.conf                   # Web configurations
├── metadata/
│   └── local.meta                 # Metadata for local configurations
└── README.md                      # Documentation file