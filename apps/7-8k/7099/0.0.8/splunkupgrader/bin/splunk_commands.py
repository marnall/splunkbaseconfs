import shlex, os
import subprocess


def start(splunk_home, logger):
    run_start = "{}/bin/splunk start --accept-license --answer-yes".format(splunk_home)
    run_start = shlex.split(run_start)
    logger.info("Starting to run the command: {}".format(run_start))
    text = subprocess.check_output(run_start)
    logger.info("Successfully restarted splunk.")
    return text
    
def stop(splunk_home):
    run_stop = "{}/bin/splunk stop".format(splunk_home)
    run_stop = shlex.split(run_stop)
    text = subprocess.check_output(run_stop)
    return text

def restart(splunk_home, logger):
    splunk_home = os.getenv('SPLUNK_HOME')
    splunk_proc = subprocess.check_output('/opt/splunk/bin/splunk display boot-start', shell=True)
    splunk_proc = splunk_proc.decode('utf-8')
    is_systemd = splunk_proc.split('\n')[5]
    if is_systemd.startswith("Systemd unit file installed"):
        try:
            logger.info("Splunk is running as systemd.")
            logger.info("Restarting Splunkd.")
            # os.system('whoami')
            # os.system('sudo systemctl restart Splunkd.service')
            os.system("sudo {}/bin/splunk restart --accept-license --answer-yes --no-prompt".format(splunk_home))
            text = "Splunk restarted successfully."
            logger.info(text)
            return(text)
        except OSError as ose:
            text = ("An error occured", ose)
            logger.info(text)
            return text
        pass
    else:
        logger.info("Splunk is running as init.d")
        logger.info("Restarting Splunk")
        os.system("{}/bin/splunk restart --accept-license --answer-yes --no-prompt".format(splunk_home))
        text = "Splunk Restarted Successfully."
        logger.info(text)
        return text
    
def reload(logger):
    splunk_home = os.getenv('SPLUNK_HOME')
    splunk_proc = subprocess.check_output('/opt/splunk/bin/splunk display boot-start', shell=True)
    splunk_proc = splunk_proc.decode('utf-8')
    is_systemd = splunk_proc.split('\n')[5]
    if is_systemd.startswith("Systemd unit file installed"):
        try:
            logger.info("Splunk is running as systemd.")
            logger.info("Reloading Splunkd.")
            # os.system('whoami')
            # os.system('sudo systemctl restart Splunkd.service')
            os.system("sudo systemctl daemon-reload")
            text = "Splunkd was reloaded successfully."
            logger.info(text)
            return text
        except OSError as ose:
            text = ("An error occured", ose)
            logger.error(text)
            return text
        pass
    else:
        logger.info("Splunkd is running as init.d")
        logger.info("No need for a reload")
        return text