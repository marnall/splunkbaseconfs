
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
BASE = 'https://image.thum.io/get/width/1200/crop/3000/auth/6358-aae1b5601b78f4e3e90fd4ed5c22492f/'

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # server = definition.parameters.get('server', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # dashboard_name = definition.parameters.get('dashboard_name', None)
    # path = definition.parameters.get('path', None)
    # fromaddr = definition.parameters.get('fromaddr', None)
    # password_of_mail = definition.parameters.get('password_of_mail', None)
    # toaddr = definition.parameters.get('toaddr', None)
    # subject_of_email = definition.parameters.get('subject_of_email', None)
    # body = definition.parameters.get('body', None)
    # filename = definition.parameters.get('filename', None)
    pass

def collect_events(helper, ew):
    server = str(helper.get_arg('server'))
    username = str(helper.get_arg('username'))
    password = str(helper.get_arg('password'))
    dashboard_name = str(helper.get_arg('dashboard_name'))
    path = str(helper.get_arg('path'))
    fromaddr = str(helper.get_arg('fromaddr'))
    password_of_mail = str(helper.get_arg('password_of_mail'))
    toaddr = str(helper.get_arg('toaddr'))
    subject_of_email = str(helper.get_arg('subject_of_email'))
    body = str(helper.get_arg('body'))
    filename = str(helper.get_arg('filename'))
    url="http://"+server+":8000/en-US/account/insecurelogin?return_to=%2Fen-US%2Fapp%2Fsearch%2F"+dashboard_name+"?loginType=splunk&username="+username+"&password="+password+"&full_page=true"
    response = requests.get(BASE + url, stream=True)
    if response.status_code == 200:
        with open(path, 'wb') as file:
            for chunk in response:
                file.write(chunk)
    
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject_of_email
    msg.attach(MIMEText(body, 'plain'))
    attachment = open(path,"rb")
    p = MIMEBase('application', 'octet-stream')
    p.set_payload((attachment).read())
    encoders.encode_base64(p)
    p.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    msg.attach(p)

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()

# Authentication
    s.login(fromaddr,password_of_mail)
    text = msg.as_string()
    s.sendmail(fromaddr, toaddr, text)
    s.quit()
    
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_server = helper.get_arg('server')
    opt_username = helper.get_arg('username')
    opt_password = helper.get_arg('password')
    opt_dashboard_name = helper.get_arg('dashboard_name')
    opt_path = helper.get_arg('path')
    opt_fromaddr = helper.get_arg('fromaddr')
    opt_password_of_mail = helper.get_arg('password_of_mail')
    opt_toaddr = helper.get_arg('toaddr')
    opt_subject_of_email = helper.get_arg('subject_of_email')
    opt_body = helper.get_arg('body')
    opt_filename = helper.get_arg('filename')
    # In single instance mode, to get arguments of a particular input, use
    opt_server = helper.get_arg('server', stanza_name)
    opt_username = helper.get_arg('username', stanza_name)
    opt_password = helper.get_arg('password', stanza_name)
    opt_dashboard_name = helper.get_arg('dashboard_name', stanza_name)
    opt_path = helper.get_arg('path', stanza_name)
    opt_fromaddr = helper.get_arg('fromaddr', stanza_name)
    opt_password_of_mail = helper.get_arg('password_of_mail', stanza_name)
    opt_toaddr = helper.get_arg('toaddr', stanza_name)
    opt_subject_of_email = helper.get_arg('subject_of_email', stanza_name)
    opt_body = helper.get_arg('body', stanza_name)
    opt_filename = helper.get_arg('filename', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
