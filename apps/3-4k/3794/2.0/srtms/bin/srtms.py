import os
import sys
import json
import requests
import time
import splunklib.client as client
from splunklib.modularinput import *

class sRTMS(Script):
	
	# Define some global variables
	MASK           = "*************"
	APP            = __file__.split(os.sep)[-3]
	SRTMS_LOGIN     = None
	CLEAR_SRTMS_PWD = None
	SPLUNK_LOGIN     = None
	CLEAR_SPLUNK_PWD = None
	
	def get_scheme(self):

		scheme = Scheme("fatstacks")
		scheme.description = ("Identify software vulnerabilities with sRTMS.")
		scheme.use_external_validation = True
		scheme.streaming_mode_xml = True
		scheme.use_single_instance = False

		srtms_api_arg = Argument(
                        name="srtms_sam",
                        title="Software Asset Management",
                        description="Enable Software Asset Management.",
                        data_type=Argument.data_type_boolean,
                        required_on_create=True,
                        required_on_edit=True
                )
                scheme.add_argument(srtms_api_arg)

		srtms_api_arg = Argument(
                        name="srtms_svm",
                        title="Software Vulnerability Management",
                        description="Enable Software Vulnerability Management.",
                        data_type=Argument.data_type_boolean,
                        required_on_create=True,
                        required_on_edit=True
                )
                scheme.add_argument(srtms_api_arg)

                srtms_api_arg = Argument(
                        name="srtms_api",
                        title="sRTMS API Url",
                        description="The sRTMS API Url.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(srtms_api_arg)

                srtms_license_arg = Argument(
                        name="srtms_license",
                        title="sRTMS License",
                        description="Your sRTMS License key.",
                        data_type=Argument.data_type_string,
                        required_on_create=True,
                        required_on_edit=True
                )
                scheme.add_argument(srtms_license_arg)

                srtms_login_arg = Argument(
                        name="srtms_login",
                        title="sRTMS Login",
                        description="Your sRTMS Login.",
                        data_type=Argument.data_type_string,
                        required_on_create=True,
                        required_on_edit=True
                )
                scheme.add_argument(srtms_login_arg)

                srtms_pwd_arg = Argument(
                        name="srtms_pwd",
                        title="sRTMS Password",
                        description="Your sRTMS Password.",
                        data_type=Argument.data_type_string,
                        required_on_create=True,
                        required_on_edit=True
                )
                scheme.add_argument(srtms_pwd_arg)
                
                splunk_api_arg = Argument(
                        name="splunk_api",
                        title="Splunk API Url",
                        description="The Splunk API Url. When provided, Splunk indexes will be used as a datasource for fatstacks sRTMS.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(splunk_api_arg)
                
                splunk_login_arg = Argument(
                        name="splunk_login",
                        title="Splunk Login",
                        description="The Splunk Login.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(splunk_login_arg)

                splunk_pwd_arg = Argument(
                        name="splunk_pwd",
                        title="Splunk Password",
                        description="The Splunk Password.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(splunk_pwd_arg)

                splunk_device_search_arg = Argument(
                        name="splunk_device_search",
                        title="Device Search",
                        description="The Splunk Device Search query.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(splunk_device_search_arg)

                splunk_package_search_arg = Argument(
                        name="splunk_package_search",
                        title="Package Search",
                        description="The Splunk Device Search query.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(splunk_package_search_arg)

                srtms_api_size_arg = Argument(
                        name="srtms_api_size",
                        title="sRTMS API size page",
                        description="The sRTMS API size page.",
                        data_type=Argument.data_type_string
                )
                scheme.add_argument(srtms_api_size_arg)
        
		return scheme

	def validate_input(self, definition):
		session_key = definition.metadata["session_key"]
                srtms_api    = definition.parameters["srtms_api"]
		srtms_login    = definition.parameters["srtms_login"]
		srtms_pwd    = definition.parameters["srtms_pwd"]
##		srtms_license    = definition.parameters["srtms_license"]
		
		try:
			# Do checks here.  For example, try to connect to whatever you need the credentials for using the credentials provided.
			# If everything passes, create a credential with the provided input.
##			r = requests.post(srtms_api+'/customer-rest-service/customers/login', headers={'Accept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1'}, data=json.dumps({'userName': srtms_login,'password':srtms_pwd}))
##			response_json = json.loads(r.text)
##
##                        v_license = response_json['results']['customer']['license']
##
##                        if srtms_license != v_license:
##                                raise ValueError("The sRTMS license is not valid."
                        
			pass
		except Exception as e:
			raise Exception, "Something did not go right: %s" % str(e)

	def encrypt_password(self, username, password, session_key):
		args = {'token':session_key}
		service = client.connect(**args)
		
		try:
			# If the credential already exists, delte it.
			for storage_password in service.storage_passwords:
				if storage_password.username == username:
					service.storage_passwords.delete(username=storage_password.username)
					break

			# Create the credential.
			service.storage_passwords.create(password, username)

		except Exception as e:
			raise Exception, "An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e)

	def mask_password(self, session_key, srtms_sam, srtms_svm, srtms_api, srtms_license, srtms_login, splunk_api, splunk_login, splunk_device_search, splunk_package_search, srtms_api_size):
		try:
			args = {'token':session_key}
			service = client.connect(**args)
			kind, input_name = self.input_name.split("://")
			item = service.inputs.__getitem__((input_name, kind))
			
			kwargs = {
                                "srtms_sam": srtms_sam,
                                "srtms_svm": srtms_svm,
                                "srtms_api": srtms_api,
                                "srtms_license": srtms_license,
                                "srtms_login": srtms_login,
                                "srtms_pwd": self.MASK,
                                "splunk_api": splunk_api,
                                "splunk_login": splunk_login,
                                "splunk_pwd": self.MASK,
                                "splunk_device_search": splunk_device_search,
                                "splunk_package_search": splunk_package_search,
                                "srtms_api_size": srtms_api_size
			}
			item.update(**kwargs).refresh()
			
		except Exception as e:
			raise Exception("Error XXXXXXXXXXXXXXXXXX updating inputs.conf: %s" % str(e))

	def get_password(self, session_key, username):
		args = {'token':session_key}
		service = client.connect(**args)

		# Retrieve the password from the storage/passwords endpoint	
		for storage_password in service.storage_passwords:
			if storage_password.username == username:
				return storage_password.content.clear_password

        def srtms_api_login(self, srtms_api, srtms_login, srtms_pwd):
                # API Login
                try:
                        r = requests.post(srtms_api+'/customer-rest-service/customers/login', headers={'Accept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1'}, data=json.dumps({'userName': srtms_login,'password':srtms_pwd}))
                except Exception as e:
                        raise Exception("Error calling sRTMS Login API: %s" % str(e))
                    
                if str(r.status_code) != "200":
                        raise Exception("Error calling sRTMS Login API - Status Code: %s " % str(r.status_code))

                response_json = json.loads(r.text)
                
                v_success = response_json["success"]

                if v_success == False:
                        v_message = response_json['message']
                        raise Exception("Error calling sRTMS Login API - Message: %s " % str(v_message))

                v_license = response_json['results']['customer']['license']
                v_sessiontoken = response_json['results']['customer']['azureToken']
                v_companyname = response_json['results']['customer']['companyName']
                
                return (v_license, v_sessiontoken, v_companyname)

        def srtms_api_trigger(self, job_name, splunk_api, splunk_login, splunk_pwd, device_search, package_search, srtms_api, v_sessiontoken):
                # API - Trigger for Splunk
                try:
                        payload={'jobName':job_name,'userName':splunk_login,'password':splunk_pwd,'url':splunk_api,'deviceSearch':device_search,'packageSearch':package_search}
                        r = requests.post(srtms_api+'/job-rest-service/splunk/job', headers={'ActionCentercept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1','X-AD-Authorization':v_sessiontoken}, data=json.dumps(payload))
                except Exception as e:
                        raise Exception("Error calling sRTMS Trigger for Splunk API: %s" % str(e))

                if str(r.status_code) != "200":
                        raise Exception("Error calling sRTMS Trigger for Splunk API - Status Code: %s " % str(r.status_code))

                response_json = json.loads(r.text)

                v_success = response_json["success"]

                if v_success == False:
                        v_message = response_json['message']
                        raise Exception("Error calling sRTMS Trigger for Splunk API - Message: %s " % str(v_message))

                v_job_id = response_json['results']['jobId']
                
                return v_job_id

        def srtms_api_status(self, v_job_id, srtms_api, v_sessiontoken):
                # API - Splunk Status
                try:
                        r = requests.get(srtms_api+'/job-rest-service/splunk/job/'+v_job_id, headers={'Accept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1','X-AD-Authorization':v_sessiontoken})
                except Exception as e:
                        raise Exception("Error calling sRTMS Status API: %s" % str(e))

                if str(r.status_code) != "200":
                        raise Exception("Error calling sRTMS Status API - Status Code: %s " % str(r.status_code))

                response_json = json.loads(r.text)

                v_success = response_json["success"]

                if v_success == False:
                        v_message = response_json['message']
                        raise Exception("Error calling sRTMS Trigger for Splunk API - Message: %s " % str(v_message))

                v_job_status = response_json['results']['status']
                v_job_progress = response_json['results']['progress']

                return (v_job_status, v_job_progress)

        def srtms_api_pull_svm(self, v_pagenumber, v_pagesize, v_companyname, job_name, input_name, srtms_api, v_sessiontoken, v_retry, ew):
                # API - Pull data
                try:
                        payload={'pageNumber': v_pagenumber,'pageSize': v_pagesize,'criteria':{'query':{'bool':{'must':[{'term':{'isPatch':'false'}},{'terms':{'cpe_Part':['a']}}]}}}}
                        r = requests.post(srtms_api+'/job-rest-service/job/search/'+v_companyname+'-'+job_name+'/ProductCVE', headers={'Accept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1','X-AD-Authorization':v_sessiontoken}, data=json.dumps(payload))

                except Exception as e:
                        raise Exception("Error calling sRTMS Pull SVM API: %s" % str(e))
                
                if str(r.status_code) != "200":
                        raise Exception("Error calling sRTMS Pull SVM API - Status Code: %s " % str(r.status_code))

                response_json = json.loads(r.text)

                v_success = response_json["success"]
                v_message = response_json["message"]
                
                if v_success == False and v_retry <= 5:
                        ew.log("INFO", "Error calling sRTMS Pull SVM API - Message: %s " % str(v_message))
                        ew.log("INFO", "Retry calling sRTMS Pull SVM API in 60s - # %s" % str(v_retry))
                        #Wait 60s
                        time.sleep(60)
                        v_retry = v_retry + 1
                        return (0,0,v_retry)
                if v_success == False:
                        raise Exception("Error calling sRTMS Pull SVM API - Message: %s " % str(v_message))
                
                v_totalElements = response_json['results']['data']['totalElements']
                v_totalPage = response_json['results']['data']['totalPage']
                v_pageNumber = response_json['results']['data']['pageNumber']

                jss_purpose_raw = response_json['results']['data']['content']

                ew.log("INFO", "%s CVEs" % str(len(jss_purpose_raw)))

                #i=0
                for ea in jss_purpose_raw:
                        #i=i+1
                        #ew.log("INFO", "Counter: %s" % str(i))

                        try:
                                v_source = ea["_source"]["source"]
                        except Exception as e:
                                v_source = ""
                                
                        try:
                                v_deviceID = ea["_source"]["deviceID"]
                        except Exception as e:
                                v_deviceID = ""

                        try:
                                v_deviceName = ea["_source"]["deviceName"]
                        except Exception as e:
                                v_deviceName = ""

                        try:
                                v_cve_ID = ea["_source"]["cve_ID"]
                        except Exception as e:
                                v_cve_ID = ""

                        try:
                                v_cvss_Severity = ea["_source"]["cvss_Severity"]
                        except Exception as e:
                                v_cvss_Severity = ""

                        try:
                                v_cvss_severity_base_score = ea["_source"]["cvss_severity_base_score"]
                        except Exception as e:
                                v_cvss_severity_base_score = ""

                        try:
                                v_cve_Description = ea["_source"]["cve_Description"]
                        except Exception as e:
                                v_cve_Description = ""

                        try:
                                v_cve_publishedDate = ea["_source"]["cve_publishedDate"]
                        except Exception as e:
                                v_cve_publishedDate = ""

                        try:
                                v_cpe_URI_2_3 = ea["_source"]["cpe_URI_2_3"]
                        except Exception as e:
                                v_cpe_URI_2_3 = ""

                        try:
                                v_cpe_URI_2_2 = ea["_source"]["cpe_URI_2_2"]
                        except Exception as e:
                                v_cpe_URI_2_2 = ""
                            
                        try:
                                v_cpe_Title = ea["_source"]["cpe_Title"]
                        except Exception as e:
                                v_cpe_Title = ""
                        
                        try:
                                v_cpe_Part = ea["_source"]["cpe_Part"]
                        except Exception as e:
                                v_cpe_Part = ""
                            
                        try:
                                v_cpe_Manufacturer = ea["_source"]["cpe_Manufacturer"]
                        except Exception as e:
                                v_cpe_Manufacturer = ""
                            
                        try:
                                v_cpe_Product = ea["_source"]["cpe_Product"]
                        except Exception as e:
                                v_cpe_Product = ""

                        try:
                                v_cpe_Version = ea["_source"]["cpe_Version"]
                        except Exception as e:
                                v_cpe_Version = ""

                        try:
                                v_cpe_Update = ea["_source"]["cpe_Update"]
                        except Exception as e:
                                v_cpe_Update = ""        
                        
                        try:
                                v_cpe_Edition = ea["_source"]["cpe_Edition"]
                        except Exception as e:
                                v_cpe_Edition = ""     

                        try:
                                v_isPatch = ea["_source"]["isPatch"]
                        except Exception as e:
                                v_isPatch = None
                                
                        try:
                                v_isPatchAvailable = ea["_source"]["isPatchAvailable"]
                        except Exception as e:
                                v_isPatchAvailable = None
                        
                        try:
                                v_kb = ea["_source"]["kb"]
                        except Exception as e:
                                v_kb = ""

                        try:
                                v_availableKB = ea["_source"]["availableKB"]
                        except Exception as e:
                                v_availableKB = ""

                        try:
                                v_lastScan = ea["_source"]["lastScan"]
                        except Exception as e:
                                v_lastScan = ""

                        try:
				v_pkgInfos = json.dumps(ea["_source"]["pkgInfos"], sort_keys=True)
                        except Exception as e:
                                v_pkgInfos = ""
                                

                        if v_source != 'Splunk':
                                v_deviceID = v_deviceName
                                
                        event = Event()
                        event.stanza = input_name
                        event.source = 'ProductCVE'
                        event.host = v_deviceID

                        event.data =  'deviceName="%s" cve_ID="%s" cvss_Severity="%s" cvss_severity_base_score="%s" cve_Description="%s" cve_publishedDate="%s" cpe_URI_2_3="%s" cpe_URI_2_2="%s" cpe_Title="%s" cpe_Part="%s" cpe_Manufacturer="%s" cpe_Product="%s" cpe_Version="%s" cpe_Update="%s" cpe_Edition="%s" isPatch=%s isPatchAvailable=%s kb="%s" availableKB="%s" lastScan="%s" pkgInfos="%s"' % \
                                     (v_deviceName.replace('"', '\''), \
                                      v_cve_ID.replace('"', '\''), \
                                      v_cvss_Severity.replace('"', '\''), \
                                      v_cvss_severity_base_score.replace('"', '\''), \
                                      v_cve_Description.replace('"', '\''), \
                                      v_cve_publishedDate.replace('"', '\''), \
                                      v_cpe_URI_2_3.replace('"', '\''), \
                                      v_cpe_URI_2_2.replace('"', '\''), \
                                      v_cpe_Title.replace('"', '\''), \
                                      v_cpe_Part.replace('"', '\''), \
                                      v_cpe_Manufacturer.replace('"', '\''), \
                                      v_cpe_Product.replace('"', '\''), \
                                      v_cpe_Version.replace('"', '\''), \
                                      v_cpe_Update.replace('"', '\''), \
                                      v_cpe_Edition.replace('"', '\''), \
                                      v_isPatch, \
                                      v_isPatchAvailable, \
                                      v_kb.replace('"', '\''), \
                                      v_availableKB.replace('"', '\''), \
                                      v_lastScan.replace('"', '\''), \
                                      v_pkgInfos.replace('"', '\'') \
                                      )
                        
                        ew.write_event(event)
                        
                return (v_totalElements,v_totalPage,0)

        def srtms_api_pull_sam(self, v_pagenumber, v_pagesize, v_companyname, job_name, input_name, srtms_api, v_sessiontoken, v_retry, ew):
                # API - Pull data
                try:
                        payload={'pageNumber': v_pagenumber,'pageSize': v_pagesize,'criteria':{'query':{'bool':{'must':[{'term':{'isCPE':'true'}},{'terms':{'cpe_Part':['a','o']}}]}}}}
                        r = requests.post(srtms_api+'/job-rest-service/job/search/'+v_companyname+'-'+job_name+'/ProductSummary', headers={'Accept': 'application/json','Content-Type': 'application/json','X-MS-VERSION': 'v0.1.1','X-AD-Authorization':v_sessiontoken}, data=json.dumps(payload))
                except Exception as e:
                        raise Exception("Error calling sRTMS Pull SAM API: %s" % str(e))

                if str(r.status_code) != "200":
                        raise Exception("Error calling sRTMS Pull SAM API - Status Code: %s " % str(r.status_code))

                response_json = json.loads(r.text)

                v_success = response_json["success"]
                v_message = response_json["message"]
                
                if v_success == False and v_retry <= 5:
                        ew.log("INFO", "Error calling sRTMS Pull SAM API - Message: %s " % str(v_message))
                        ew.log("INFO", "Retry calling sRTMS Pull SAM API in 60s - # %s" % str(v_retry))
                        #Wait 60s
                        time.sleep(60)
                        v_retry = v_retry + 1
                        return (0,0,v_retry)
                if v_success == False:
                        raise Exception("Error calling sRTMS Pull SAM API - Message: %s " % str(v_message))

                v_totalElements = response_json['results']['data']['totalElements']
                v_totalPage = response_json['results']['data']['totalPage']
                v_pageNumber = response_json['results']['data']['pageNumber']

                jss_purpose_raw = response_json['results']['data']['content']

                ew.log("INFO", "%s Products" % str(len(jss_purpose_raw)))

                #i=0
                for ea in jss_purpose_raw:
                        #i=i+1
                        #ew.log("INFO", "Counter: %s" % str(i))

                        try:
                                v_source = ea["_source"]["source"]
                        except Exception as e:
                                v_source = ""
                                
                        try:
                                v_deviceID = ea["_source"]["deviceID"]
                        except Exception as e:
                                v_deviceID = ""

                        try:
                                v_deviceName = ea["_source"]["deviceName"]
                        except Exception as e:
                                v_deviceName = ""

                        try:
                                v_cpe_URI_2_3 = ea["_source"]["cpe_URI_2_3"]
                        except Exception as e:
                                v_cpe_URI_2_3 = ""

                        try:
                                v_cpe_URI_2_2 = ea["_source"]["cpe_URI_2_2"]
                        except Exception as e:
                                v_cpe_URI_2_2 = ""
                            
                        try:
                                v_cpe_Title = ea["_source"]["cpe_Title"]
                        except Exception as e:
                                v_cpe_Title = ""
                        
                        try:
                                v_cpe_Part = ea["_source"]["cpe_Part"]
                        except Exception as e:
                                v_cpe_Part = ""
                            
                        try:
                                v_cpe_Manufacturer = ea["_source"]["cpe_Manufacturer"]
                        except Exception as e:
                                v_cpe_Manufacturer = ""
                            
                        try:
                                v_cpe_Product = ea["_source"]["cpe_Product"]
                        except Exception as e:
                                v_cpe_Product = ""

                        try:
                                v_cpe_Version = ea["_source"]["cpe_Version"]
                        except Exception as e:
                                v_cpe_Version = ""

                        try:
                                v_cpe_Update = ea["_source"]["cpe_Update"]
                        except Exception as e:
                                v_cpe_Update = ""        
                        
                        try:
                                v_cpe_Edition = ea["_source"]["cpe_Edition"]
                        except Exception as e:
                                v_cpe_Edition = ""     

                        try:
                                v_cpe_Family = ea["_source"]["cpe_Family"]
                        except Exception as e:
                                v_cpe_Family = ""

                        try:
                                v_cpe_MinorVersion = ea["_source"]["cpe_MinorVersion"]
                        except Exception as e:
                                v_cpe_MinorVersion = ""
                                
                        try:
                                v_cpe_MajorVersion = ea["_source"]["cpe_MajorVersion"]
                        except Exception as e:
                                v_cpe_MajorVersion = ""

                        try:
                                v_cpe_IsSuite = ea["_source"]["cpe_IsSuite"]
                        except Exception as e:
                                v_cpe_IsSuite = None

                        try:
                                v_cpe_GA = ea["_source"]["cpe_GA"]
                        except Exception as e:
                                v_cpe_GA = ""

                        try:
                                v_cpe_EOL = ea["_source"]["cpe_EOL"]
                        except Exception as e:
                                v_cpe_EOL = ""

                        try:
                                v_cpe_EOS = ea["_source"]["cpe_EOS"]
                        except Exception as e:
                                v_cpe_EOS = ""

                        try:
                                v_isEOL = ea["_source"]["isEOL"]
                        except Exception as e:
                                v_isEOL = None

                        try:
                                v_isEOS = ea["_source"]["isEOS"]
                        except Exception as e:
                                v_isEOS = None

                        try:
                                v_cpe_IsLicensable = ea["_source"]["cpe_IsLicensable"]
                        except Exception as e:
                                v_cpe_IsLicensable = None

                        try:
                                v_cpe_IsOpensource = ea["_source"]["cpe_IsOpensource"]
                        except Exception as e:
                                v_cpe_IsOpensource = None
                               
                        try:
                                v_lastScan = ea["_source"]["lastScan"]
                        except Exception as e:
                                v_lastScan = ""

                        try:
				v_pkgInfos = json.dumps(ea["_source"]["pkgInfos"], sort_keys=True)
                        except Exception as e:
                                v_pkgInfos = ""


                        if v_source != 'Splunk':
                                v_deviceID = v_deviceName

                                
                        event = Event()
                        event.stanza = input_name
                        event.source = 'ProductSummary'
                        event.host = v_deviceID

                        event.data =  'deviceName="%s" cpe_URI_2_3="%s" cpe_URI_2_2="%s" cpe_Title="%s" cpe_Part="%s" cpe_Manufacturer="%s" cpe_Product="%s" cpe_Version="%s" cpe_Update="%s" cpe_Edition="%s" cpe_Family="%s" cpe_MinorVersion="%s" cpe_MajorVersion="%s" cpe_IsSuite=%s cpe_GA="%s" cpe_EOL="%s" cpe_EOS="%s" isEOL=%s isEOS=%s cpe_IsLicensable=%s cpe_IsOpensource=%s lastScan="%s" pkgInfos="%s"' % \
                                     (v_deviceName.replace('"', '\''), \
                                      v_cpe_URI_2_3.replace('"', '\''), \
                                      v_cpe_URI_2_2.replace('"', '\''), \
                                      v_cpe_Title.replace('"', '\''), \
                                      v_cpe_Part.replace('"', '\''), \
                                      v_cpe_Manufacturer.replace('"', '\''), \
                                      v_cpe_Product.replace('"', '\''), \
                                      v_cpe_Version.replace('"', '\''), \
                                      v_cpe_Update.replace('"', '\''), \
                                      v_cpe_Edition.replace('"', '\''), \
                                      v_cpe_Family.replace('"', '\''), \
                                      v_cpe_MinorVersion.replace('"', '\''), \
                                      v_cpe_MajorVersion.replace('"', '\''), \
                                      v_cpe_IsSuite, \
                                      v_cpe_GA.replace('"', '\''), \
                                      v_cpe_EOL.replace('"', '\''), \
                                      v_cpe_EOS.replace('"', '\''), \
                                      v_isEOL, \
                                      v_isEOS, \
                                      v_cpe_IsLicensable, \
                                      v_cpe_IsOpensource, \
                                      v_lastScan.replace('"', '\''), \
                                      v_pkgInfos.replace('"', '\'') \
                                      )
                        
                        ew.write_event(event)
                        
                return (v_totalElements,v_totalPage,0)

	def stream_events(self, inputs, ew):
                ew.log("INFO", "##############START sRTMS#################")
		self.input_name, self.input_items = inputs.inputs.popitem()
		session_key = self._input_definition.metadata["session_key"]

		kind, job_name = self.input_name.split("://")
                srtms_sam = self.input_items["srtms_sam"]
                srtms_svm = self.input_items["srtms_svm"]
                srtms_license = self.input_items["srtms_license"]
                srtms_login = self.input_items["srtms_login"]
                srtms_pwd = self.input_items["srtms_pwd"]

                try:
                        srtms_api = self.input_items["srtms_api"]
                        if srtms_api == "" or srtms_api == None:
                                srtms_api = "https://srtms.fatstacks.tech:11000"
                except Exception as e:
                        srtms_api = "https://srtms.fatstacks.tech:11000"

                try:
                        splunk_api = self.input_items["splunk_api"]
                        if splunk_api == "" or splunk_api == None:
                                splunk_api = ""
                except Exception as e:
                        splunk_api = ""

                try:
                        splunk_login = self.input_items["splunk_login"]
                        if splunk_login == "" or splunk_login == None:
                                splunk_login = "*************"
                except Exception as e:
                        splunk_login = "*************"

                try:
                        splunk_pwd = self.input_items["splunk_pwd"]
                        if splunk_pwd == "" or splunk_pwd == None:
                                splunk_pwd = "XXXXXXXXX"
                except Exception as e:
                        splunk_pwd = "XXXXXXXXX"
                        
                        
                try:
                        splunk_device_search = self.input_items["splunk_device_search"]
                        if splunk_device_search == "" or splunk_device_search == None:
                                splunk_device_search = '(index=windows OR index=os) (Type=Computer OR Type=OperatingSystem OR sourcetype=Unix:Version) earliest=-7d@d latest=now | stats values(host) as DeviceID values(Domain) as DeviceDomain values(ComputerName) as ComputerName max(_time) as LastScan values(Manufacturer) as Manufacturer values(Model) as Model values(OS) as OS values(os_name) as os_name values(ServicePack) as OSServicePack values(Version) as Version values(version) as version values(BuildNumber) as OSBuildNumber values(Architecture) as Architecture values(machine_architecture_name) as machine_architecture_name values(InstallDate) as OSInstallDate by host | eval LastScan=strftime(LastScan,"%F %T"), OSInstallDate=strftime(strptime(OSInstallDate,"%Y%m%d%H%M%S.000000+000"),"%F %T"), DeviceName=coalesce(ComputerName,DeviceID), OSName=coalesce(OS,os_name), OSVersion=coalesce(Version,version), OSBit=coalesce(Architecture,machine_architecture_name) | fields DeviceID DeviceDomain DeviceName LastScan Manufacturer Model OSName OSServicePack OSVersion OSBuildNumber OSBit OSInstallDate'
                except Exception as e:
                        splunk_device_search = '(index=windows OR index=os) (Type=Computer OR Type=OperatingSystem OR sourcetype=Unix:Version) earliest=-7d@d latest=now | stats values(host) as DeviceID values(Domain) as DeviceDomain values(ComputerName) as ComputerName max(_time) as LastScan values(Manufacturer) as Manufacturer values(Model) as Model values(OS) as OS values(os_name) as os_name values(ServicePack) as OSServicePack values(Version) as Version values(version) as version values(BuildNumber) as OSBuildNumber values(Architecture) as Architecture values(machine_architecture_name) as machine_architecture_name values(InstallDate) as OSInstallDate by host | eval LastScan=strftime(LastScan,"%F %T"), OSInstallDate=strftime(strptime(OSInstallDate,"%Y%m%d%H%M%S.000000+000"),"%F %T"), DeviceName=coalesce(ComputerName,DeviceID), OSName=coalesce(OS,os_name), OSVersion=coalesce(Version,version), OSBit=coalesce(Architecture,machine_architecture_name) | fields DeviceID DeviceDomain DeviceName LastScan Manufacturer Model OSName OSServicePack OSVersion OSBuildNumber OSBit OSInstallDate'

                try:
                        splunk_package_search = self.input_items["splunk_package_search"]
                        if splunk_package_search == "" or splunk_package_search == None:
                                splunk_package_search = '(index=Windows OR index=os) (sourcetype=Script:InstalledApps OR sourcetype=package) earliest=-7d@d latest=now | multikv | makemv delim=\"\\\"\" DisplayName | eval PkgManufacturer0=coalesce(Publisher,VENDOR), PkgDisplayName0=coalesce(DisplayName,NAME), PkgVersion0=coalesce(DisplayVersion,VERSION) | stats values(host) as DeviceID values(PkgManufacturer0) as PkgManufacturer, values(PkgDisplayName0) as PkgDisplayName values(PkgVersion0) as PkgVersion, values(ARCH) as PkgBit values(InstallDate) as InstallDate count by host, PkgManufacturer0, PkgDisplayName0, PkgVersion0 | fields DeviceID PkgManufacturer PkgDisplayName PkgVersion PkgBit InstallDate'
                except Exception as e:
                        splunk_package_search = '(index=Windows OR index=os) (sourcetype=Script:InstalledApps OR sourcetype=package) earliest=-7d@d latest=now | multikv | makemv delim=\"\\\"\" DisplayName | eval PkgManufacturer0=coalesce(Publisher,VENDOR), PkgDisplayName0=coalesce(DisplayName,NAME), PkgVersion0=coalesce(DisplayVersion,VERSION) | stats values(host) as DeviceID values(PkgManufacturer0) as PkgManufacturer, values(PkgDisplayName0) as PkgDisplayName values(PkgVersion0) as PkgVersion, values(ARCH) as PkgBit values(InstallDate) as InstallDate count by host, PkgManufacturer0, PkgDisplayName0, PkgVersion0 | fields DeviceID PkgManufacturer PkgDisplayName PkgVersion PkgBit InstallDate'
                        
                try:
                        srtms_api_size = self.input_items["srtms_api_size"]
                        if srtms_api_size == "" or srtms_api_size == None:
                                srtms_api_size = 500
                except Exception as e:
                        srtms_api_size = 500
                
                self.SRTMS_LOGIN = srtms_login
                self.SPLUNK_LOGIN = splunk_login

		try:
			# If the password is not masked, mask it.
			v_mask = 0

			if srtms_pwd != self.MASK:
                                self.encrypt_password(srtms_login, srtms_pwd, session_key)
                                v_mask = 1
                        if splunk_pwd != self.MASK:
                                self.encrypt_password(splunk_login, splunk_pwd, session_key)
                                v_mask = 1

                        if v_mask == 1:
                            self.mask_password(session_key, srtms_sam, srtms_svm, srtms_api, srtms_license, srtms_login,splunk_api, splunk_login, splunk_device_search, splunk_package_search, srtms_api_size)

			self.CLEAR_SRTMS_PWD = self.get_password(session_key, srtms_login)
			self.CLEAR_SPLUNK_PWD = self.get_password(session_key, splunk_login)
		except Exception as e:
			ew.log("ERROR", "Error: %s" % str(e))

		#SAM or SVM
		ew.log("INFO", "srtms_sam: %s" % str(srtms_sam))
		ew.log("INFO", "srtms_svm: %s" % str(srtms_svm))
		
		if (srtms_sam == "1") or (srtms_svm == "1"):

                        #API Login
                        ew.log("INFO", "Calling sRTMS Login API")
                        v_license, v_sessiontoken, v_companyname = self.srtms_api_login(srtms_api, srtms_login, self.CLEAR_SRTMS_PWD)

                        ew.log("INFO", "v_license: %s" % v_license)
                        ew.log("INFO", "v_sessiontoken: %s" % v_sessiontoken)
                        ew.log("INFO", "v_companyname: %s" % v_companyname)
                        ew.log("INFO", "splunk_api: %s" % splunk_api)

                        #API Trigger
                        if splunk_api != "" and splunk_api != None:
                                ew.log("INFO", "Calling sRTMS Trigger for Splunk API")
                                v_job_id = self.srtms_api_trigger(job_name, splunk_api, splunk_login, self.CLEAR_SPLUNK_PWD, splunk_device_search, splunk_package_search, srtms_api, v_sessiontoken)
            
                                ew.log("INFO", "v_job_id: %s" % v_job_id)

                                #API Status
                                v_job_status = 'wait'
                                while v_job_status == 'wait' or v_job_status == 'Progress':

                                        #Wait 30s
                                        time.sleep(30)
                                        
                                        ew.log("INFO", "Calling sRTMS Status API")
                                        v_job_status, v_job_progress = self.srtms_api_status(v_job_id, srtms_api, v_sessiontoken)
                                        ew.log("INFO", "v_job_status: %s" % v_job_status)
                                        if v_job_status == 'Progress':
                                                 ew.log("INFO", "v_job_progress: %s" % v_job_progress)
                                        #v_job_status = 'Done'
                                        #ew.log("INFO", "v_job_status: %s" % v_job_status)

                                if v_job_status != 'Done':
                                        raise Exception("Error calling sRTMS Status API - Job Status: %s " % str(v_job_status))

                        
                        #API Pull Data
                        ew.log("INFO", "v_pagesize: %s" % srtms_api_size)

                        if (srtms_sam == "1"):
                                ew.log("INFO", "Calling sRTMS Pull SAM API - Page 1/?")
                                v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_sam(1, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, 0, ew)
                                if v_retry != 0:
                                        v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_sam(1, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, v_retry, ew)
                                        
                                ew.log("INFO", "v_totalElements: %s" % str(v_totalElements))
                                ew.log("INFO", "v_totalPage: %s" % str(v_totalPage))

                                #v_totalPage = v_totalPage + 1 - 1

                                for i in range(2,v_totalPage+1):
                                        ew.log("INFO", "Calling sRTMS Pull SAM API - Page %s/%s" % (str(i),str(v_totalPage)))
                                        v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_sam(i, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, 0, ew)
                                        if v_retry != 0:
                                                v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_sam(i, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, v_retry, ew)

                        if (srtms_svm == "1"):
                                ew.log("INFO", "Calling sRTMS Pull SVM API - Page 1/?")
                                v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_svm(1, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, 0, ew)
                                if v_retry != 0:
                                        v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_svm(1, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, v_retry, ew)
                                            
                                ew.log("INFO", "v_totalElements: %s" % str(v_totalElements))
                                ew.log("INFO", "v_totalPage: %s" % str(v_totalPage))

                                #v_totalPage = v_totalPage + 1 - 1

                                for i in range(2,v_totalPage+1):
                                        ew.log("INFO", "Calling sRTMS Pull SVM API - Page %s/%s" % (str(i),str(v_totalPage)))
                                        v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_svm(i, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, 0, ew)
                                        if v_retry != 0:
                                                v_totalElements, v_totalPage, v_retry = self.srtms_api_pull_svm(i, srtms_api_size, v_companyname, job_name, self.input_name, srtms_api, v_sessiontoken, v_retry, ew)

                                    
                        ew.log("INFO", "##############END sRTMS#################")
                
if __name__ == "__main__":
	exitcode = sRTMS().run(sys.argv)
	sys.exit(exitcode)
