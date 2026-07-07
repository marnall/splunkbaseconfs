#!/bin/bash
podman events --stream=true --format '{{.Time}} {{.Type}} {{.Status}} {{.ID}} ({{- $first := true }}{{- range $k, $v := .Attributes}}{{if not $first}}, {{end}}{{printf "%s=%s" $k $v}}{{- $first = false }}{{- end}})' | grep --line-buffered -vE "exec_(start|create|die)|top"

