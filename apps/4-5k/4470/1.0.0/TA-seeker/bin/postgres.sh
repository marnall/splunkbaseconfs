#/bin/bash
# PostrGRES SQL Status

runuser -l  seeker -c '/opt/seeker/install/database/bin/pg_ctl -D /opt/seeker/data/server/pg_data status'