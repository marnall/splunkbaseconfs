kill $(ps aux | grep optiv_decept | grep python | awk '{print $2}')
kill $(ps aux | grep start_decept.sh | grep -v grep | awk '{print $2}')
