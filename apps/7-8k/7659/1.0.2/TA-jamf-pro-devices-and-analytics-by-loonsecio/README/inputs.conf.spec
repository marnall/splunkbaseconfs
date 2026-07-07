[jamf_mac_devices://<name>]
jamf_pro_url = <yourServer>.jamfcloud.com
client_id = Client id for the API or Username
client_secret = Client Secret or the API Password
device_management_status = 
limit_inventory_time = Time limit for devices that haven't inventories. 0 = Unlimited, 1 = 1 day ago, 14 = 2 weeks
api_sections = 
meta_builder = Leave blank for the default value
application_patching = Select Patching Guidance Feeds, Empty list means don't include the data. If empty no patch guidance given
share_analytics = Shares the Analytics information, refer to documentation
vulnerability_detections = Add vulnerability information for the devices
vulnerability_requirements = Refer to https://loonsecio.com/resourcesVulnerabilities must match this criteriaEmpty list requires all