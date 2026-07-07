import sys
import os
from base64 import b64encode
import json
import time

class AuthenticateMOVEit():

    def __init__(self,helper,server_type,server_address,uname,pwd):
        self.helper = helper
        self.server_type = server_type
        self.server_address = server_address
        self.uname = uname
        self.pwd = pwd
        self.class_name = 'authenticate'
        self.http_timeout = 30

    def SendRequest(self):

        self.helper.log_debug(f'{self.server_type} - {self.class_name} - SendRequest - Start')
        # offset in seconds
        token_refresh_offset = 300
        self.helper.log_debug(f'{self.server_type} - {self.class_name} - token_refresh_offset : {token_refresh_offset}')

        # defining checkpoint values. 2 sets will be there for automation and transfer servers
        token_checkpoint = f'ta_moveit_{self.server_type}_token'  # last token
        refresh_token_checkpoint = f'ta_moveit_{self.server_type}_ref_token'  # refresh token
        token_exp_checkpoint = f'ta_moveit_{self.server_type}_exp' # token expiration time in epoch

        # read existing checkpoint values
        last_saved_token = self.helper.get_check_point(f'{token_checkpoint}')
        self.helper.log_debug(f'{self.server_type} - {self.class_name} - last_saved_token : {last_saved_token}')
        last_saved_refresh_token = self.helper.get_check_point(f'{refresh_token_checkpoint}')
        self.helper.log_debug(f'{self.server_type} - {self.class_name} - last_saved_refresh_token : {last_saved_refresh_token}')
        last_saved_exp_time = self.helper.get_check_point(f'{token_exp_checkpoint}')
        self.helper.log_debug(f'{self.server_type} - {self.class_name} - last_saved_exp_time : {last_saved_exp_time}')

        url = f'{self.server_address}/api/v1/token'

        # datetime now in epoch
        dateTimeNow = int(time.time())
        self.helper.log_debug(f'{self.server_type} - {self.class_name} - dateTimeNow : {dateTimeNow}')

        if last_saved_token == None or last_saved_refresh_token == None or last_saved_exp_time == None:
            # token does not exist. use username and password to request new token
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - either last_saved_token, last_saved_refresh_token, last_saved_exp_time is none')
            response = self.RequestToken(url,self.uname,self.pwd)

        elif dateTimeNow > last_saved_exp_time:
            # token has expired. use username and password to ask for a new token 
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - dateTimeNow > last_saved_exp_time')
            response = self.RequestToken(url,self.uname,self.pwd)

        elif dateTimeNow + token_refresh_offset > last_saved_exp_time:
            # if token is about to expire, try to refresh the token using refresh token
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - dateTimeNow + token_refresh_offset > last_saved_exp_time')
            response = self.RefreshToken(url,last_saved_refresh_token)

        else:
            # return the existing token
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - return last_saved_token')
            return last_saved_token

        self.helper.log_debug(f'respose message : {response}')
            
        r_status = response.status_code

        if r_status == 200:

            self.helper.log_debug(f'token retrieve - success')

            new_access_token = response.json()['access_token']
            new_refresh_token = response.json()['refresh_token']
            new_exp = response.json()['expires_in']            

            # set new checkpoint values
            self.helper.save_check_point(f'{token_checkpoint}',new_access_token)
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - new_access_token : {new_access_token}')
            self.helper.save_check_point(f'{refresh_token_checkpoint}',new_refresh_token)
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - new_refresh_token : {new_refresh_token}')

            # set new expiration time in epoch
            dateTimeNow = int(time.time())
            new_exp_time = dateTimeNow + new_exp
            self.helper.save_check_point(f'{token_exp_checkpoint}',new_exp_time)
            self.helper.log_debug(f'{self.server_type} - {self.class_name} - new_exp_time : {new_exp_time}')

            return new_access_token

        elif r_status == 401 or r_status == 403:
            self.helper.log_error(f'invalid credentials.')
            self.helper.log_debug(r_status)
            self.helper.log_debug(response.json())
            raise ValueError(r_status)

        else:
            self.helper.log_error(f'unable to fetch the access token.')
            self.helper.log_debug(r_status)
            self.helper.log_debug(response.json())
            raise ValueError(r_status)

    def RequestToken(self,url,uname,pwd):

        self.helper.log_debug(f'Start RequestToken')

        token_url = f'{self.server_address}/api/v1/token'

        payld = f'grant_type=password&username={uname}&password={pwd}'

        userAndPass = b64encode(bytes(f'{uname}:{pwd}',encoding='utf-8')).decode("ascii")

        head = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': bytes(f'Basic {userAndPass}', encoding='utf-8')}

        response = self.helper.send_http_request(url,method="POST",parameters=None,payload=payld,headers=head,cookies=None,verify=False,cert=None,timeout=self.http_timeout,use_proxy=None)

        return response

        

    def RefreshToken(self,url,refresh_token):

        self.helper.log_debug(f'Start RequestToken')
        
        payld = f'grant_type=refresh_token&refresh_token={refresh_token}'

        head = {'Content-Type': 'application/x-www-form-urlencoded'}

        response = self.helper.send_http_request(url,method="POST",parameters=None,payload=payld,headers=head,cookies=None,verify=False,cert=None,timeout=self.http_timeout,use_proxy=None)

        return response

