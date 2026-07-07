from glob import glob
import os, sys
import re
import shutil
from tarfile import TarFile
from splunk_commands import start
from splunk_commands import stop
import subprocess
import shlex
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)


splunk_home = os.getenv('SPLUNK_HOME')
base_path = splunk_home.split('/')[1]
etc_path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc')
app_path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps')
splunk_upgrader_path = os.path.join(app_path, 'splunkupgrader')
splunk_upgrader_bin = os.path.join(splunk_upgrader_path, 'bin')
app_files = sorted(os.listdir(app_path))
etc_files = sorted(os.listdir(etc_path))
main_files = sorted(os.listdir(splunk_home))
kvstore_loc = os.path.join(os.getenv('SPLUNK_DB'), 'kvstore')


# def setup_logger():
#     logger = logging.getLogger('splunkupgrader')
#     log_file = os.path.join(os.getenv('SPLUNK_HOME'), 'var', 'log', 'splunk', 'splunkupgrader.log')
#     logging.basicConfig(filename =log_file, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
#     return logger
    
    
def etc_app_dirs(logger):
    
    for item in etc_files:
        if item =="apps":
            etc_files.remove(item)
    
    for item in app_files:
        if item == 'splunkupgrader':
            app_files.remove(item)
        if item == 'SA-VSCode':
            app_files.remove(item)
        if item == 'config_explorer':
            app_files.remove(item)
    return etc_files, app_files

def create_tf_txt(logger):
    os.chdir(splunk_upgrader_bin)
    install_file = glob('splunk-*.tgz')[-1]
    if os.path.exists('tf.txt'):
        os.remove('tf.txt')
    tar = TarFile.open(install_file)
    comp_files = tar.getnames()
    tar.close()
    tf = open("tf.txt", "w")
    for file in comp_files:
        logger.info("Writing {} to {}".format(file, tf.name))
        tf.write("{} \n".format(file))
    tf.close()
    text = "Finished creating file {}".format(tf.name)
    return text


def remove_file_dirs(logger):
    for file in main_files:
        if file == 'bin':
            message = "Skipping folder: {}".format(file)
            logger.info(message)
        elif file == 'etc':
            message = "Skipping folder: {}".format(file)
            logger.info(message)
        elif file == 'lib':
            message = "Skipping folder: {}".format(file)
            logger.info(message)
        elif file == 'var':
            message = "Skipping folder: {}".format(file)
            logger.info(message)
        else:
            path = "{}/{}".format(splunk_home, file)
            if os.path.isdir(path):
                shutil.rmtree(path)
    

def run_untar(logger):
    # stop(splunk_home)
    os.chdir(splunk_home)
    
    # Had to move back to using subprocess with restores as it won't overwrite files if they exist. 
    # We are already exluding the dirs from the list that we don't want to overwrite.
    tar_file = glob('splunk_backup*.tgz')[-1]
    tar_command = shlex.split("tar xzvf {} --exclude=etc/apps/splunkupgrader".format(tar_file))
    logger.info('Extracting {}.'.format(tar_file))
    file_list = subprocess.check_output(tar_command)
    logger.info(file_list)
    text = 'Finished restoring {}. Please restart Splunk.'.format(tar_file)
    return text
    
    
def remove_app_dirs(logger, app_files):
    try:       
        for folder in app_files:
            logger.info("Removing {}".format(folder))
            path = "{}/{}".format(app_path, folder)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        text = 'Finished removing app directories.'
        logger.info(text)
        return text
    except:
        text = "All app files were already removed moving to extract files."     
        return text   

def remove_etc_dirs(logger, etc_files):
    for dir in etc_files:
        logger.info("Removing {}".format(dir))
        path = "{}/{}".format(etc_path, dir)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    text = 'Finished removing directories from etc directories.'
    logger.info(text)
    return text
            
def run_restore(logger):
    # logger = setup_logger()
    etc_app_dirs(logger)
    
    os.chdir(splunk_home)
    tar_file_len = len(glob('splunk_backup*.tgz'))
    if tar_file_len > 1:
        text = 'Number of tar files is greater than one. Please remove the tar files that you don\'t wish to use.'
        logger.error(text)
    else:
        try:
            text = "Removing KvStore."
            logger.info(text)
            shutil.rmtree(kvstore_loc)
        except:
            text = "Failed to remove KVStore."
            logger.info(text)
            return text
        try:
            text = remove_app_dirs(logger, app_files)
            logger.info(text)
        except:
            text = 'Failed to remove app directories.'
            logger.error(text)
            return text
        try:
            text = remove_etc_dirs(logger, etc_files)
            logger.info(text)
        except:
            text = "Could not remove etc dirs."
            logger.error(text)
            return text
        try:
            text = remove_file_dirs(logger)
            logger.info(text)
        except:
            text = 'Could not remove main directories.'
            logger.error(text)
            return text            
        try:
            text = run_untar(logger)
            logger.info(text)
        except Exception as e:
            text = "The untar command failed to run. {}".format(e)
            logger.error(text)
            return text
        return text

# if __name__ == "__main__":
#     run_restore()
