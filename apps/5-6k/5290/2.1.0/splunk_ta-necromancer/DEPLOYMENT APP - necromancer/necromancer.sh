#!/bin/bash
WRITE_TO_LOG="/opt/splunk*/etc/*apps/necromancer/logs/necromancer.log"

echo "summon = 'Necromancer has been summoned to check Splunkd: $(date)'" >> $WRITE_TO_LOG

if systemctl status Splunkd.service | grep -q dead
then
        sudo systemctl start Splunkd.service
        echo "status = 'Splunkd was found dead.'" >> $WRITE_TO_LOG
        echo "action = 'Necromancer is resurrecting Splunkd.'" >> $WRITE_TO_LOG
        echo "result = 'Resurrection of Splunkd complete.'" >> $WRITE_TO_LOG
else
        echo "status = 'Splunkd is alive.'"  >> $WRITE_TO_LOG
        echo "action = 'Necromancer does not perform ritual.'" >> $WRITE_TO_LOG
        echo "result = 'Splunkd's heart continues to beat.'" >> $WRITE_TO_LOG
fi
