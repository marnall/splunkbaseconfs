#!/usr/bin/env python
# coding=utf-8
#
import os, sys
import json
import requests
import csv
import tarfile
import random
import re
import time
from collections import OrderedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators
from s3_files import S3Files
from botocore.exceptions import ClientError
from kat_utils import *


@Configuration()
class KatDataset(EventingCommand):
    """
    The katdataset command sends data to the Edge Conductor for training.

    Example:

    ``| inputlookup input_data.csv | head 4000 | katdataset train_data="train_data.csv"``

    Returns records having inference complete.
    """
    lookup_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'mellerikat-for-splunk', 'lookups')
    upload_tmp_path = os.path.join(lookup_path, "_tmp")
    input_file_name = Option(doc='''**Syntax:** **file_name=***<train_data.csv>*''', default='input_data.csv', require=False)
    S3_path = Option(doc='''**Syntax:** **S3_path=***</dataset/train/input_data.csv>*''', require=True)
    model_name = Option(doc='''**Syntax:** **model_name=***<model_name>*''', default='default', require=False)
    profile_name = Option(require=False, default=None)


    def get_mellerikat_conf(self, model=None):
        """Get mellerikat config from Splunk config file."""
        if (model is None):
            mellerikat_session = "default"
        else:
            mellerikat_session = "mellerikat:" + model
        return getMellerikatConf(mellerikat_session)

    def transform(self, records):
        katinfo = self.get_mellerikat_conf()
        s3files = S3Files(katinfo['profile_name'])
        file_name = get_file_name(self.S3_path)
        input_data = []
        
        if self.S3_path.startswith("/"):
            self.S3_path = self.S3_path.lstrip("/")
            
        self.logger.error('[MfS]')
        self.logger.error(self.profile_name)
        self.logger.error(self.S3_path)
        self.logger.error(file_name)
        self.logger.error(self.model_name)
        self.logger.error(katinfo)

        for record in records:
            input_data.append(record)

        keys = input_data[0].keys()

        results_message = dict()

        if(is_csv_file_name(file_name)):
            check_if_exists_tmp(self.upload_tmp_path)
            # 데이터를 lookup 경로에 저장하기.
            train_data_file_path = os.path.join(self.upload_tmp_path, file_name)
            with open(train_data_file_path, 'w', newline='') as output_file:
                dict_writer = csv.DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(input_data)

            # 저장된 lookup을 s3에 저장하기.
            bucket = katinfo['train_bucket_name']
            # prefix = katinfo['train_input_prefix']

            try:
                # yield {"_time": time.time(), "Message": "S3 uploading!!!", "Bucket_File_List": "", "Size": "", "Last_Modfied": "" }
                response = s3files.uploadFile(train_data_file_path, bucket, self.S3_path)
                self.logger.error('[MfS]', response)
                if response is not None:                    
                    object_key = os.path.join(bucket, self.S3_path)
                    utc_time = response["LastModified"] 
                    formatted_time = utc_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
                    yield {"_time": time.time(), "Message": "S3 upload Success", "Bucket_File": object_key, "Size": f"{response['ContentLength']} bytes", "Last_Modfied": formatted_time}

                else:
                    yield {"_time": time.time(), "Message": "S3 upload Fail"}
                os.remove(train_data_file_path) # 완료 후 tmp 파일 삭제하여 공간 유지
            except ClientError as e:
                yield {"_time": time.time(), "Message": "Check bucket info!!!"} 
            except Exception as e:
                yield {"_time": time.time(), "Message":  str(e)} 
        else:
            yield {"_time": time.time(), 'Message': 'Please, train_data file name check!!!'}

dispatch(KatDataset, sys.argv, sys.stdin, sys.stdout, __name__)

