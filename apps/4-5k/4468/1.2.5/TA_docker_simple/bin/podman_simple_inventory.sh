#!/bin/bash
# podman inspect $(podman ps -aq) | jq -c -M -r ".[]"
podman inspect $(podman ps -aq) | jq -c -M -r '.[] | delpaths([paths | select(.[-1] | strings | startswith("Env"))])'
