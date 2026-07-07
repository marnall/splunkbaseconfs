#!/bin/sh
# This script resolves binary which should be executed based on uname output.
# Binaries are kept inside /bin under directories from a following list:
# - linux_x86_64
# - linux_arm64
# - linux_ppc64le
# - linux_s390x
# - darwin_x86_64
# - darwin_arm64
# - windows_x86
# - windows_x86_64
# - freebsd_amd64
# - solaris_amd64
# - aix_ppc64
# 
# windows_x86, windows_x86_64, darwin_x86_64, linux_x86_64 should be handled
# by modular input feature automatically. Only the rest needs to be
# explicitly resolved.

if [ "$1" = "--scheme" ]
then
    # we use default scheme, exit immediately
    exit 0
fi

KERNEL=$(uname -s)
ARCH=$(uname -m)
LOG_PATH=$SPLUNK_HOME/var/log/splunk/effective_configuration.log
TIME_FORMAT="+%Y-%m-%dT%H:%M:%S.000Z"
TIME='time'
MESSAGE='message'
LOG_LEVEL='level'
LOG_LEVEL_INFO='INFO'
LOG_LEVEL_ERROR='ERROR'

printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on on $KERNEL $ARCH." >> "$LOG_PATH"

case "$KERNEL" in
    "Linux")
        if [ "$ARCH" = "ppc64le" ] 
        then
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u "$TIME_FORMAT")" $MESSAGE "Starting effective-configuration-add-on from binary located in linux_ppc64le directory." >> "$LOG_PATH"
            exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/linux_ppc64le/bin/effective-configuration-add-on"
        elif [ "$ARCH" = "s390x" ]
        then
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in linux_s390x directory." >> "$LOG_PATH"
            exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/linux_s390x/bin/effective-configuration-add-on"
        elif echo "$ARCH" | grep -e '^aarch*' -e '^arm*';
        then
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in linux_arm64 directory." >> "$LOG_PATH"
            exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/linux_arm64/bin/effective-configuration-add-on"
        else
            # linux_amd64 should be handled by modular inputs
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_ERROR $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Unsupported platform: $KERNEL $ARCH." >> "$LOG_PATH"
        fi
        ;;
    "SunOS")
        ARCH=$(uname -p)
        printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Resolved effective-configuration-add-on on $KERNEL $ARCH" >> "$LOG_PATH"
        if echo "$ARCH" | grep -q 'sparc'; then
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_ERROR $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Unsupported platform: $KERNEL $ARCH." >> "$LOG_PATH" # DMXAM-1121
        elif [ "$ARCH" = "i386" ] || [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "x64" ] || [ "$ARCH" = "amd64" ] 
        then
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in solaris_amd64 directory." >> "$LOG_PATH"
            exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/solaris_amd64/bin/effective-configuration-add-on"
        else
            printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_ERROR $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Unsupported platform: $KERNEL $ARCH." >> "$LOG_PATH"
        fi
        ;;
    "Darwin")
        printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in darwin_arm64 directory." >> "$LOG_PATH"
        exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/darwin_arm64/bin/effective-configuration-add-on"
        ;;
    "FreeBSD")
        printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in freebsd_amd64 directory." >> "$LOG_PATH"
        exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/freebsd_amd64/bin/effective-configuration-add-on"
        ;;
    "AIX")
        printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_INFO $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Starting effective-configuration-add-on from binary located in aix_ppc64 directory." >> "$LOG_PATH"
        exec "$SPLUNK_HOME/etc/apps/Splunk_TA_effective_configuration/aix_ppc64/bin/effective-configuration-add-on"
        ;;
    *)
        # windows_x86, windows_amd64 should be handled by modular inputs
        printf "{\"%s\":\"%s\",\"%s\":\"%s\",\"%s\":\"%s\"}\n" $LOG_LEVEL $LOG_LEVEL_ERROR $TIME "$(date -u $TIME_FORMAT)" $MESSAGE "Unsupported platform: $KERNEL $ARCH." >> "$LOG_PATH"
        exit 1
        ;;
esac
