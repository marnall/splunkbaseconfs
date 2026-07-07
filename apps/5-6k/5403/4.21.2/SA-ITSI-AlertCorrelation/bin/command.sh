#!/usr/bin/env sh

if [ -n "$JAVA_HOME" ];then
    JAVA_CMD="$JAVA_HOME/bin/java"
else
    JAVA_CMD="java"
fi

exec $JAVA_CMD "$@"
