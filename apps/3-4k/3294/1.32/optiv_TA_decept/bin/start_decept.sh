#PYTHON_FILE_DIR="/opt/decept/"
PYTHON_FILE_DIR="/opt/splunk/etc/apps/optiv_TA_decept/bin/"
PROGRAM_NAME="optiv_decept.py"
PROGRAM_DESC="decept"
#PYTHON_EXEC="/bin/python"
PYTHON_EXEC="/opt/splunk/bin/splunk cmd python"

#ps ax | grep decept|grep -v "grep" | wc -l


START_DECEPT="${PYTHON_EXEC} ${PYTHON_FILE_DIR}${PROGRAM_NAME}"

sleep 20
echo "start decept: ${START_DECEPT}"

until $START_DECEPT; do
    echo "Program ${PROGRAM_DESC} crashed with exit code $?.  Respawning.." >&2
    sleep 20
done
