#!/bin/bash
command_date=$(date +%s)
podman stats --no-stream --format "${command_date}\t{{.ID}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"

