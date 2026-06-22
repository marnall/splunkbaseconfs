#!/bin/bash
# Wrapper script to ensure Python 3 execution on Splunk Cloud

# Find Splunk's Python 3
if [ -n "$SPLUNK_HOME" ]; then
    PYTHON="$SPLUNK_HOME/bin/python3"
else
    PYTHON="python3"
fi

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Execute the Python script with all arguments
exec "$PYTHON" "$DIR/nucleus_logs.py" "$@"
