#!/usr/bin/env python
# coding=utf-8
#
import os, sys
import json
import requests
import csv
import random
import time
import io
import zipfile
import datetime

from datetime import timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators
from s3_files import S3Files
from botocore.exceptions import ClientError
from kat_utils import *
import boto3
import yaml

@Configuration()
class KatInference(EventingCommand):
    """
    The KatInference command sends data to the Edge App and receives the inference results.

    Example:

    ``| inputlookup input_data.csv | KatInference file_name="inference_data.csv"``

    Returns records having inference complete.
    """

    lookup_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'mellerikat-for-splunk', 'lookups')
    upload_tmp_path = os.path.join(lookup_path, "_tmp")
    input_file_name = Option(doc='''**Syntax:** **input_file_name=***<infer_data.csv>*''', require=True)
    model = Option(doc='''**Syntax:** **model=***<model>*''', default='default', require=False)
    model_name = Option(doc='''**Syntax:** **model_name=***<model_name>*''', default='default', require=False)
    output_file_name = Option(doc='''**Syntax:** **output_file_name=***<output_filename>*''', default='output.csv', require=False)
    inference_source = Option(require=False, default="s3")
    profile_name = Option(require=False, default=None)
    zip_file_name = Option(require=False)
    bucket_name = Option(require=False)
    wait_timeout = Option(require=False, default=60)
    poll_interval = Option(require=False, default=5)
    debug_check = Option(require=False, default=False)


    def get_mellerikat_conf(self, model=None):
        """Get mellerikat config from Splunk config file."""
        if (model is None):
            mellerikat_session = "default"
        else:
            mellerikat_session = "mellerikat:" + model
        return getMellerikatConf(mellerikat_session)

    def write_csv(self, file_path, data, fieldnames):
        """Write data to a CSV file."""
        with open(file_path, 'w', newline='') as outfile:
            csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(data)

    def _read_zipfile_results(self, zip_buffer):
        """Read results from a Zip file."""
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            with z.open(f'output/{self.output_file_name}') as result_file:
                result_reader = csv.DictReader(result_file.read().decode('utf-8').splitlines())
            try:
                with z.open('/output/splunk.yaml') as summary_file:
                    result_summary = yaml.safe_load(summary_file)
            except:
                result_summary = None
        return list(result_reader), result_summary

    def _process_s3_zip(self, bucket_name, prefix, last_time):
        """Retrieve and process zip file from S3."""
        katinfo = self.get_mellerikat_conf()
        s3files = S3Files(katinfo['profile_name'])

        start_time = time.time()
        zip_buffer = io.BytesIO()

        while True:
            try:
                self.logger.error(f"[MfS] Response")
                self.logger.error(bucket_name)
                self.logger.error(prefix)
                response = s3files.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
                if self.debug_check: self.logger.error(f"reponse list: {response}")

                if 'Contents' in response:
                    for obj in response['Contents']:
                        if self.debug_check: self.logger.error(f"{obj['Key']} - {obj['Size']} - {obj['LastModified']}")
                        if obj['Key'].endswith('inference_artifacts.zip') and obj['Size'] > 0 and obj['LastModified'] > last_time:
                            if self.debug_check: self.logger.error(f"key name: {obj['Key']}")
                            s3files.s3_client.download_fileobj(bucket_name, obj['Key'], zip_buffer)
                            zip_buffer.seek(0)
                            return self._read_zipfile_results(zip_buffer)
                if time.time() - start_time >= int(self.wait_timeout):
                    raise TimeoutError(f"File not found within timeout period.")
                time.sleep(int(self.poll_interval))
            except Exception as e:
                self.logger.error(f"Error while waiting for S3 zip file: {e}")
                raise

    def transform(self, records):
        katinfo = self.get_mellerikat_conf()
        katinfo_model = self.get_mellerikat_conf(self.model)
        self.logger.error(f"Input: {records}")
        self.logger.error(f"Input: {katinfo}")
        self.logger.error(f"Input model: {katinfo_model}")
        self.logger.error(f"debug: {self.debug_check}")
        self.logger.error(f"error2 - type {type(katinfo['profile_name'])} / {len(katinfo['profile_name'])} / {self.profile_name}")

        s3files = S3Files(katinfo['profile_name'])
        input_data = [record for record in records]
        keys = input_data[0].keys()

        session_key = self._metadata.searchinfo.session_key  # Splunk 인증 토큰 가져오기
        # self.logger.error(f"session_key : {session_key}")


        if is_csv_file_name(self.input_file_name):
            check_if_exists_tmp(self.upload_tmp_path)
            infer_data_file_path = os.path.join(self.upload_tmp_path, self.input_file_name)
            self.write_csv(infer_data_file_path, input_data, keys)

            # 새로 생성된 규칙에서 파일명과 버킷명을 구분하기
            input_path_tmp = katinfo_model['infer_input_path'].split("/")
            bucket_input  = input_path_tmp[0] 
            prefix_input  = "/".join(input_path_tmp[1:])
            output_path_tmp = katinfo_model['infer_output_path'].split("/")
            bucket_output  = output_path_tmp[0] 
            prefix_output  = "/".join(output_path_tmp[1:])        
            if self.debug_check: self.logger.error(f"bucket_input: {bucket_input} / prefix_input: {prefix_input} / bucket_output: {bucket_output} /  prefix_output: {prefix_output}")

            try:
                s3files.deleteFile(bucket_output, os.path.join(prefix_output, "inference_artifacts.zip"))
                upload_path_dt = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                response = s3files.uploadFile(infer_data_file_path, bucket_input, os.path.join(prefix_input, upload_path_dt, self.input_file_name))
                os.remove(infer_data_file_path)

                if response is not None:
                    upload_time = response['LastModified'].astimezone(datetime.timezone.utc)
                    self.logger.error(f"[MfS] Upload Response")
                    self.logger.error(upload_time)

                    if self.inference_source == "s3":
                        result, summary = self._process_s3_zip(bucket_output, prefix_output, upload_time)
                    elif self.inference_source == "disk":
                        result = self._process_disk_zip(self.zip_file_name)
                    else:
                        raise ValueError("Invalid 'inference_source' option.")

                    result_key = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    result_path = os.path.join(self.lookup_path, f"{result_key}-result.csv")
                    summary_path = os.path.join(self.lookup_path, f"{result_key}-summary.csv")

                    result_data = []
                    if summary is not None:
                        summary_flat = {'result_key':result_key, **summary}
                        self.write_csv(summary_path, [summary_flat], summary_flat.keys())
                        
                        for row in result:
                            row["result_key"] = result_key  # 새로운 컬럼 추가
                            result_data.append(row)
 
                        column_order = ['pred_y_column', 'pred_prob_columns', 'y_column', 'x_categorical_columns', 'x_numeric_columns']
                        reordered_result_data = []
 
                        for row in result_data:
                            new_row = {}
                            for col in column_order:
                                if col in summary_flat:
                                    keys = summary_flat[col]
                                    if isinstance(keys, list):
                                        for key in keys:
                                            if key in row:
                                                new_row[key] = row[key]
                                    else:
                                        if keys in row:
                                            new_row[keys] = row[keys]
                            new_row['result_key'] = row['result_key']
                            reordered_result_data.append(new_row)
 
                        yield from reordered_result_data
 
                        self.write_csv(result_path, result_data, result_data[0].keys())
                    else:
                        for row in result:
                            row["result_key"] = result_key  # 새로운 컬럼 추가
                            result_data.append(row)
                        yield from result_data
 
                        self.write_csv(result_path, result_data, result_data[0].keys())                                    

                else:
                    yield {"_time": time.time(), "Message": "Check Upload!!!"}

            except ClientError as e:
                yield {"_time": time.time(), "Message": f"Check bucket info!!! {str(e)}"}
            except Exception as e:
                yield {"_time": time.time(), "Message": str(e)}
        else:
            yield {"_time": time.time(), "Message": "Please, file_name file name check!!!"}

dispatch(KatInference, sys.argv, sys.stdin, sys.stdout, __name__)
