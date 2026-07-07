import os
import sys
import subprocess
import glob
from datetime import datetime
import shlex
import tarfile
from build_list import file_list


splunk_home = os.getenv('SPLUNK_HOME')
base_dir = splunk_home.split('/')[1]
splunk_dir = splunk_home.split('/')[2]
base_dir = os.path.join('/', base_dir)
bin_dir = os.path.join(splunk_home, 'bin')
# os.chdir(bin_dir)
# cur_dir = os.getcwd()
path = "{}/bin/splunk".format(splunk_home)
command = "./splunk diag"
# exclude = None
exclude = "*/var/*"
# full_command = "{} {}".format(command, exclude)

now = datetime.now()
cur_time = now.strftime("%m-%d-%Y_%H-%M-%S")
tar_file_name = "splunk_backup-{}.tgz".format(cur_time)
splunk_upgrader_name = "splunk_upgrader_backup-{}.tgz".format(cur_time)




def run_diag():
    if exclude is not None:
        subprocess.run([path, "diag", "--exclude", exclude], stdout=subprocess.PIPE)
    else:
        subprocess.run([path, "diag"], stdout=subprocess.PIPE)
    os.chdir(os.environ.get('SPLUNK_HOME'))
    diag_files = glob.glob('diag-*')

def run_tar(logger):
    logger.info("Backup to file {} started.".format(tar_file_name))
    os.chdir(splunk_dir)
    tar_command = "tar --exclude='var' --exclude='splunk_upgrader' --exclude '.tgz' --exclude='.gz' -czvf {} .".format(tar_file_name)
    tar_command = shlex.split(tar_command)
    logger.info("Running the command {}".format(tar_command))
    try:
        output = subprocess.check_output(tar_command)
        out_list = []
        out_list = output.splitlines()
        logger.info("Backed up Files: {}".format(out_list))
        text = {"text": "Backup completed successfully to {}".foramt(tar_file_name)}
        return text
    except subprocess.CalledProcessError as e:
        logger.info(f"Command failed with return code {e.returncode}")

# Added kvstore backup to the process.
def backup_kvstore(logger, username, password):
    logger.info('Backing up kvstore.')
    path = os.path.join(os.getenv('SPLUNK_HOME'), 'bin', 'splunk')
    command = '{} backup kvstore -auth {}:{}'.format(path, username, password)
    command = shlex.split(command)
    run_command = subprocess.check_output(command)
    if run_command == b'':
        kvstore_backup_loc = os.path.join(os.getenv('SPLUNK_DB'), 'kvstorebackup')
        os.chdir(kvstore_backup_loc)
        kvstore_len = len(glob.glob('*.tar.gz'))
        if kvstore_len > 1:
            kvstore_backup_file = glob.glob('*.tar.gz')[-1]
        else:
            kvstore_backup_file = glob.glob('*.tar.gz')
        logger.info("Finished backiing up kvstore to {}".format(kvstore_backup_file))
    else:
        logger.info("Failed backing up kvstore.")

# Added a filter for the .tgz files with addtional logging
def create_exclude_tgz_files(logger):
    def exclude_tgz_files(tarinfo):
        if tarinfo.name.endswith('.tgz'):
            logger.info("Skipping file: {}.".format(tarinfo.name))
            return None
        else:
            return tarinfo
    return exclude_tgz_files
    
# Using this function from the run_backup.py
def tar_file_cmd(logger, username, password):
    backup_kvstore(logger, username, password)
    logger.info("Backing up to {}.".format(tar_file_name))
    splunk_files = file_list(logger)
    os.chdir(splunk_home)
    tf = tarfile.TarFile.open(tar_file_name, 'w:gz')
    exclude_tgz_files = create_exclude_tgz_files(logger)
    for file in splunk_files:
        if os.path.isdir(file):
            logger.info("Adding {} to {}".format(file, tar_file_name))
            tf.add(file, recursive=True, filter=exclude_tgz_files)
        else:
            logger.info("Adding {} to {}".format(file, tar_file_name))
            tf.add(file, filter=exclude_tgz_files)
    tf.close()
    text = "Backup to file {} complete.".format(tar_file_name)
    logger.info(text)
    return text
    
def backup_app():
    app_dir = "{}/etc/apps/splunk_upgrader".format(splunk_home)
    os.chdir(app_dir)
    files = []
    files = os.listdir()
    tf = tarfile.TarFile.open(splunk_upgrader_name, 'w:gz')
    for file in files:
        if file.endswith('.py'):
            tf.add(file)
    tf.close()
    


    
# backup_app()
# tar_file_cmd()
# username = 'admin'
# password = 'password'
# backup_kvstore(username, password)



