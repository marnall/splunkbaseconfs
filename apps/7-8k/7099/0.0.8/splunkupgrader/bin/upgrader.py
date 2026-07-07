import sys, os
from glob import glob
from tarfile import TarFile
import subprocess
import shlex
# from splunk_start import start
import backup
import splunk_commands

def splunk_upgrade(logger):
    splunk_home = os.environ.get('SPLUNK_HOME')
    app_path = os.path.join(splunk_home, 'etc', 'apps', 'splunkupgrader')
    base_path = splunk_home.split('/')[-2]
    base_path = os.path.join('/', base_path)
    
    os.chdir("{}/bin".format(app_path))
    curdir = os.getcwd()
    install_file = glob('splunk-*.tgz')[-1]
    logger.info('Starting to install {}.'.format(install_file))

    # Using subprocess to perform the upgrade since TarFile kept giving permission errors on the openssl dir.
    logger.info("Extracting file {}".format(install_file))
    tar_command = shlex.split("tar xzvf {}/bin/{} -C {}".format(app_path, install_file, base_path))
    # splunk_status_cmd = shlex.split("{}/bin/splunk status --accept-license --answer-yes --no-prompt".format(splunk_home))
    output = subprocess.check_output(tar_command)
    output = output.splitlines()
    # subprocess.check_output(splunk_status_cmd)
    logger.info("Completed extracting {}".format(install_file))
    text = {'text': 'Completed upgrading splunk. Please restart Splunk.'}
    return text
    

# if __name__ == '__main__':
#     main()

