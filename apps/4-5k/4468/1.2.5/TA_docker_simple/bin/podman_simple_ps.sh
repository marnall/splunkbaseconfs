#!/bin/bash
command_date=$(date +%s)

for id in $(podman ps -a --format "{{.ID}}"); do
  size_bytes=$(podman inspect --size --format '{{.SizeRootFs}}' "$id" 2>/dev/null)
  size_human=$(numfmt --to=iec --suffix=B "$size_bytes" 2>/dev/null)
  [[ -z "$size_human" ]] && size_human="0B"

  ps_line=$(podman ps -a --filter "id=$id" --format "${command_date}\t{{.ID}}\t{{.Image}}\t{{.Names}}\t\"{{.Command}}\"\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}\t{{.Mounts}}")
  net_mode=$(podman inspect --format '{{.HostConfig.NetworkMode}}' "$id" 2>/dev/null)
  [[ -z "$net_mode" ]] && net_mode="-"

  echo -e "${ps_line}\t${net_mode}\t${size_human}"
done

