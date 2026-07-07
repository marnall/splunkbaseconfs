#!/usr/bin/env python
# coding=utf-8

import os, sys, time
import json, csv

from types import SimpleNamespace
import shutil

app_basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
logger_filepath = os.path.abspath(os.path.join(app_basepath, "..", "..", "..", "var", "log", "splunk", "kaggle_app.log"))
isdebug = 0

sys.path.append(os.path.join(app_basepath, "bin"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

import splunk.Intersplunk

import logging
logger = logging.getLogger()

# make sure that at least api.authenticate() in bin/kaggle/__init__.py is commented out
# as we are using environment-method and first have to set the env-vars
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()

@Configuration()
class KaggleApiCustomSearchCommand(GeneratingCommand):

    valid_arguments = {
      'competitions': {
        'list': {
          'group': ['general', 'entered', 'inClass'],
          'category': ['all', 'featured', 'research', 'recruitment', 'gettingStarted', 'masters', 'playground'],
          'sort_by': ['grouped', 'prize', 'earliestDeadline', 'latestDeadline', 'numberOfTeams', 'recentlyCreated'],
          'page': [],
          'search': []
        },
        'files': {},
        'download': {
          'file': []
        },
        'leaderboard': {}
      },
      'datasets': {
        'list': {
          'sort_by': ['hottest', 'votes', 'updated', 'active'],
          'size': ['all', 'small', 'medium', 'large'],
          'file_type': ['csv'],
          'license_name': ['all', 'cc', 'gpl', 'odb', 'other'],
          'tag_ids': [],
          'search': [],
          'user': [],
          'page': []
        },
        'files': {},
        'download': {
          'file': []
        },
        'metadata': {}
      },
      'kernels': {
        'list': {
          'page': [],
          'page_size': [],
          'search': [],
          'parent': [],
          'competition': [],
          'dataset': [],
          'user': [],
          'language': ['all', 'python', 'r', 'sqlite', 'julia'],
          'kernel_type': ['all', 'script', 'notebook'],
          'output_type': ['all', 'visualizations', 'data'],
          'sort_by': ['hotness', 'commentCount', 'dateCreated', 'dateRun', 'relevance', 'scoreAscending', 'scoreDescending', 'viewCount', 'voteCount']
        },
        'pull': {},
        'output': {},
        'status': {}
      }
    }

    def is_valid_args(self, args):

        errors = []

        if (len(args) < 3):
            errors.append("No command or function given. Usage e.g.: kaggle datasets list")
        else:
            if args[1] not in self.valid_arguments:
                errors.append("Invalid command '" + args[1] + "' given. Choose one of " + str(list(self.valid_arguments.keys())))
                pass
            elif args[2] not in self.valid_arguments[args[1]]:
                errors.append("Invalid function '" + args[2] + "' for command '" + args[1] + "' given. Choose one of " + str(list(self.valid_arguments[args[1]].keys())))

        if len(errors) > 0:
            for error in errors:
                logger.error(error)
                return False
        else:
            return True


    def is_valid_kwargs(self, args, kwargs):

        curr_valid_arguments = self.valid_arguments[args[1]][args[2]]

        errors = []
        for curr_arg_name, curr_arg_val in kwargs.items():
            if (curr_arg_name not in curr_valid_arguments):
                errors.append("Invalid argument '" + curr_arg_name + "' given. Choose one of " + str(list(curr_valid_arguments.keys())))
                continue
            if (len(curr_valid_arguments[curr_arg_name]) > 0 and curr_arg_val not in curr_valid_arguments[curr_arg_name]):
                errors.append("Invalid value '" + curr_arg_val + "' for argument '" + curr_arg_name + "' given. Choose one of " + str(curr_valid_arguments[curr_arg_name]))

        if len(errors) > 0:
            for error in errors:
                logger.error(error)
                return False
        else:
            return True

    def check_arg3_given(self, args, name):
        if len(args) < 4:
            logger.error("No %s given.", name)
            return False
        return True

    def is_valid_competition(self, args):
        return self.check_arg3_given(args, "competition")

    def is_valid_dataset(self, args):
        if not self.check_arg3_given(args, "dataset"):
            return False
        else:
            dataset_list = args[3].split("/")
            if len(dataset_list) != 2:
                logger.error("No valid dataset structure.")
                return False
            else:
                return True

    def is_valid_kernel(self, args):
        return self.check_arg3_given(args, "kernel")



    def setup_logging(self):
        if isdebug:
            logger.setLevel(logging.DEBUG)
            logfile = logging.StreamHandler(open(logger_filepath, "a"))
            logfile.setLevel(logging.DEBUG)
            logfile.setFormatter(logging.Formatter('%(asctime)s [%(process)06d] %(levelname)-8s %(name)s:  %(message)s'))
            logger.addHandler(logfile)
        else:
            logger.setLevel(logging.WARNING)

    def write_error(self, exc_info, extra_info):
        exc_type, exc_obj, exc_tb = exc_info
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error("%s; Line-Number: %s; Type: %s; Filename: %s; Info: %s" % (extra_info, exc_tb.tb_lineno, exc_type, fname, exc_info[1]))


    def get_kaggle_api_key(self, key_realm, key_username):
        try:
            secrets = self.service.storage_passwords
            return next(secret for secret in secrets if (secret.realm == key_realm and secret.username == key_username)).clear_password
        except:
            self.write_error(sys.exc_info(), "Kaggle API Key ERROR.")
            return False


    def get_kaggle_api_username(self, username_conf, username_stanza, username_key):
        try:
            return self.service.confs[username_conf][username_stanza][username_key]
        except:
            self.write_error(sys.exc_info(), "Kaggle API Username ERROR.")
            return False

    def set_authentication_environment_variables(self, username, key):
        os.environ['KAGGLE_USERNAME'] = username
        os.environ['KAGGLE_KEY'] = key


    def parse_param_page(self, kwargs):
        pages = [1]
        try:
            if ('page' in kwargs):
                # list of pages, eg. page="[1,2,4]", page="1-3", page="2"
                if kwargs['page'].startswith("[") and  kwargs['page'].endswith("]"):
                    pages = kwargs['page'].strip('][').split(',')
                elif "-" in kwargs['page']:
                    pages_range = kwargs['page'].split("-")
                    pages = list(range(int(pages_range[0]), int(pages_range[1]) + 1))
                else:
                    pages = kwargs['page'].split(",")
        except:
            self.write_error(sys.exc_info(), "Error parsing param 'page'.")
        pages = [str(i) for i in pages]
        return pages


    def parse_kwargs_quotes(self, kwargs):
        params = ['page', 'page_size']
        for p in params:
            # strip quotation marks and blacks from page string
            if p in kwargs:
                kwargs[p] = kwargs[p].strip("\" ")
        return kwargs


    def handle_call_competitions(self, curr_function, args, kwargs):

        result_data = []
        kwargs = self.parse_kwargs_quotes(kwargs)

        # LIST function
        # https://github.com/Kaggle/kaggle-api#list-competitions
        # | kaggle competitions list
        # | kaggle competitions list group=<GROUP> category=<CATEGORY> sort_by=<SORT_BY> page=<PAGE> search=<SEARCH>
        #   * page can be either int, range or list. eg page=3, page=1-3, page=[1,3]
        if (curr_function == "list"):
            try:
                pages = self.parse_param_page(kwargs)
                for page in pages:
                    kwargs['page'] = page
                    result_data.extend(api.competitions_list_with_http_info(**kwargs)[0])
            except:
                self.write_error(sys.exc_info(), "")

        # FILES function
        # https://github.com/Kaggle/kaggle-api#list-competition-files
        # | kaggle competitions files <competition>
        elif (curr_function == "files"):
            if not self.is_valid_competition(args):
                return
            try:
                result_data = api.competitions_data_list_files_with_http_info(args[3])[0]
            except:
                self.write_error(sys.exc_info(), "")

        # DOWNLOAD function
        # https://github.com/Kaggle/kaggle-api#download-competition-files
        # | kaggle competitions download <competition>
        # | kaggle competitions download <competition> file=<FILE>
        elif (curr_function == "download"):
            if not self.is_valid_competition(args):
                return
            try:
                kwargs['force'] = True
                kwargs['path'] = os.path.join(app_basepath,"lookups")
                kwargs['quiet'] = True

                competition_files = []
                if 'file' in kwargs:
                    kwargs['file'] = kwargs['file'].strip('\"')
                    competition_files = [SimpleNamespace(**{'name': kwargs['file']})]
                    kwargs.pop('file', None)
                else:
                    competition_files = [x for x in api.competition_list_files(args[3]) if (x.name.endswith('.csv'))]

                if not competition_files:
                    logger.warning("There are no valid files (CSV) in the root of this competition. To download a specific file within a subfolder, use 'file=<<filepath>>' to explicitly download it.")

                downloaded_files = []
                for file in competition_files:
                    try:
                        file_downloaded = api.competition_download_file(args[3], file.name, **kwargs)
                        # large files seem to be downloaded as zip file -> unpack
                        if file_downloaded and os.path.isfile(os.path.join(kwargs['path'], file.name + '.zip')):
                            shutil.unpack_archive(os.path.join(kwargs['path'], file.name + '.zip'), kwargs['path'])
                            os.remove(os.path.join(kwargs['path'], file.name + '.zip'))
                        downloaded_files.append(file.name)
                    except:
                        self.write_error(sys.exc_info(), "Error in 'competitions download' trying to download files.")

                result_data = [{'downloaded_files': downloaded_files}]
            except:
                self.write_error(sys.exc_info(), "")

        # LEADERBOARD function
        # https://github.com/Kaggle/kaggle-api#get-competition-leaderboard
        # | kaggle competitions leaderboard <competition>
        elif (curr_function == "leaderboard"):
            if not self.is_valid_competition(args):
                return
            try:
                result_data = api.competition_view_leaderboard_with_http_info(args[3])[0]
            except:
                self.write_error(sys.exc_info(), "")
            if ('submissions' in result_data):
                result_data = result_data['submissions']

        # competition not found check
        if isinstance(result_data, str) and result_data.startswith('<!DOCTYPE html>'):
            result_data = [{'result': 'competition ' + args[3] + ' not found'}]

        return result_data


    def handle_call_datasets(self, curr_function, args, kwargs):

        result_data = []
        kwargs = self.parse_kwargs_quotes(kwargs)

        # LIST function
        # https://github.com/Kaggle/kaggle-api#list-datasets
        # | kaggle datasets list
        # | kaggle datasets list sort_by=<SORT_BY> size=<SIZE> file_type=<FILE_TYPE> license_name=<LICENSE_NAME> tag_ids=<TAG_IDS> search=<SEARCH> user=<USER> page=<PAGE>
        #   * page can be either int, range or list. eg page=3, page=1-3, page=[1,3]
        if (curr_function == "list"):
            try:
                pages = self.parse_param_page(kwargs)
                for page in pages:
                    kwargs['page'] = page
                    result_data.extend(api.datasets_list_with_http_info(**kwargs)[0])
            except:
                self.write_error(sys.exc_info(), "")

        # FILES function
        # https://github.com/Kaggle/kaggle-api#list-files-for-a-dataset
        # | kaggle datasets files <dataset>
        elif (curr_function == "files"):
            if not self.is_valid_dataset(args):
                return
            try:
                curr_dataset = args[3].split('/')
                result_data = api.datasets_list_files_with_http_info(*curr_dataset)[0]
                result_data = result_data['datasetFiles']
            except:
                self.write_error(sys.exc_info(), "")

        # DOWNLOAD function
        # https://github.com/Kaggle/kaggle-api#download-dataset-files
        # | kaggle datasets download <dataset>
        # | kaggle datasets download <dataset> file=<FILE_NAME>
        elif (curr_function == "download"):
            if not self.is_valid_dataset(args):
                return
            try:
                kwargs['force'] = True
                kwargs['path'] = os.path.join(app_basepath,"lookups")
                kwargs['quiet'] = True
                curr_dataset = args[3]

                dataset_files = []
                if 'file' in kwargs:
                    kwargs['file'] = kwargs['file'].strip('\"')
                    dataset_files = [SimpleNamespace(**{'name': kwargs['file']})]
                    kwargs.pop('file', None)
                else:
                    dataset_files = [x for x in api.dataset_list_files(curr_dataset).files if (x.fileType=='.csv')]

                if not dataset_files:
                    logger.warning("There are no valid files (CSV) in the root of this dataset. To download a specific file within a subfolder, use 'file=<<filepath>>' to explicitly download it.")

                downloaded_files = []
                for file in dataset_files:
                    try:
                        file_downloaded = api.dataset_download_file(curr_dataset, file.name, **kwargs)
                        # large files seem to be downloaded as zip file -> unpack
                        if file_downloaded and os.path.isfile(os.path.join(kwargs['path'], file.name + '.zip')):
                            shutil.unpack_archive(os.path.join(kwargs['path'], file.name + '.zip'), kwargs['path'])
                            os.remove(os.path.join(kwargs['path'], file.name + '.zip'))
                        downloaded_files.append(file.name)
                    except:
                        self.write_error(sys.exc_info(), "Error in 'datasets download' trying to download files.")

                result_data = [{'downloaded_files': downloaded_files}]
            except:
                self.write_error(sys.exc_info(), "")


        # METADATA function
        # https://github.com/Kaggle/kaggle-api#download-metadata-for-an-existing-dataset
        # | kaggle datasets metadata <dataset>
        if (curr_function == "metadata"):
            if not self.is_valid_dataset(args):
                return
            try:
                curr_dataset = args[3].split('/')
                result_data = api.metadata_get(*curr_dataset, **kwargs)
                result_data = [result_data['info']]
            except:
                self.write_error(sys.exc_info(), "")


        return result_data


    def handle_call_kernels(self, curr_function, args, kwargs):

        result_data = []
        kwargs = self.parse_kwargs_quotes(kwargs)

        # LIST function
        # https://github.com/Kaggle/kaggle-api#list-kernels
        # | kaggle kernels list
        # | kaggle kernels list page=<PAGE> page_size=<PAGE_SIZE> search=<SEARCH> parent=<PARENT> competition=<COMPETITION> dataset=<DATASET> user=<USER> language=<LANGUAGE> kernel_type=<KERNEL_TYPE> output_type=<OUTPUT_TYPE> sort_by=<SORT_BY>
        if (curr_function == "list"):
            try:
                if 'parent' in kwargs:
                    kwargs['parent_kernel'] = kwargs.pop('parent')
                pages = self.parse_param_page(kwargs)
                for page in pages:
                    kwargs['page'] = page
                    result_data.extend(api.kernels_list_with_http_info(**kwargs)[0])
            except:
                self.write_error(sys.exc_info(), "")

        # PULL function
        # https://github.com/Kaggle/kaggle-api#pull-a-kernel
        # | kaggle kernels pull <kernel>
        elif (curr_function == "pull"):
            if not self.is_valid_kernel(args):
                return
            try:
                kwargs['metadata'] = True
                kwargs['path'] = os.path.normpath(os.path.join(app_basepath, "appserver", "static", "downloaded_kernels", args[3]))
                kwargs['quiet'] = True
                effective_path = api.kernels_pull(args[3], **kwargs)
                result_data = [{'kernel': args[3], 'path': effective_path}]
            except:
                self.write_error(sys.exc_info(), "")

        # OUTPUT function
        # https://github.com/Kaggle/kaggle-api#retrieve-a-kernels-output
        # | kaggle kernels output <kernel>
        elif (curr_function == "output"):
            if not self.is_valid_kernel(args):
                return
            try:
                kwargs['force'] = True
                kwargs['path'] = os.path.normpath(os.path.join(app_basepath, "appserver", "static", "downloaded_kernels", args[3]))
                kwargs['quiet'] = True
                downloaded_file = api.kernels_output(args[3], **kwargs)
                result_data = [{'downloaded_file': downloaded_file}]
            except:
                self.write_error(sys.exc_info(), "")

        # STATUS function
        # https://github.com/Kaggle/kaggle-api#get-the-status-of-the-latest-kernel-run
        # | kaggle kernels status <kernel>
        elif (curr_function == "status"):
            if not self.is_valid_kernel(args):
                return
            try:
                status_response = api.kernels_status(args[3])
                result_data = [{'kernel': args[3], 'status': status_response}]
            except:
                self.write_error(sys.exc_info(), "")

        return result_data


    def generate(self):

        self.setup_logging()

        # import time
        # start_time = time.time()
        # logger.info("1--- %s seconds ---" % (time.time() - start_time))

        # logger.info(sys.path)
        # logger.info(app_basepath)

        key_realm = 'kaggle_app_realm'
        key_username = 'admin'
        username_conf = 'kaggle'
        username_stanza = 'api'
        username_key = 'username'

        curr_username = self.get_kaggle_api_username(username_conf, username_stanza, username_key)
        curr_key = self.get_kaggle_api_key(key_realm, key_username)

        if (curr_username and curr_key):
            self.set_authentication_environment_variables(
                curr_username,
                curr_key
            )
        else:
            logger.warning("Kaggle API authentication failed")
            sys.exit()


        api.authenticate()

        args, kwargs = splunk.Intersplunk.getKeywordsAndOptions()

        if not self.is_valid_args(args):
            logger.warning("args not valid")
            return

        if not self.is_valid_kwargs(args, kwargs):
            logger.warning("kwargs not valid")
            return

        if (args[1] == "competitions"):
            result_data = self.handle_call_competitions(args[2], args, kwargs)
        elif (args[1] == "datasets"):
            result_data = self.handle_call_datasets(args[2], args, kwargs)
        elif (args[1] == "kernels"):
            result_data = self.handle_call_kernels(args[2], args, kwargs)

        try:
            for i, entry in enumerate(result_data):
                event = {'_serial': str(i), '_time': time.time(), '_raw': str(entry) }
                for key, value in entry.items():
                    event[key] = value
                yield event
        except:
            logger.error("There was an error generating the events.")
            logger.error("result_data = %s", str(result_data))



dispatch(KaggleApiCustomSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
