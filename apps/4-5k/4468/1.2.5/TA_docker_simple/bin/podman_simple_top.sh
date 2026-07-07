#!/bin/bash
command_date=$(date +%s)

for container_id in $(podman ps -q); do
  podman top "$container_id" \
    user pid ppid pcpu etime tty time args 2>/dev/null | \
    tail -n +2 | \
    sed -E "s/^(.*)$/${command_date}\t${container_id}\t\1/"
done

