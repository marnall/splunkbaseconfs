import os

splunk_home = os.getenv('SPLUNK_HOME')
base_path = splunk_home.split('/')[1]
etc_path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc')
app_path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps')
var_lib_splunk_path = os.path.join(splunk_home, 'var', 'lib', 'splunk')
splunk_upgrader_path = os.path.join(app_path, 'splunk_upgrader')
files = sorted(os.listdir(splunk_home))
app_files = sorted(os.listdir(app_path))
etc_files = sorted(os.listdir(etc_path))
var_files = sorted(os.listdir(var_lib_splunk_path))
full_list = []

def file_list(logger):
    os.chdir(splunk_home)
    cur_dir = os.getcwd()
    logger.info("Building the file list for the backup process.")
    files_list = []
    for file in files:
        if file == "var":
            logger.info("Skipping: {}".format(file))
        elif file == ".DS_STORE":
            logger.info("Skipping: {}".format(file))
        elif file.endswith(".tgz") or file.endswith(".gz"):
            logger.info("Skipping: {}".format(file))
        else:
            files_list.append(file)

    full_vars = []
    for file in var_files:
        if file.startswith('kvstore'):
            full_vars.append('var/lib/splunk/{}'.format(file))

    
    full_list = [ *files_list, *full_vars]
    logger.info("The full list of files that will be backed up is: {}".format(full_list))

    return full_list
    
