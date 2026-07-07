#!/bin/bash

. `dirname $0`/common.sh

set -u

if queryHaveCommand curl ; then
    fetchcmd="curl -sSf -m 5"
elif queryHaveCommand wget ; then
    fetchcmd="wget -q -T 5 -O -"
else
    failLackMultipleCommands curl wget
fi

AWK_M2CIM='
function print_event (context, sub_context, sourceid, value) {
    printf("context=%s,sub_context=%s", context, sub_context);
    if (sourceid != "") {
        printf(",%s%s\n", sourceid, value);
    } else
        printf("\n");
}

/^[^ \t]+/ {
    if (context != "") {
        print_event(context, sub_context, sourceid, value)
    }
    context = $1
    sub_context = ""
    sourceid = ""
    value = ""
    next
}

/^ +[^=]+$/ {
    if (sub_context != "") {
        print_event(context, sub_context, sourceid, value)
    }

    sub_context = $1
    sourceid = ""
    value = ""
    next
}

/{[^}]*}:/ {
    if (sourceid != "") {
        print_event(context, sub_context, sourceid, value)
    }

    sourceid = gensub("[{}:]", "", "g", $1)
    value = ""
    next
}

{
    value = value "," $1
}

END {
    if (context != "" && sub_context != "")
        print_event(context, sub_context, sourceid, value)
}'

metrics=$($fetchcmd $1 2>&1)
ret=$?

if [ $ret -eq 0 ]; then
    if [[ "$1" =~ /metrics$ ]]; then
        echo "$metrics" | $AWK "$AWK_M2CIM"
    else
        echo $metrics
    fi
else
    echo "ERROR $ret [$fetchcmd $1] $metrics" >&2
fi

exit $ret
