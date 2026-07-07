#!/bin/sh

# debug
# set -x

#set this to the home path of your Splunk install
SPLUNK_HOME=/opt/splunk

pid='-1'
configFilepath="estreamer.conf"
pybin="$SPLUNK_HOME/bin/python3"
basepath="$SPLUNK_HOME/etc/apps/TA-eStreamer/bin/encore/"
datapath="$SPLUNK_HOME/etc/apps/TA-eStreamer/bin/encore/data"
procpathfile="$SPLUNK_HOME/etc/apps/TA-eStreamer/bin/encore/*_proc.pid"
isRunning=0

# constants
configure="$pybin ./estreamer/configure.py $configFilepath"
diagnostics="$pybin ./estreamer/diagnostics.py $configFilepath"
service="$pybin ./estreamer/service.py $configFilepath"
preflight="$pybin ./estreamer/preflight.py $configFilepath"

pidFile="encore.pid"

EXIT_CODE_ERROR=1

# change pwd
cd $basepath


chk_env() {

    if [ -z ${LD_LIBRARY_PATH+x} ] || [ -z ${SPLUNK_HOME+x} ]; then
        echo "In order to use the Splunk openssl library to process the certificate file you must set the LD_LIBRARY_PATH"
        echo "     1) Run the following"
        echo "            export SPLUNK_HOME=/opt/splunk"
        echo "            export LD_LIBRARY_PATH=\$SPLUNK_HOME/lib"
        echo "        This will need to be set everytime the session is terminated, to make it permanent perform the following"
        echo ""
        echo "     2) Edit the  ~/.bash_profile or equivalent depending on your OS, and add the following"
        echo "            export SPLUNK_HOME=/opt/splunk          #Modify if your SPLUNK_HOME directory is not /opt/splunk"
        echo "            export LD_LIBRARY_PATH=\$SPLUNK_HOME/lib"
        echo "        Save the file then run"
        echo "            source ~/.bash_profile"
        echo ""
        echo "Bug Reference"
		echo "https://community.splunk.com/t5/Developing-for-Splunk-Enterprise/How-to-get-Splunk-Python-on-CentOS-to-use-SSL-Crypto/m-p/310051"
        exit
    else
        SPLUNK_HOME="${SPLUNK_HOME}"
        LD_LIBRARY_PATH="${LD_LIBRARY_PATH}"
    fi

}

setup_page() {
    cp ../setup.xml ../../default
}

setup() {
    $configure --enabled=true
    $configure --output=splunk
}

init() {
    pythonVersion=`$pybin -V 2>&1 | grep "Python 3*"`

    if [ ! -e "$configFilepath" ]
    then
        cp default.conf $configFilepath
        setup
    fi

    $preflight
    ok=$?
    if [ "$ok" -ne 0 ]
    then
        exit $EXIT_CODE_ERROR
    fi

    pidFile=`$configure --print pidFile`
    pid=`$configure --print pid`

    # Work out if we're running already
    ps ax | grep -F -- $pid | grep -v 'grep' > /dev/null 2>&1
    process=$?
    if [ $pid = '-1' ]
    then
        : #echo "Checking pid.... none found."

    elif [ $process -eq 1 ]
    then
        # echo "Stale pidFile ($pid). Removing"
        rm $pidFile
        pid=-1

    elif [ $process -eq 0 ]
    then
        # echo "$service ($pid) is running."
        isRunning=1

    fi
}

preflight() {
    $preflight --nostdin
    ok=$?
    if [ "$ok" -ne 0 ]
    then
        exit $EXIT_CODE_ERROR
    fi

    pidFile=`$configure --print pidFile`
    pid=`$configure --print pid`

    # Work out if we're running already
    ps ax | grep -F -- $pid | grep -v 'grep' > /dev/null 2>&1
    process=$?

    if [ $pid = '-1' ]
    then
        : #echo "Checking pid.... none found."

    elif [ $process -eq 1 ]
    then
        # echo "Stale pidFile ($pid). Removing"
        rm $pidFile
        pid=-1

    elif [ $process -eq 0 ]
    then
        # echo "$service ($pid) is running."
        isRunning=1

    fi
}

diagnostics() {
    $diagnostics
}

foreground() {
    $service
}

start() {
    if [ $isRunning -eq 0 ]
    then
        echo -n "Starting \"$service\". "
        $service > /dev/null 2>&1 &
        sleep 1

        pid=`$configure --print pid`
        echo "Started. pid=$pid"

    else
        echo "$service is already running."

    fi
}

stop() {
    if [ $isRunning -eq 0 ]
    then
        echo "Not running"

    else
        echo "Found pid. Terminating \"$service\" ($pid)"
        kill -s INT $pid

        # Wait for the process to finish
        while [ 1 ]
        do
            # Do not redirect stdErr - Splunk no likey
            ps ax | grep -F -- $pid | grep -v 'grep' > /dev/null #2>&1
            process=$?

            if [ $process -eq 1 ]
            then
                break
            fi

            sleep 0.5
        done

        pid='-1'
        isRunning=0
        sleep 1

    fi
}

status() {
    $configure --print splunkstatus
}

clean() {
    # Delete data older than 12 hours -> 720mins
    # NOTE:  This is a static directory, please use caution in executing this utility and modify as needed
    find /opt/splunk/etc/apps/TA-eStreamer/bin/encore/data -type f -mmin +720 -delete
}

restart() {
    stop
    start
}

ts() {
    tar -zcvf ../"encore-ts-$(date '+%Y-%m-%d_%H-%M-%S%z(%Z)').tar.gz" *
}

main() {
    case "$1" in
        start)
            init
            preflight
            start
            ;;

        stop)
            init
            preflight
            stop
            ;;
        
	clean)
	    init
	    clean
	    ;;

        restart)
            restart
            ;;
        
        test)
	    chk_env
            diagnostics
            ;;

        foreground)
            foreground
            ;;

        status)
	    status
	    ;;
	    
        setup)
            setup
            ;;

        setup_page)
	    setup_page
	    ;;
	
        ts)
	    ts
	    ;;
	     
        *)
            echo $"Usage: $prog {start | stop | restart | foreground | test | setup}"
            echo
            echo '    start:      starts eNcore as a background task'
            echo '    stop:       stop the eNcore background task'
            echo '    restart:    stop the eNcore background task'
            echo '    foreground: runs eNcore in the foreground'
            echo '    test:       runs a quick test to check connectivity'
            echo '    setup:      change the output (splunk | cef | json)'
            echo '    status:     returns the current status in a splunk way'
            echo
            echo $1
            exit $EXIT_CODE_ERROR

    esac
}
init
main $1
