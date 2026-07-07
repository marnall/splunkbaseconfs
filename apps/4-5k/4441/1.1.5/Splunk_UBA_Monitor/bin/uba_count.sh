#!/bin/bash
source /opt/caspida/bin/CaspidaCommonEnv.sh
source /opt/caspida/bin/CaspidaFunctions
unset LD_LIBRARY_PATH

PostgresHost=`grep "persistence.datastore.rdbms.host" $CASPIDA_PROPERTIES | awk -F "=" '{ print $2 }' | awk -F ":" '{ print $1 }'`
PostgresPort=`grep "persistence.datastore.rdbms.port" $CASPIDA_PROPERTIES | awk -F "=" '{ print $2 }' | awk -F ":" '{ print $1 }'`
export PGUSER=`readProperty persistence.datastore.rdbms.username`
export PGPASSWORD=`readProperty persistence.datastore.rdbms.password`

threat="SELECT COUNT(*) FROM v_threats WHERE isActive=true;"
anomaly="SELECT COUNT(*) FROM v_anomalies WHERE status='Active';"
user="SELECT COUNT(*) FROM v_users;"
device="SELECT COUNT(*) FROM v_systems;"
app="SELECT COUNT(*) FROM v_applications;"

for type in threat anomaly user device app; do
    cmd=${!type}
    count=$(/usr/bin/psql -h ${PostgresHost} -p ${PostgresPort} -d caspidadb -t -c "${cmd}" | tr -d ' ')
    if [ $? -ne 0 ]; then
        exit 1
    fi
    printf "type=${type} uba_count=${count}\n"
done
