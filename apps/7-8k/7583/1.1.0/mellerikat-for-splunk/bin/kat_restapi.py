#!/usr/bin/env python
# coding=utf-8
#
import email
import os
import sys
import json
import base64
import shutil
import logging
import requests
import splunk
import mimetypes
import tarfile
import splunk.entity as entity
from splunk.clilib import cli_common as cli
from urllib.parse import unquote
import configparser
import urllib.parse
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import connect


from pathlib import Path

CONF_FILE = 'mellerikatinfo'  # kat.conf 파일

class KatConfHandler(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        try:
            # kvstore에 저장하기 위한 session 획득
            session_key = self.sessionKey
            
            self.response.setHeader('content-type', 'application/json')

            try:
                payload = self.request['payload']
                for el in payload.split('&'):
                    key, value = el.split('=')
                    if 'train_set' in key:  # train 일 경우
                        train_set = value
                    if 'model_name' in key:
                        model_name = value
                    if 'profile_name' in key:
                        profile_name = value
                    if 'train_bucket_name' in key:
                        train_bucket_name = urllib.parse.unquote(value)
                    # if 'train_input_prefix' in key:
                    #     train_input_prefix = urllib.parse.unquote(value)
                    # if 'infer_input_bucket' in key:
                    #     infer_input_bucket = urllib.parse.unquote(value)
                    # if 'infer_input_prefix' in key:
                    #     infer_input_prefix = urllib.parse.unquote(value)
                    # if 'infer_output_bucket' in key:
                    #     infer_output_bucket = urllib.parse.unquote(value)
                    # if 'infer_output_prefix' in key:
                    #     infer_output_prefix = urllib.parse.unquote(value)
                    if 'infer_input_path' in key:
                        infer_input_path = urllib.parse.unquote(value)
                    if 'infer_output_path' in key:
                        infer_output_path = urllib.parse.unquote(value)


            except Exception as e:
                self.response.write(e)
                self.response.write(json.dumps(e))

            if(train_set=="train"): 
                mellerikat_session = "default"  # 단독 설정
            else:                
                mellerikat_session = "mellerikat:" + model_name

            # kat.conf 파일 경로 구성
            splunk_home = os.environ.get('SPLUNK_HOME')
            conf_file_path = os.path.join(splunk_home, 'etc', 'apps', 'mellerikat-for-splunk', 'local', f'{CONF_FILE}.conf')


            # ConfigParser 객체 생성 및 파일 읽기
            config = configparser.ConfigParser(interpolation=None)

            # 파일이 있으면 읽고, 없으면 새로 생성
            if os.path.exists(conf_file_path):
                config.read(conf_file_path)
            else:
                # 파일이 없는 경우 빈 파일을 생성
                open(conf_file_path, 'w').close()

            # Stanza (model_name)가 없으면 추가
            if mellerikat_session not in config.sections():
                config.add_section(mellerikat_session)

            # 설정 값 저장
            config.set(mellerikat_session, 'profile_name', profile_name)
            if 'model_name' in locals():
                config.set(mellerikat_session, 'model_name', model_name)
            if 'train_bucket_name' in locals():
                config.set(mellerikat_session, 'train_bucket_name', train_bucket_name)
            # if 'train_input_prefix' in locals():  
            #     config.set(mellerikat_session, 'train_input_prefix', train_input_prefix)
            # if 'infer_input_bucket' in locals():                
            #     config.set(mellerikat_session, 'infer_input_bucket', infer_input_bucket)
            # if 'infer_input_prefix' in locals():
            #     config.set(mellerikat_session, 'infer_input_prefix', infer_input_prefix)
            # if 'infer_output_bucket' in locals():
            #     config.set(mellerikat_session, 'infer_output_bucket', infer_output_bucket)
            # if 'infer_output_prefix' in locals():
            #     config.set(mellerikat_session, 'infer_output_prefix', infer_output_prefix)
            if 'infer_input_path' in locals():
                config.set(mellerikat_session, 'infer_input_path', infer_input_path)
            if 'infer_output_path' in locals():
                config.set(mellerikat_session, 'infer_output_path', infer_output_path)

            # 설정을 파일에 저장
            with open(conf_file_path, 'w') as configfile:
                config.write(configfile)

            # kvstore 데이터 저장(화면에서 읽기 위해서 추가로 저장)
            if(train_set=="infer"):
                try:
                    # KV Store 설정
                    app_name = "mellerikat-for-splunk"               # KV Store가 속한 앱 이름
                    collection_name = "mellerikat_kv_configuration"  # KV Store 컬렉션 이름
                    owner = "nobody"  
                    

                    section_data = {key: value for key, value in config.items(mellerikat_session)}
                    # return {"status":200,"message":section_data,"mellerikat_session":mellerikat_session} # value check

                    payload = {
                        "_key": mellerikat_session,                                   # 섹션 이름을 _key로 사용
                        "last_modified": int(datetime.datetime.utcnow().timestamp()), # 수정 시간을 저장
                        **section_data                                                # 섹션 내 항목들을 데이터로 삽입
                    }



                    try:
                        # KV Store API 엔드포인트 설정(키 포함)
                        kv_store_url = f"/servicesNS/{owner}/{app_name}/storage/collections/data/{collection_name}/{mellerikat_session}"
                        # 먼저 GET 요청으로 해당 _key가 존재하는지 확인
                        response, content = splunk.rest.simpleRequest(
                            kv_store_url,
                            sessionKey=self.sessionKey,
                            method="GET",  # HTTP 메서드: GET (조회)
                        )

                        if response.status == 200:  # 해당 _key가 이미 존재하면 PUT으로 덮어쓰기
                            response, content = splunk.rest.simpleRequest(
                                kv_store_url,
                                sessionKey=self.sessionKey,
                                method="PUT",                  # HTTP 메서드: PUT (덮어쓰기)
                                jsonargs=json.dumps(payload),  
                            )
                        else:
                            return {"status": 500, "message": f"Error storing KV Store data: {response.status}"}
                    except Exception as e:
                        if '404' in str(e):
                    
                            # KV Store API 엔드포인트 설정(키 제외)
                            kv_store_url = f"/servicesNS/{owner}/{app_name}/storage/collections/data/{collection_name}"
                            # SimpleRequest를 사용해 POST 요청 보내기
                            response, content = splunk.rest.simpleRequest(
                                kv_store_url,
                                sessionKey=self.sessionKey,
                                method="POST",  
                                jsonargs=json.dumps(payload),  
                            )
                        else:
                            return {"status": 500, "message": f"Error storing KV Store data: {str(e)}"}

                except Exception as e:
                    return {"status": 500, "message": f"Error fetching KV Store data: {str(e)}"}


            # 성공적으로 저장했음을 클라이언트에 알림
            self.response.write(json.dumps({"status": "success", "message": "Configuration saved"}))
            self.response.setStatus(200)

        except Exception as e:
            # 오류 발생 시 에러 메시지 반환
            self.response.write(json.dumps({"status": "error", "message": str(e)}))
            self.response.setStatus(500)

            
    def handle_GET(self):
        # self.response.write(json.dumps({"status": "success", "message": "Configuration saved", "config_info":self.request}))

        full_path = self.request['path']
        path_parts = full_path.split('/')

        if len(path_parts) == 4: # "/services/kat-config/default"
            model_tmp = path_parts[3]
            model_name = model_tmp.split(":")
            # self.response.write(json.dumps({"status": "success", "model_tmp": model_tmp, "config_info":f"len {len(model_name)} / {model_name}"}))
            # return
            # kat.conf 파일 경로 구성
            if len(model_name) == 1:    # "/services/kat-config/default"
                mellerikat_session = model_name[0]
            else:                       # "/services/kat-config/model:default"    
                mellerikat_session = "mellerikat:" + model_name[1]
            
            try:
                cfg = cli.getConfStanza(CONF_FILE, mellerikat_session)
                self.response.write(json.dumps({"status": "success", "message": "Configuration info", "config_info":cfg}))
                self.response.setStatus(200)
                return
            except Exception as e:
                # 오류 발생 시 에러 메시지 반환
                self.response.write(json.dumps({"status": "error", "message": str(e)}))
                self.response.setStatus(500)
                return

        else:
            self.response.write(json.dumps({"status": "error", "message": "Invalid path. /services/kat-config/{model_tmp}"}))
            self.response.setStatus(400)
            return    


    # def handle_DELETE(self):
    #     # self.response.write(json.dumps({"status": "success", "message": "Configuration saved", "config_info":self.request}))
    #     try:
    #         # kvstore에 저장하기 위한 session 획득
    #         session_key = self.sessionKey
    #         mellerikat_session = "mellerikat:" + model_name

        

    #         full_path = self.request['path']
    #         path_parts = full_path.split('/')

    #         if len(path_parts) == 4: # "/services/kat-config/mobilnet"
    #             model_name = path_parts[3]
    #             # kat.conf 파일 경로 구성
    #             mellerikat_session = "mellerikat:" + model_name

    #         else:
    #             self.response.write(json.dumps({"status": "error", "message": "Invalid path. /services/kat-config/{model_name}"}))
    #             self.response.setStatus(400)
    #             return         
    #     except Exception as e:
    #         # 오류 발생 시 에러 메시지 반환
    #         self.response.write(json.dumps({"status": "error", "message": str(e)}))
    #         self.response.setStatus(500)
    #         return                   