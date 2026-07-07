#!/bin/bash
source /opt/caspida/bin/CaspidaCommonEnv.sh
source /opt/caspida/bin/CaspidaFunctions
unset LD_LIBRARY_PATH

PostgresHost=`grep "persistence.datastore.rdbms.host" $CASPIDA_PROPERTIES | awk -F "=" '{ print $2 }' | awk -F ":" '{ print $1 }'`
PostgresPort=`grep "persistence.datastore.rdbms.port" $CASPIDA_PROPERTIES | awk -F "=" '{ print $2 }' | awk -F ":" '{ print $1 }'`
export PGUSER=`readProperty persistence.datastore.rdbms.username`
export PGPASSWORD=`readProperty persistence.datastore.rdbms.password`

sql="select row_to_json(backendStats) from backendStats"
/usr/bin/psql -h ${PostgresHost} -p ${PostgresPort} -d caspidadb -c "${sql}" -t | sed 's/\\//g' | sed 's/\"{/{/g' | sed 's/}\"/}/g'
