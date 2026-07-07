#!/bin/bash
CORPSE=necromancer.log
DEATH_COUNT=0
SOUL=$CORPSE
GRAVE_COUNT=$(du -b /opt/splunk*/etc/*apps/necromancer/logs/$CORPSE | tr -s '\t' ' ' | cut -d' ' -f1)
TOMB_COUNT=262144000
#rotating @250MB
if [[ $GRAVE_COUNT -gt $TOMB_COUNT ]]; then
while [[ -e "$SOUL" ]]; do
    printf -v SOUL '%s-%02d' "$CORPSE" "$(( ++DEATH_COUNT ))"
done

GRAVE= printf 'CryptKeeper has opened a new crypt,"%s" sealing.\n' "$SOUL"
#OBITUARY= printf 'Now, be sealed"%s".\n' "$SOUL"
CRYPT= mv /opt/splunk*/etc/*apps/necromancer/logs/$CORPSE /opt/splunk*/etc/*apps/necromancer/logs/$SOUL
RELIC= touch /opt/splunk*/etc/*apps/necromancer/logs/$CORPSE


$GRAVE
#$OBITUARY
$CRYPT
$RELIC
fi
