'''
Utility Functions used across all the API input scripts
'''

base_api_seam_url = "https://bluejeans.com/seamapi"
base_api_indigo_url = "https://indigo-api.bluejeans.com"

def create_checkpoint_key(inputname, timestampKey):
    return "{0}_{1}".format(inputname, timestampKey)

def get_checkpoint(helper, timestampKey):
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()
    key = create_checkpoint_key(inputname, timestampKey)

    checkpoint_value = False
    try:
        checkpoint_value = helper.get_check_point(key)
        helper.log_debug("input_type={0:s} input={1:s} message='Successfully retrieved checkpoint for key:{2:s}'".format(inputtype, inputname, key))
    except Exception as e:
        helper.log_error("input_type={0:s} input={1:s} message='Unable to retrieve checkpoint for key: {2:s} with error {3:s}'".format(inputtype, inputname, key, str(e)))
        pass
    return checkpoint_value

def save_checkpoint(helper, timestampKey, value):
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()
    key = create_checkpoint_key(inputname, timestampKey)

    try:
        helper.save_check_point(key, value)
        helper.log_debug("input_type={0:s} input={1:s} message='Storing checkpoint at key:{2:s}'".format(inputtype, inputname, key))
    except Exception as e:
        helper.log_error("input_type={0:s} input={1:s} message='Error while saving checkpoint at key:{2:s}'".format(inputtype, inputname, key))

def save_last_pushed_date(helper, epochTimestamp):
    inputtype = helper.get_input_type()
    key_name = str(inputtype) + "_last_pushed_date"
    helper.save_check_point(key_name, epochTimestamp)

def get_enterprise_profile(helper, user_id, user_access_token):
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()

    method = 'GET'
    parameters = {
        'access_token': user_access_token
    }
    user_enterprise_profile_url = base_api_seam_url + '/v1/user/' + str(user_id) + '/enterprise_profile'

    response = helper.send_http_request(user_enterprise_profile_url, method, parameters=parameters, payload=None, headers={}, cookies=None, verify=True, cert=None, timeout=50, use_proxy=False)
    r_status = response.status_code

    if r_status is not 200:
        helper.log_error("input_type={0:s} input={1:s} message='Get User Enterprise Profile API failed.' status_code={2:d}".format(inputtype, inputname,r_status))
        return { 'user_enterprise_id': None }
    else:
        helper.log_debug("input_type={0:s} input={1:s} message='Successfuly retrieved user enterprise Profile' status_code={2:d}".format(inputtype, inputname, r_status))

        obj = response.json()
        user_enterprise_id = obj['enterprise']
        return { 'user_enterprise_id': user_enterprise_id}

def generate_user_access_token(helper, username, password):
    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()

    method = 'POST'
    generate_access_token_url = base_api_seam_url + '/oauth2/token'
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password
    }

    response = helper.send_http_request(generate_access_token_url, method, parameters={}, payload=payload, headers={}, cookies=None, verify=True, cert=None, timeout=10, use_proxy=False)

    r_status = response.status_code

    if r_status is not 200:
        helper.log_error("input_type={0:s} input={1:s} message='Oauth2 Token API failed.' status_code={2:d}".format(inputtype, inputname,r_status))
        return { 'user_id': None, 'user_access_token': None }
    else:
        helper.log_debug("input_type={0:s} input={1:s} message='Successfuly generated user access token' status_code={2:d}".format(inputtype, inputname, r_status))

        obj = response.json()
        user_access_token = obj['access_token']
        user_id = obj['scope']['user']
        helper.save_check_point("access_token", user_access_token)
        return { 'user_id': user_id, 'user_access_token': user_access_token }

#check if token is valid and stored 
def access_token_storage(helper):
    # Retrieve runtime variables
    bjn_username = helper.get_arg('bluejeans_creds')['username']
    bjn_password = helper.get_arg('bluejeans_creds')['password']
    token = helper.get_check_point("access_token")
    method = 'GET'
    token_validation_url = base_api_seam_url + '/oauth2/tokenInfo?access_token=' + str(token)
    response = helper.send_http_request(token_validation_url, method, parameters={}, payload={}, headers={}, cookies=None, verify=True, cert=None, timeout=10, use_proxy=False)
    status_code = response.status_code
    if status_code is not 200: 
        helper.log_error(" message='*******Oauth2 Token API failed.**********' status_code={0:d}".format(status_code))
        return generate_user_access_token(helper, bjn_username, bjn_password)
    else:
        helper.log_debug(" message='*******Token EXISTS.**********' status_code={0:d}".format(status_code))
        return { 'user_id': response.json()['user'], 'user_access_token': token }