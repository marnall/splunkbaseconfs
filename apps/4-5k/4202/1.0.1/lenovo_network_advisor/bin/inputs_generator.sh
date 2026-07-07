#!/bin/sh


HEALTH_INTERVAL=`grep ^Health_Interval ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`
HEALTH_LOG=`grep ^Health_Log_File ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`

if [ ! -n "$HEALTH_INTERVAL" ]; then
	HEALTH_INTERVAL=60
fi

# generate similar general input.conf,  which always has hooks triggered with fixed time interval.
# Find the The real binding relationship in python script (called by hook bash script)
# With the forwarder host name,  decide if the real monitor action should be performed.
echo "[script:///opt/splunk/etc/apps/lenovo_network_advisor/bin/health_start_hooks.sh]"
echo "interval = $HEALTH_INTERVAL"
echo "[monitor://$HEALTH_LOG]"


TRAFFIC_INTERVAL=`grep ^Traffic_Interval ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`
TRAFFIC_LOG=`grep ^Traffic_Log_File ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`

if [ ! -n "$TRAFFIC_INTERVAL" ]; then
	TRAFFIC_INTERVAL=60
fi

echo "[script:///opt/splunk/etc/apps/lenovo_network_advisor/bin/traffic_start_hooks.sh]"
echo "interval = $TRAFFIC_INTERVAL"
echo "[monitor://$TRAFFIC_LOG]"

CONGESTION_INTERVAL=`grep ^Congestion_Interval ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`
CONGESTION_LOG=`grep ^Congestion_Log_File ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`

if [ ! -n "$CONGESTION_INTERVAL" ]; then
        CONGESTION_INTERVAL=60
fi

echo "[script:///opt/splunk/etc/apps/lenovo_network_advisor/bin/congestion_start_hooks.sh]"
echo "interval = $CONGESTION_INTERVAL"
echo "[monitor://$CONGESTION_LOG]"


BUFFUTIL_INTERVAL=`grep ^Buffer_Interval ../default/lenovo_inspector.conf  | sed -e 's/=/ /g' | awk '{ print $2 }'`
BUFFUTIL_LOG=`grep ^Buffutil_Log_File ../default/lenovo_inspector.conf | sed -e 's/=/ /g' | awk '{ print $2 }'`

if [ ! -n "$BUFFUTIL_INTERVAL" ]; then
        BUFFUTIL_INTERVAL=60
fi

echo "[script:///opt/splunk/etc/apps/lenovo_network_advisor/bin/buffutil_start_hooks.sh]"
echo "interval = $BUFFUTIL_INTERVAL"
echo "[monitor://$BUFFUTIL_LOG]"



