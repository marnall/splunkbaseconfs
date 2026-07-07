#!/bin/bash

source /opt/caspida/bin/CaspidaCommonEnv.sh
source /opt/caspida/bin/CaspidaFunctions
unset LD_LIBRARY_PATH

redis=$(grep persistence.redis.server $CASPIDA_PROPERTIES | cut -d "=" -f 2 | cut -d "," -f 1)
eps=$(redis-cli -h ${redis} ${RedisAuthCmd} -c get caspida:eps 2> /dev/null)
if [[ $? -ne 0 ]]; then
    exit 1
fi
printf "${eps}\n"

eps_etl=$(/opt/caspida/bin/status/eps_etl 2> /dev/null)
printf "***SPLUNK*** source=uba:eps:etl\n${eps_etl}\n"
