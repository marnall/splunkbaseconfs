#!/bin/bash
export SPLUNK_APPS=/opt/splunk/etc/apps
usage=$1
latesthash=latest_model_integrity_hash_$(date "+%Y.%m.%d-%H.%M.%S")
curl --silent --show-error --fail  -L -o $latesthash "https://cdn.splunk-ai.com/models/${usage}_model_integrity_hash"
nhashvalue="$(cat $latesthash)"
lhashvalue="$(cat $SPLUNK_APPS/SA-Revelation/lookups/${usage}_model_integrity_hash)"
if cmp $latesthash "$SPLUNK_APPS/SA-Revelation/lookups/${usage}_model_integrity_hash"
then
     echo "$(date "+%Y.%m.%d-%H.%M.%S") | Z^2:Download | INFO | No change for hash of cloud basemodel $nhashvalue and local basemodel $lhashvalue | No basemodel will be downloaded at this time." >> $SPLUNK_APPS/SA-Revelation/log/model_update.log
     rm $latesthash
else
     echo "$(date "+%Y.%m.%d-%H.%M.%S") | Z^2:Download | INFO | Change for hash of cloud basemodel $nhashvalue and local basemodel $lhashvalue | Downloading the updated basemodel and archiving the old basemodel." >> $SPLUNK_APPS/SA-Revelation/log/model_update.log
     curl -L -o __mlspl_base_${usage}_rba_custom.mlmodel "https://cdn.splunk-ai.com/models/__mlspl_base_${usage}_rba_custom.mlmodel"
     mv "$SPLUNK_APPS/SA-Revelation/lookups/${usage}_model_integrity_hash" "$SPLUNK_APPS/SA-Revelation/lookups/archive/${usage}_model_integrity_hash_$(date "+%Y.%m.%d-%H.%M.%S")"
     mv "$SPLUNK_APPS/SA-Revelation/lookups/__mlspl_base_${usage}_rba_custom.mlmodel" "$SPLUNK_APPS/SA-Revelation/lookups/archive/__mlspl_base_${usage}_rba_custom.mlmodel_$(date "+%Y.%m.%d-%H.%M.%S")"
     mv $latesthash "$SPLUNK_APPS/SA-Revelation/lookups/${usage}_model_integrity_hash"
     mv __mlspl_base_${usage}_rba_custom.mlmodel "$SPLUNK_APPS/SA-Revelation/lookups/__mlspl_base_${usage}_rba_custom.mlmodel"
     echo "$(date "+%Y.%m.%d-%H.%M.%S") | Z^2:Download | INFO | Change for hash of cloud basemodel $nhashvalue and local basemodel $lhashvalue | Basemodel update and archival complete." >> $SPLUNK_APPS/SA-Revelation/log/model_update.log
fi
#sleep(10s)