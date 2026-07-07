#!/bin/sh
fecha=$(date +"%Y-%m-%d %H:%M:%S")
todo=$@
echo $fecha"--Evento="$todo >> /var/log/ossim_action.log
