# encoding = utf-8

import os
import sys
import time
import datetime
import csv
import json

'''

# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    client_id = definition.parameters.get('client_id', None)
    client_secret = definition.parameters.get('client_secret', None)
    pass


def collect_events(helper, ew):

    splunk_home = os.getenv('SPLUNK_HOME')
    subscription_id = helper.get_arg('subscription_id')
    tenant_id = helper.get_arg('tenant_id')
    offer_durable_id = helper.get_arg('offer_durable_id')
    client_id = helper.get_arg('client_id')
    client_secret = helper.get_arg('client_secret')

    currency = helper.get_arg('currency')
    locale = helper.get_arg('locale')
    azure_region = helper.get_arg('azure_region')

    method = "GET"


    access_token_url = " https://login.microsoftonline.com/" + tenant_id +"/oauth2/token"
    access_token_headers = {"Content-Type" : "application/x-www-form-urlencoded"}
    access_token_body = "grant_type=client_credentials&client_id=" + client_id + "&client_secret=" + client_secret + "&resource=https://management.core.windows.net/"

    token_response = helper.send_http_request(access_token_url, method, parameters=None, payload=access_token_body, headers=access_token_headers, cookies=None, verify=True, cert=None,timeout=None, use_proxy=True)

    token_response_status = token_response.status_code
    token_response_json = json.loads(json.dumps(token_response.json()))

    #helper.log_info("token response json: " + json.dumps(token_response.json()))

    access_token = token_response_json["access_token"]

    prices_url = "https://management.azure.com/subscriptions/" + subscription_id + "/providers/Microsoft.Commerce/RateCard?api-version=2016-08-31-preview&%24filter=OfferDurableId+eq+'" + offer_durable_id + "'+and+Currency+eq+'" + currency + "'+and+Locale+eq+'" + locale + "'+and+RegionInfo+eq+'" + azure_region + "'"
    prices_headers = {"Authorization" : "Bearer " + access_token}

    prices_response = helper.send_http_request(prices_url, method, parameters=None, payload=None, headers=prices_headers, cookies=None, verify=True, cert=None,timeout=None, use_proxy=True)

    prices_response_status = prices_response.status_code
    prices_response_json = json.loads(json.dumps(prices_response.json()))
    disks_json = {"Meterios" : []}

    diskoutput = [['type', 'tier', 'max_size', 'region', 'location', 'rate', 'currency']]
    ipoutput = [['type', 'sku', 'rate', 'currency']]
    
    for meter in prices_response_json["Meters"]:
        # get disk prices - PRICE PER MONTH
        if meter["MeterSubCategory"] == "Premium SSD Managed Disks" or meter["MeterSubCategory"] == "Standard SSD Managed Disks" or meter["MeterSubCategory"] == "Standard HDD Managed Disks":
            disk_type_meter = meter["MeterName"]
            meter_region = meter["MeterRegion"]
            meter_rate = meter["MeterRates"]["0"]
            max_disk_size = "N/A"
            location = "N/A"
            if meter["MeterSubCategory"] == "Premium SSD Managed Disks":
                disk_tier = "Premium_LRS"
                if disk_type_meter == "P4 LRS Disk":
                    max_disk_size = "32"
                    disk_type = "P4"
                elif disk_type_meter == "P6 LRS Disk":
                    max_disk_size = "64"
                    disk_type = "P6"
                elif disk_type_meter == "P10 LRS Disk":
                    max_disk_size = "128"
                    disk_type = "P10"
                elif disk_type_meter == "P15 LRS Disk":
                    max_disk_size = "256"
                    disk_type = "P15"
                elif disk_type_meter == "P20 LRS Disk":
                    max_disk_size = "512"
                    disk_type = "P20"
                elif disk_type_meter == "P30 LRS Disk":
                    max_disk_size = "1024"
                    disk_type = "P30"
                elif disk_type_meter == "P40 LRS Disk":
                    max_disk_size = "2048"
                    disk_type = "P40"
                elif disk_type_meter == "P50 LRS Disk":
                    max_disk_size = "4096"
                    disk_type = "P50"
                elif disk_type_meter == "P60 LRS Disk":
                    max_disk_size = "8192"
                    disk_type = "P60"
                elif disk_type_meter == "P70 LRS Disk":
                    max_disk_size = "16384"
                    disk_type = "P70"
                elif disk_type_meter == "P80 LRS Disk":
                    max_disk_size = "32767"
                    disk_type = "P80"
            if meter["MeterSubCategory"] == "Standard SSD Managed Disks":
                disk_tier = "StandardSSD_LRS"
                if disk_type_meter == "E4 Disks":
                    max_disk_size = "32"
                    disk_type = "E4"
                elif disk_type_meter == "E6 Disks":
                    max_disk_size = "64"
                    disk_type = "E6"
                elif disk_type_meter == "E10 Disks":
                    max_disk_size = "128"
                    disk_type = "E10"
                elif disk_type_meter == "E15 Disks":
                    max_disk_size = "256"
                    disk_type = "E15"
                elif disk_type_meter == "E20 Disks":
                    max_disk_size = "512"
                    disk_type = "E20"
                elif disk_type_meter == "E30 Disks":
                    max_disk_size = "1024"
                    disk_type = "E30"
                elif disk_type_meter == "E40 Disks":
                    max_disk_size = "2048"
                    disk_type = "E40"
                elif disk_type_meter == "E50 Disks":
                    max_disk_size = "4096"
                    disk_type = "E50"
                elif disk_type_meter == "E60 Disks":
                    max_disk_size = "8192"
                    disk_type = "E60"
                elif disk_type_meter == "E70 Disks":
                    max_disk_size = "16384"
                    disk_type = "E70"
                elif disk_type_meter == "E80 Disks":
                    max_disk_size = "32767"
                    disk_type = "E80"
            if meter["MeterSubCategory"] == "Standard HDD Managed Disks":
                disk_tier = "Standard_LRS"
                if disk_type_meter == "S4 Disks":
                    max_disk_size = "32"
                    disk_type = "S4"
                elif disk_type_meter == "S6 Disks":
                    max_disk_size = "64"
                    disk_type = "S6"
                elif disk_type_meter == "S10 Disks":
                    max_disk_size = "128"
                    disk_type = "S10"
                elif disk_type_meter == "S15 Disks":
                    max_disk_size = "256"
                    disk_type = "S15"
                elif disk_type_meter == "S20 Disks":
                    max_disk_size = "512"
                    disk_type = "S20"
                elif disk_type_meter == "S30 Disks":
                    max_disk_size = "1024"
                    disk_type = "S30"
                elif disk_type_meter == "S40 Disks":
                    max_disk_size = "2048"
                    disk_type = "S40"
                elif disk_type_meter == "S50 Disks":
                    max_disk_size = "4096"
                    disk_type = "S50"
                elif disk_type_meter == "S60 Disks":
                    max_disk_size = "8192"
                    disk_type = "S60"
                elif disk_type_meter == "S70 Disks":
                    max_disk_size = "16384"
                    disk_type = "S70"
                elif disk_type_meter == "S80 Disks":
                    max_disk_size = "32767"
                    disk_type = "S80"
            if meter_region == "UK South":
                location = "uksouth"
            elif meter_region == "EU West":
                location = "westeurope"
            if "Snapshots" not in disk_type_meter:
                diskoutput.append([disk_type, disk_tier, max_disk_size, meter_region, location, meter_rate, currency])
        # get ip prices - PRICE PER HOUR
        if meter["MeterSubCategory"] == "IP Addresses":
            ip_meter_name = meter["MeterName"]
            meter_region = meter["MeterRegion"]
            ip_type = "N/A"
            ip_sku = "N/A`"
            if ip_meter_name == "Basic IPv4 Static Public IP":
                ip_type = "Static"
                ip_sku = "Basic"
            elif ip_meter_name == "Standard IPv4 Static Public IP":
                ip_type = "Static"
                ip_sku = "Standard"
            elif ip_meter_name == "Global Static Public IP":
                ip_type = "Static"
                ip_sku = "Global"
            elif ip_meter_name == "Global IPv4 Static Public IP":
                ip_type = "Static"
                ip_sku = "Global"
            elif ip_meter_name == "Basic IPv4 Dynamic Public IP":
                ip_type = "Dynamic"
                ip_sku = "Basic"
            meter_rate = meter["MeterRates"]["0"]
            if "US Gov" not in meter_region and "Remap" not in ip_meter_name:
                ipoutput.append([ip_type, ip_sku, meter_rate, currency])
                

    print('Writing volumes csv...')
    azure_volume_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'azure_volumeprices.csv')
    with open(azure_volume_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(diskoutput)
    csvFile.close()
    print('Finished writing volumes csv.')
    
    print('Writing ip csv...')
    azure_ip_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'azure_ipprices.csv')
    with open(azure_ip_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(ipoutput)
    csvFile.close()
    print('Finished writing ip csv.')
