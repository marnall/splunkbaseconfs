
# encoding = utf-8

import os
import sys
import time
import datetime
import platform
import requests
from selenium import webdriver
path = sys.path[1]


if platform.system() == 'Windows':
    path = os.path.join(path,"chromedriver.exe")

if platform.system() == 'Linux':
    path = os.path.join(path,"chromedriver.linux")

if platform.system() == 'Darwin':
    path = os.path.join(path,"chromedriver.mac")

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

def get(helper, ew, symbol):

    uri = 'http://charts.kitco.com/KitcoCharts/index.jsp?Symbol=' + symbol + '&Currency=USD'
    driver = None
    driver = webdriver.Chrome(executable_path=path)
    driver.get(uri)
    
    driver.find_element_by_class_name("buttonA").click()
    

    for p_element in driver.find_elements_by_xpath("//div[@id='div_info_chart']/table/tbody/tr/td/span[@id='bid']"):
        bid=p_element.text
    for p_element in driver.find_elements_by_xpath("//div[@id='div_info_chart']/table/tbody/tr/td/span[@id='ask']"):
        ask=p_element.text
    
    if 'bid' not in locals():
        bid="-"
    if 'ask' not in locals():
        ask="-"
    
    data='{"symbol":"' + symbol + '", "bid":' + bid + ', "ask":' + ask + '}'
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # precious_metals = definition.parameters.get('precious_metals', None)
    # base_metals = definition.parameters.get('base_metals', None)
    pass

def collect_events(helper, ew):
    opt_precious_metals = helper.get_arg('precious_metals')
    opt_base_metals = helper.get_arg('base_metals')
    opt_currencies = helper.get_arg('currencies')
    opt_other = helper.get_arg('other')

    if len(opt_precious_metals) > 0:
        for precious_metal in opt_precious_metals:
            get(helper, ew, precious_metal)
    if len(opt_base_metals) > 0:
        for base_metal in opt_base_metals:
            get(helper, ew, base_metal)
    if len(opt_currencies) > 0:
        for currency in opt_currencies:
            get(helper, ew, currency)
    if len(opt_other) > 0:
        for other in opt_other:
            get(helper, ew, other)
    

    