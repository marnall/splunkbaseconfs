# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
A script that allows for the following:
    - Move objects from kvstore collection(s) to a file on disk
    - Restore objects from file on disk to kvstore:
        - by replacing existing kv store data
        - by appending to existing kv store data if possible
"""
import getpass
import json
import logging
import os
import sys
from optparse import OptionParser, OptionGroup

import splunk.rest as rest
from splunk import AuthenticationFailed, auth
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
import itsi_py3

from ITOA.itoa_common import is_valid_str
from ITOA.setup_logging import getLogger, setup_logging
from ITOA.storage.itoa_storage import ITOAStorage
from ITOA.version_check import VersionCheck
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.objects.itsi_service import ItsiService
from itsi.upgrade.timezones import migrate_timezones
from migration.migration import MigrationBaseMethod
from migration.supervisor import MigrationSupervisor

KVSTORE_JSON_SPLUNKD_HOST_PATH = 'https://localhost'
KVSTORE_JSON_SPLUNKD_PORT = '8089'
KVSTORE_JSON_SPLUNKD_USER = 'admin'
KVSTORE_JSON_BACKUP_BASEDIR = os.path.join(os.getcwd(), 'backup')
DEFAULT_DUPNAME_TAG = '_dup_from_restore'

ITSI_VERSION_2_0 = '2.0.0'
ITSI_VERSION_2_3 = '2.3.0'

MAX_RETRIES = 3

INVALID_RESPONSE_MSG = 'Must enter the correct response value or contact your Splunk administrator.'


def is_valid_response(var):
    is_valid_response = False
    valid_response = ['', 'y', 'n', 'yes', 'no']
    if isinstance(var, itsi_py3.string_type):
        if var.strip().lower() in valid_response:
            is_valid_response = True
    return is_valid_response


def is_true(var):
    """
    utility method to check if value of var implies true
    @param var: the variable under question
    @param type: string, bool, number types
    @return False by default, True if it implies as such
    """
    is_true = False
    if isinstance(var, itsi_py3.string_type):
        # user could enter true/yes/y or merely press the enter key which is an empty string
        if var.strip().lower() == 'true' or var.strip().lower().startswith('yes') or len(
                var.strip()) == 0 or var.strip().lower() == 'y':
            is_true = True
    elif isinstance(var, bool):
        is_true = var
    elif isinstance(var, (int, float, complex)):
        if int(var) > 0:
            is_true = True
    return is_true


def get_username_password():
    """
    An interactive method that prompts a user for username and password.
    @return username
    @return password
    @rtype str
    """
    if options.username is None:
        options.username = input('>> Enter splunk username or press enter to use "{}" > '
                                 .format(KVSTORE_JSON_SPLUNKD_USER))
        if len(options.username.strip()) == 0:
            options.username = KVSTORE_JSON_SPLUNKD_USER
    if options.password is None:
        options.password = getpass.getpass(prompt='>> Enter splunk password for "{}" > '.format(options.username))
    return options.username, options.password


def is_invalid_string(str_obj):
    """
    Method that checks and sees if var is a valid string
    Invalid string is one which is of None type or an empty str
    @param str_obj string object to check
    @param type str

    @return True if invalid option; False if valid
    """
    if str_obj is None or len(str_obj.strip()) == 0:
        return True
    return False


def do_interactive():
    """
    Method that does interactive data collection
    @return collected_data
        {
        'username': <str>,
        'password':<str>,
        'file_path':<str>,
        'import_data':<bool>,
        'br_version':<str>,
        'persist_data':'<bool>,
        'dupname_tag':'<str>'
        }
    @rtype dict
    """
    # get the splunkd port
    if options.splunkdport is not None:
        try:
            int(options.splunkdport)
        except ValueError:
            options.splunkdport = None
            print('Invalid port number. Try again.')
    retries = MAX_RETRIES
    while not options.splunkdport and retries:
        entered = input(
            '>> Enter the splunkd port number OR press the enter key to use [{}] > '.format(KVSTORE_JSON_SPLUNKD_PORT))
        if len(entered.strip()) == 0:
            options.splunkdport = KVSTORE_JSON_SPLUNKD_PORT
        else:
            try:
                int(entered)
                options.splunkdport = entered
            except ValueError:
                print('Invalid port number. Try again.')
                retries -= 1
    if not retries:
        print('You have reached the maximum number of retries. Run the script again.')
        sys.exit(1)

    # get the username and password
    sessionkey = None
    retries = MAX_RETRIES
    hostpath = KVSTORE_JSON_SPLUNKD_HOST_PATH + ':' + options.splunkdport
    while not sessionkey and retries:
        username, password = get_username_password()
        try:
            sessionkey = auth.getSessionKey(username, password, hostpath)
        except Exception as e:
            print('Encountered an error when logging in - ' + str(e))
            print('Try again.')
            retries -= 1
            options.password = None
    if retries == 0:
        print(
            'Try running the command again with proper credentials or contact your Splunk administrator for permissions.')
        sys.exit(1)

    if options.mode == '3' or options.mode == '4':
        return sessionkey

    if options.mode == '5':
        skip_local_failure = input('>> Do you wish to skip local failures? [y|n|enter]: > ')
        if is_valid_response(skip_local_failure):
            options.skip_local_failure = is_true(skip_local_failure)
        return sessionkey

    # get file_path
    if options.file_path is None:
        msg = (
            '>> Enter full path of backup or restore directory. Note: It could be a file, if you are importing from ITSI 1.2.0'
            '\n Press enter to use your current working directory {} > ').format(KVSTORE_JSON_BACKUP_BASEDIR)
        options.file_path = input(msg)
        if is_true(options.file_path):
            options.file_path = KVSTORE_JSON_BACKUP_BASEDIR
        else:
            print('You entered "{}" for backup/restore. Proceeding.'.format(options.file_path))

    backup_data_option_retries = MAX_RETRIES
    while backup_data_option_retries:
        # check if user wants to import data from disk to kv store
        backup_data_from_kv = input('>> Do you wish to back up data from KV Store OR restore to KV store.'
                                    '\n Press [y|yes|enter] to backup, [n|no] to restore? > ')
        include_conf_files = input('>> Do you wish to include .conf files? [y|n|enter]: > ')
        if is_valid_response(include_conf_files):
            options.conf_file = is_true(include_conf_files)
        else:
            print(' Must enter y or n as your answer.')
            break
        if is_valid_response(backup_data_from_kv):
            if is_true(backup_data_from_kv):
                options.import_data = False
                # set the br_version for backups to the current app version
                options.br_version = ITOAInterfaceUtils.get_app_version(sessionkey, 'itsi', 'nobody')
                print('You have indicated backup of data from current ITSI version {}. Proceeding.'.format(
                    options.br_version))
            else:
                options.import_data = True
                print('You would like to restore data from disk to KV Store. Proceeding.')
                # check if user would like to do a partial restore
                partial_restore_option_retries = MAX_RETRIES
                while partial_restore_option_retries:
                    partial_restore = input('>> Do you wish to perform a partial restore? [y|n|enter]: > ')
                    if is_valid_response(partial_restore):
                        if is_true(partial_restore):
                            persist_data_option_retries = MAX_RETRIES
                            while persist_data_option_retries:
                                persistent_mode = input('>> Partial restore will only run in persistent mode.\n '
                                                        'Do you wish to continue with the partial restore in persistent mode? [y|n|enter]: > ')
                                if is_valid_response(persistent_mode):
                                    if is_true(persistent_mode):
                                        options.persist_data = True
                                        rename_dup = input(
                                            '>> Do you wish to rename any duplicated entries as part of the restore process?\n'
                                            'You may need to resolve any dependencies issues from the UI after the restore. [y|n|enter]: > ')
                                        if (is_true(rename_dup)):
                                            dupname_tag = input(
                                                '>> Enter a tag to be appended to the duplicates entries.\n'
                                                'By default, the tag is _dup_from_restore_<epoch_timestamp>.\n'
                                                '<epoch_timestamp> is auto-generated by the system.\n'
                                                'Ex: service_1 --> service_1_dup_from_restore_1234567 > ')
                                            if (len(dupname_tag.strip()) == 0):
                                                dupname_tag = DEFAULT_DUPNAME_TAG

                                            options.dupname_tag = dupname_tag
                                        else:
                                            print(
                                                ' Duplicated names or dependencies will not resolve automatically. Restore may fail.')
                                    else:
                                        print(
                                            ' Partial restore in non-persistent mode will erase all data in KV store. Exiting.')
                                        sys.exit(1)
                                    break
                                else:
                                    print(' Must enter y or n as your answer.')
                                    persist_data_option_retries -= 1
                            if persist_data_option_retries == 0:
                                print(INVALID_RESPONSE_MSG)
                                sys.exit(1)
                        else:
                            # check if user wants to persist existing data in kv store in the midst of backup
                            persist_data_option_retries = MAX_RETRIES
                            while persist_data_option_retries:
                                persist_data_in_kv = input(
                                    '>> Do you wish to persist the existing data in KV Store during the import [y|n|enter]: > ')
                                if is_valid_response(persist_data_in_kv):
                                    if is_true(persist_data_in_kv):
                                        options.persist_data = True

                                        rename_dup = input(
                                            '>> Do you wish to rename any duplicated entries as part of the restore process?\n'
                                            'You may need to resolve any dependencies issues from the UI after the restore. [y|n|enter]: > ')
                                        if (is_true(rename_dup)):
                                            dupname_tag = input(
                                                '>> Enter a tag to be appended to the duplicates entries.\n'
                                                'By default, the tag is _dup_from_restore_<epoch_timestamp>.\n'
                                                '<epoch_timestamp> is auto-generated by the system.\n'
                                                'Ex: service_1 --> service_1_dup_from_restore_1234567 > ')
                                            if (len(dupname_tag.strip()) == 0):
                                                dupname_tag = DEFAULT_DUPNAME_TAG

                                            options.dupname_tag = dupname_tag
                                        else:
                                            print(
                                                ' Duplicated names or dependencies will not resolve automatically. Restore may fail.')
                                    else:
                                        options.persist_data = False
                                    break
                                else:
                                    print(' Must enter y or n as your answer.')
                                    persist_data_option_retries -= 1
                            if persist_data_option_retries == 0:
                                print(INVALID_RESPONSE_MSG)
                                sys.exit(1)
                        break
                    else:
                        print(' Must enter y or n as your answer.')
                        partial_restore_option_retries -= 1
                if partial_restore_option_retries == 0:
                    print(INVALID_RESPONSE_MSG)
                    sys.exit(1)
            break
        else:
            print(' Must enter y or n as your answer.')
            backup_data_option_retries -= 1
        if backup_data_option_retries == 0:
            print(INVALID_RESPONSE_MSG)
            sys.exit(1)
    return sessionkey


def do_interactive_post_init(kvStoreBackupRestore_worker):
    # Initializing KVStoreBackupRestore extracts information from backup folder like app version info of the backup
    # So do version check/prompting for app version of backup after init
    if options.import_data:
        version_validated = False
        options.br_version = kvStoreBackupRestore_worker.get_app_version_of_backup()
        while not version_validated:
            if options.br_version is None:
                if options.no_prompt:
                    print('Could not determine ITSI version for the backup data in the path specified. Must '
                          'specify the ITSI version for the backup data.')
                    sys.exit(1)
                else:
                    msg = ('>> The ITSI version on which the backup data was collected is unavailable. '
                           'Enter the ITSI version on which the backup data was collected, to restore to. '
                           'Ex: \'2.3.0\', \'2.3.1\', \'2.4.0\' >')
                    options.br_version = input(msg)
            else:
                print('ITSI version on which the backup data was collected is indicated to '
                      'be {0}. Restore will treat the backup data as being from this ITSI version.'.format(
                          options.br_version))
            if len(options.br_version.strip()) != 0 and VersionCheck.validate_version(options.br_version):
                version_validated = True
                kvStoreBackupRestore_worker.set_app_version_of_backup(options.br_version)
                if VersionCheck.compare(options.br_version, ITSI_VERSION_2_3) < 0:
                    print('Restoring from backup file with version belows 2.3.0 is not supported, existing...')
                    sys.exit(1)
            else:
                options.br_version = None
                print('Invalid version found. Must enter a valid version string.')


def do_kpi_operations(splunkd_session_key):
    """
    Performs KPI CRUD operations for mode 2 of the tool

    @param splunkd_session_key: Session key for Splunkd operations

    @return: None, output is written to output.json in argument for file_path
    """
    owner = 'nobody'

    # Validate group options
    count_options = \
        (1 if options.get_objects else 0) + \
        (1 if options.create_objects else 0) + \
        (1 if options.update_objects else 0) + \
        (1 if options.delete_objects else 0)
    if count_options != 1:
        raise Exception('Pick exactly one service KPI operation among: get, create, update and delete.')

    if not is_valid_str(options.file_path):
        raise Exception(('Specified file path is invalid. It must be a directory containing input.json '
                         'with the input to the specified service KPI operation. On exit, it will contain output.json '
                         'with the results.'))

    input_file = os.path.join(options.file_path, 'input.json')
    output_file = os.path.join(options.file_path, 'output.json')
    if not os.path.isfile(input_file):
        raise Exception(('Input not specified for the service KPI operation. '
                         'Must provide a valid directory path containing input.json.'))

    with open(input_file, 'r') as input_file_handle:
        input_json = json.load(input_file_handle)

    service_object = ItsiService(session_key=splunkd_session_key, current_user_name=owner)
    if options.get_objects:
        output_json = service_object.fetch_kpis_via_script(owner, input_json)
    elif options.create_objects or options.update_objects:
        output_json = service_object.change_kpis_via_script(owner, input_json)
    elif options.delete_objects:
        is_delete_kpis = input('>> You have requested to delete KPIs. Are you sure you want to delete KPIs? [y|n]: > ')
        if is_true(is_delete_kpis):
            output_json = service_object.delete_kpis_via_script(owner, input_json)
        else:
            print('Operation cancelled')
            return
    else:
        raise Exception('No service KPI operation specified.')

    try:
        with open(output_file, 'w') as output_file_handle:
            output_file_handle.writelines(json.dumps(output_json, sort_keys=True, indent=4))
            print('Results have been written to ' + output_file)
    except Exception:
        print('Results could not be written output to ' + output_file)
        print('\nDumping results out to screen:\n' + json.dumps(output_json))


def do_timezone_offset_operations(splunkd_session_key):
    """
    Performs timezone offset operations for mode 3 of the tool

    @param splunkd_session_key: Session key for Splunkd operations

    @return: None, output is written to stdout
    """
    # determine which timezone migration tool to use, based on app version
    # for itsi version 2.6.0 and beyond, the timezone migrator for 2.6.0 will be used.
    migrate_timezones(splunkd_session_key, options)


def do_regenerate_saved_search_schedule(splunkd_session_key):
    """
    Performs a reset of the saved search scheduling for ALL service KPIs
    Achieves this by creating a copy of the list of services

    @param splunkd_session_key: Session key for splunkd operations
    @return: None, output written to stdout
    """
    service_list = []
    base_search_list = []
    print("Retrieving KPIs to reset their saved search scheduling")
    migration_method = MigrationBaseMethod(splunkd_session_key)
    service_iter = migration_method.migration_get("service")
    for service in service_iter:
        service_list.append(service)
    migration_method.migration_save("service", service_list)
    base_search_iter = migration_method.migration_get("kpi_base_search")
    for kpi_base_search in base_search_iter:
        base_search_list.append(kpi_base_search)
    migration_method.migration_save("kpi_base_search", base_search_list)
    print("Saving updated KPI scheduling")
    ret = migration_method.migration_bulk_save_to_kvstore(validation=True, dupname_tag=None)
    if ret:
        print("Done.")
    else:
        print("Error occurred when saving updated schedules. See itsi_kvstore_to_json.log for details.")


############
# Initialize parser
############
parser = OptionParser()
parser.add_option(
    '-s',
    '--splunkdport',
    dest='splunkdport',
    default=None,
    help='splunkd port. If no option is provided, we will default to "{}"'.format(KVSTORE_JSON_SPLUNKD_PORT))
parser.add_option(
    '-u',
    '--username',
    dest='username',
    help='Splunk username')
parser.add_option(
    '-p',
    '--password',
    dest='password',
    help='Splunk password')
parser.add_option(
    '-n',
    '--no-prompt',
    dest='no_prompt',
    action='store_true',
    default=False,
    help='Use this option when you want to disable the prompt version of this script')
parser.add_option(
    '-v',
    '--verbose',
    dest='verbose',
    action='store_true',
    default=False,
    help='Use this option for verbose logging')
parser.add_option(
    '-f',
    '--filepath',
    dest='file_path',
    default=None,
    help='The full path of a directory. Usage depends on mode.\n'
         'When importing backed up data of version 1.2.0, this could be a file or a set of files.\n'
         'When working with service KPIs, this is a directory containing input.json on entry '
         'and output.json on exit.'
)
parser.add_option(
    '-m',
    '--mode',
    dest='mode',
    default='1',
    help='Specify the mode of operation - what kind of operations to perform. Mode is set to:\n'
         '\t1 - for backup/restore operations.\n'
         '\t2 - for service KPI operations.\n'
         '\t3 - for adjusting timezone offsets on objects.'
         '\t4 - for regenerate KPI search schedules.'
         '\t5 - for migration.')
backup_restore_group = OptionGroup(
    parser,
    'Backup and restore operations. This is mode 1.',
    'Use this option when you want to perform backup/restore operations.'
)
backup_restore_group.add_option(
    '-i',
    '--importData',
    dest='import_data',
    action='store_true',
    default=False,
    help=('Use this option when you want to upload data to the KV Store.'
          '\nWhen importing data from version 1.2.0, you can use filepath as wildcard to upload data from more than one file.'
          '\nHowever, filepath must be within quotes if it is being used as a wildcard'))
backup_restore_group.add_option(
    '-d',
    '--persist-data',
    dest='persist_data',
    action='store_true',
    default=False,
    help=('Use this option when you want to persist existing configuration in KV Store during import.'
          '\nNOTE: Applicable only if importData option is used'))
backup_restore_group.add_option(
    '-y',
    '--dry-run',
    dest='dry_run',
    action='store_true',
    default=False,
    help='Use this option when you want only to list objects for import or backup.')
backup_restore_group.add_option(
    '-a',
    '--conf-file',
    dest='conf_file',
    action='store_true',
    default=False,
    help='Use this option when you want to back up .conf files.')
backup_restore_group.add_option(
    '-b',
    '--base-version',
    dest='br_version',
    default=None,
    help='The original ITSI application version user intend to backup/restore from.')
backup_restore_group.add_option(
    '-e',
    '--dupname-tag',
    dest='dupname_tag',
    default=None,
    help='Automatically rename all the duplicated service or entity names from restoring with a tag.'
         '\nIf this option is not set, the restoring will halt if duplicate names are detected.'
         '\nThe default tag is: _dup_from_restore_<epoch_timestamp>')
parser.add_option_group(backup_restore_group)
kpis_group = OptionGroup(
    parser,
    'Service KPI operations. This is mode 2.',
    'Use this option when you want to get/create/update/delete KPIs for existing services.'
)
kpis_group.add_option(
    '-g',
    '--get',
    dest='get_objects',
    action='store_true',
    default=False,
    help='For input, specify a list of service keys with the keys of KPIs to retrieve. '
         'Expected format: [{_key: <service key>, kpis: [{_key: <KPI key>}]]. '
         'Specify [] to get all KPIs from all services. '
         'Specify [{_key: <service key>, kpis: []] to get all KPIs from a service. '
         'Assumes input is available in file_path/input.json'
)
kpis_group.add_option(
    '-c',
    '--create',
    dest='create_objects',
    action='store_true',
    default=False,
    help='For input, specify a non-empty list of service keys with their KPIs list. '
         'Expected format: [{_key: <service key>, kpis: [{_key: <KPI key>, <rest of KPI structure>}]]. '
         'Note that only existing services could be updated with new KPIs only with this option. '
         'Assumes input is available in file_path/input.json'
)
kpis_group.add_option(
    '-t',
    '--update',
    dest='update_objects',
    action='store_true',
    default=False,
    help='For input, specify a non-empty list of service keys with their KPIs list. '
         'Expected format: [{_key: <service key>, kpis: [{_key: <KPI key>, <rest of KPI structure>}]]. '
         'Note that only existing services and existing KPIs could be updated using this option. '
         'Assumes input is available in file_path/input.json'
)
kpis_group.add_option(
    '-r',
    '--delete',
    dest='delete_objects',
    action='store_true',
    default=False,
    help='For input, specify a list of service keys with the keys for the KPIs to delete. '
         'Expected format: [{_key: <service key>, kpis: [{_key: <KPI key>}]]. '
         'Assumes input is available in file_path/input.json'
)
parser.add_option_group(kpis_group)
timezone_offsets_group = OptionGroup(
    parser,
    'Timezone offset operations. This is mode 3.',
    'Use this option when you want to adjust timezone settings for time sensitive fields on object configuration.'
)
timezone_offsets_group.add_option(
    '-q',
    '--is_get',
    dest='is_get',
    default=False,
    help='For input, specify if you are trying to read objects or update their timezone offsets.'
)
timezone_offsets_group.add_option(
    '-o',
    '--object_type',
    dest='object_type',
    default=None,
    help='For input, specify a valid object type that contains time sensitive configuration. This option will '
         'apply offset to all objects on this type unless scoped to a specific object using object_key parameter. '
         'Supported object types are:\n'
         '"maintenance_calendar" for maintenance windows,\n'
         '"service" for Services/KPIs (threshold policies),\n'
         '"kpi_threshold_template" for KPI threshold template policies\n'
)
timezone_offsets_group.add_option(
    '-k',
    '--object_title',
    dest='object_title',
    default=None,
    help='For input, specify an optional object title of object type that contains time sensitive configuration. Using '
         'this option will cause the offset change to only apply to that object.'
)
timezone_offsets_group.add_option(
    '-z',
    '--offset_seconds',
    dest='offset_in_sec',
    default=None,
    help='For input, specify the offset to apply in seconds as a positive or negative number. '
         'This offset should be the number of seconds that you want to add or subtract from the current value.'
)
parser.add_option_group(timezone_offsets_group)

############
# parse input arguments
############
(options, args) = parser.parse_args()

############
# decide on mode of operation
############
collected_data = {}
print('\n>>>> Note: We will only be using localhost for all operations. <<<<\n')

print('Mode specified is: {0}. Options for other modes would be ignored.\n'.format(options.mode))

operation_mode = options.mode.strip()
if options.no_prompt:
    if options.splunkdport is None:
        options.splunkdport = KVSTORE_JSON_SPLUNKD_PORT
    else:
        try:
            int(options.splunkdport)
        except ValueError:
            raise ValueError('-s(--splunkdport) must be a valid splunkd port number')

    if is_invalid_string(options.username) or is_invalid_string(options.password) \
            or is_invalid_string(options.file_path):
        print('Username, password or file path have not been specified.')
        parser.print_help()
        sys.exit(0)
    try:
        hostPath = KVSTORE_JSON_SPLUNKD_HOST_PATH + ':' + options.splunkdport
        session_key = auth.getSessionKey(options.username, options.password, hostPath=hostPath)
    except AuthenticationFailed:
        print('Having trouble trying to log you in...')
        print(
            'Try running the command again with proper credentials or contact your Splunk administrator for permissions.')
        sys.exit(1)
else:
    if operation_mode == '2':
        print('Interactive mode not supported for selected mode of operation. '
              'Try again without interactive mode.')
        sys.exit(1)
    print('#########################')
    print('Starting Interactive mode.')
    print('#########################\n')
    session_key = do_interactive()

logger = getLogger(logger_name='itsi.kvstore.operations')
try:
    # Setup logging
    if options.dry_run:
        if operation_mode != '1':
            print('Dry run not supported for selected mode of operation. '
                  'Try again without dry run selected.')
            sys.exit(1)
        print('>>>> This is a dry run. No actual backup or importing will happen, only a list of objects will be '
              'displayed. To perform the actual operation, re-run again without the flag for dry run ...')
    else:
        # Setup child logger for this python module only, so console logs only works for current module
        logger = setup_logging(logger=logger, is_console_header=True)

    if options.verbose:
        logger.setLevel(logging.DEBUG)
    # KV store takes longer to initialized on under resourced machine
    storage = ITOAStorage()
    if not storage.wait_for_storage_init(session_key):
        raise Exception(
            'KV store has not been initialized yet. Make sure Splunk is running. If it is, check for startup errors.')

    if operation_mode == '1':
        # We have to import on demand here to setup logger currently
        from itsi.upgrade.kvstore_backup_restore import KVStoreBackupRestore

        worker = KVStoreBackupRestore(
            session_key,
            options.file_path,
            not options.import_data,
            options.persist_data,
            options.br_version,
            options.dupname_tag,
            options.verbose,
            logger_instance=logger,
            is_dry_run=options.dry_run,
            include_conf_files=options.conf_file
        )

        do_interactive_post_init(worker)

        worker.execute()
    elif operation_mode == '2':
        do_kpi_operations(splunkd_session_key=session_key)
    elif operation_mode == '3':
        do_timezone_offset_operations(splunkd_session_key=session_key)
    elif operation_mode == '4':
        do_regenerate_saved_search_schedule(splunkd_session_key=session_key)
    elif operation_mode == '5':
        migration_checker = MigrationSupervisor(session_key)
        if not migration_checker.is_migration_running():
            data = {'skip_local_failure': options.skip_local_failure}
            rsp, content = rest.simpleRequest(
                '/servicesNS/nobody/SA-ITOA/storage/collections/data/itsi_migration_queue', sessionKey=session_key,
                raiseAllErrors=False, jsonargs=json.dumps(data), method='POST')
            if rsp.status != 200 and rsp.status != 201:
                print('Failed to dispatch migration. Please try again.')
                sys.exit(1)
            print('Successfully dispatched migration. See the logs for details. '
                  'Do not restart Splunk until the migration is completed.')
        else:
            print('Failed to start migration because a migration is already in progress.')
            sys.exit(1)
    else:
        print('Incorrect mode of operation specified. Fix the mode and try again.')

except Exception as e:
    logger.exception('Failed. Try running the script again. Error:%s', e.args[0])
    if options.dry_run:
        print(e)
        print('Refer %s for more information' % logger.getLogFilePath())
    sys.exit(1)
sys.exit(0)
