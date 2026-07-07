
import time
from xml.etree import ElementTree as ET

url = 'https://{}:{}/webconsole/APIController?'
Login = '<Request><Login><Username>{}</Username><Password>{}</Password></Login>{}</Request>'

time = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())

verif_host = '<Get><IPHost><Filter><key criteria="=" name="IPAddress">{}</key></Filter></IPHost></Get>'

host_list = '<Get><IPHost><Filter><key criteria="like" name="Name">{}</key></Filter></IPHost></Get>'

verif_group = '<Get><FirewallRuleGroup><Name/></FirewallRuleGroup></Get>'

add_gp = '<Set operation="add"><FirewallRuleGroup><Name>{}</Name><Description>Added by {}</Description><SecurityPolicyList><SecurityPolicy>{}</SecurityPolicy></SecurityPolicyList><Policytype>Network rule</Policytype></FirewallRuleGroup></Set>' 

existant_rules = '<Get><FirewallRule><Name/></FirewallRule></Get>'

gp_params = '<Get><FirewallRuleGroup><Filter><key name="Name" criteria="=">{}</key></Filter></FirewallRuleGroup></Get>'

rule_params = '<Get><FirewallRule><Filter><key name ="Name" criteria="=">{}</key></Filter></FirewallRule></Get>'  

def define_host(new_host, ipfamily, host ):
	fwhost = ET.Element('IPHost', transactionid="")
	ET.SubElement(fwhost, 'Name').text = new_host
	ET.SubElement(fwhost, 'IPFamily').text = ipfamily
	ET.SubElement(fwhost, 'HostType').text = "IP"
	ET.SubElement(fwhost, 'IPAddress').text = host
	defined_host = ET.tostring(fwhost, 'unicode')
	defined_host = '<Set operation="add">' + defined_host + '</Set>'
	print(defined_host)
	return defined_host


def update_rule(root, new_host, blk_type, host, ipfamily, user = None):
	
	if (root.find('.//FirewallRule/PolicyType').text) == "User":
		tag = 'UserPolicy'
	else:
		if (root.find('.//FirewallRule/PolicyType').text) == "Network":
			tag = 'NetworkPolicy'
	fwrule = ET.Element('FirewallRule', transactionid="")
	ET.SubElement(fwrule, 'Name').text = root.find('.//FirewallRule/Name').text
	previous_description = root.find('.//FirewallRule/Description').text
	if previous_description == None:
		ET.SubElement(fwrule, 'Description').text = "Last modification at:" + time + '.'
	else:
		if previous_description.find('.') == -1 :
			ET.SubElement(fwrule, 'Description').text = previous_description  + ". \nLast modification at:" + time + '.'
		else :
			ET.SubElement(fwrule, 'Description').text = previous_description[:((previous_description.index('.'))+1)]  + "\nLast modification at:" + time + '.'
	
	ET.SubElement(fwrule, 'IPFamily').text = root.find('.//FirewallRule/IPFamily').text
	ET.SubElement(fwrule, 'Status').text = root.find('.//FirewallRule/Status').text
	ET.SubElement(fwrule, 'Position').text =  "Top"  #root.find('.//FirewallRule/Position').text 
	ET.SubElement(fwrule, 'PolicyType').text = root.find('.//FirewallRule/PolicyType').text
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'Action').text = root.find('.//FirewallRule/'+tag+'/Action').text
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'LogTraffic').text = root.find('.//FirewallRule/'+tag+'/LogTraffic').text
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'Schedule').text = root.find('.//FirewallRule/'+tag+'/Schedule').text
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'SkipLocalDestined').text = root.find('.//FirewallRule/'+tag+'/SkipLocalDestined').text
	if tag == 'UserPolicy':
		
		ET.SubElement(ET.SubElement(fwrule, tag),
		              'MatchIdentity').text = root.find('.//FirewallRule/'+tag+'/MatchIdentity').text

		ET.SubElement(ET.SubElement(fwrule, tag),
		              'DataAccounting').text = root.find('.//FirewallRule/'+tag+'/DataAccounting').text
		ET.SubElement(ET.SubElement(fwrule, tag),
		              'ShowCaptivePortal').text = root.find('.//FirewallRule/'+tag+'/ShowCaptivePortal').text
		for i in range (len(root.findall('.//FirewallRule/'+tag+'/Identity/Member'))):
			ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
		              'Identity'), 'Member').text = root.find('.//FirewallRule/'+tag+'/Identity/Member').text
		
		if user not in [None, ""]:
			if blk_type == "user":
				ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag), 'Identity'), 'Member').text = user

	
	for net_tag_pre in ['SourceNetworks', 'DestinationNetworks' ]:
		for i in range (len(root.findall('.//FirewallRule/'+tag+'/'+net_tag_pre+'/Network'))):
			ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
		              net_tag_pre), 'Network').text = root.findall('.//FirewallRule/'+tag+'/'+net_tag_pre+'/Network')[i].text

	if blk_type in ["src_ip", "user"]:
		net_tag = 'SourceNetworks'
	else:
		net_tag = 'DestinationNetworks' 
	ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
	              net_tag), 'Network').text = new_host


	updated_rule = ET.tostring(fwrule, 'unicode')
	print(updated_rule)
	if host != None:	
		updated_rule = define_host(new_host, ipfamily, host ) + '<Set operation="update">' + updated_rule + '</Set>'
	else:
		updated_rule = '<Set operation="update">' + updated_rule + '</Set>'
	return updated_rule

def insert_in_group(root, rule_name, status = True):

	fwgroup =  ET.Element('FirewallRuleGroup', transactionid="")
	ET.SubElement(fwgroup, 'Name').text = root.find('.//FirewallRuleGroup/Name').text
	ET.SubElement(fwgroup, 'Description').text = root.find('.//FirewallRuleGroup/Description').text
	ET.SubElement(ET.SubElement(fwgroup, 'SecurityPolicyList'),
	              	'SecurityPolicy').text = rule_name
	for i in range (len (root.findall('.//FirewallRuleGroup/SecurityPolicyList/SecurityPolicy'))):
		if status:
			ET.SubElement(ET.SubElement(fwgroup, 'SecurityPolicyList'),
	              	'SecurityPolicy').text = root.findall('.//FirewallRuleGroup/SecurityPolicyList/SecurityPolicy')[i].text
		else:
			if root.findall('.//FirewallRuleGroup/SecurityPolicyList/SecurityPolicy')[i].text != rule_name:
				ET.SubElement(ET.SubElement(fwgroup, 'SecurityPolicyList'),
	              		'SecurityPolicy').text = root.findall('.//FirewallRuleGroup/SecurityPolicyList/SecurityPolicy')[i].text
			else:
				continue
	
	ET.SubElement(fwgroup, 'Policytype').text = root.find('.//FirewallRuleGroup/Policytype').text
	inserted_in_group = ET.tostring(fwgroup, 'unicode')
	inserted_in_group = '<Set operation="update">'  + inserted_in_group + '</Set>'
	return inserted_in_group


def define_rule(name, description, ipfamily, network, host, blk_type, position ="Top", first_rule=None, policytype = "Network", user = None):
	
	fwrule = ET.Element('FirewallRule', transactionid="")
	ET.SubElement(fwrule, 'Name').text = name
	ET.SubElement(fwrule, 'Description').text = description
	ET.SubElement(fwrule, 'IPFamily').text = ipfamily
	ET.SubElement(fwrule, 'Status').text = "Enable"
	ET.SubElement(fwrule, 'Position').text = position
	if position == "Before":
		ET.SubElement(ET.SubElement(fwrule, 'Before'),
	              'Name').text = first_rule
		if first_rule == None:
			raise Exception ("Missing 'first_rule' parameter in function 'define_rule'")

	if user not in [None, ""]:
		tag = 'UserPolicy'
		ET.SubElement(fwrule, 'PolicyType').text = "User"
	else:
		tag = 'NetworkPolicy'
		ET.SubElement(fwrule, 'PolicyType').text = policytype 
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'Action').text = "Drop"
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'LogTraffic').text = "Enable"
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'Schedule').text = "All The Time"
	ET.SubElement(ET.SubElement(fwrule, tag),
	              'SkipLocalDestined').text = "Disable"
	if user not in [None, ""]:
		if blk_type in [ "user"]:
			ET.SubElement(ET.SubElement(fwrule, tag),
				      'MatchIdentity').text = "Enable"
			ET.SubElement(ET.SubElement(fwrule, tag),
				      'DataAccounting').text = "Disable"
			ET.SubElement(ET.SubElement(fwrule, tag),
				      'ShowCaptivePortal').text = "Disable"
			ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
				      'Identity'), 'Member').text = user

	if blk_type in ["src_ip", "user"]:
		ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
              'SourceNetworks'), 'Network').text = network
	else:
		ET.SubElement(ET.SubElement(ET.SubElement(fwrule, tag),
              'DestinationNetworks'), 'Network').text = network
	defined_rule = ET.tostring(fwrule, 'unicode')
	if host != None:	
		defined_rule = define_host(network, ipfamily, host ) + '<Set operation="add">' + defined_rule + '</Set>'
	else:
		defined_rule = '<Set operation="add">' + defined_rule + '</Set>'
	print(defined_rule)
	return defined_rule


get_user = '<Get><User><Filter><key name="Username" criteria="=">{}</key></Filter></User></Get>'

def update_user(root, group):

    user_params = ET.Element('User', transactionid="")
    ET.SubElement(user_params, 'Username').text = root.find('.//User/Username').text
    ET.SubElement(user_params, 'Name').text = root.find('.//User/Name').text
    ET.SubElement(user_params, 'Description').text = root.find('.//User/Description').text
    ET.SubElement(user_params, 'UserType').text = root.find('.//User/UserType').text
    ET.SubElement(ET.SubElement(user_params, 'EmailList'),
                  'EmailID').text = root.find('.//User/EmailList/EmailID').text
    ET.SubElement(user_params, 'Group').text = group
    ET.SubElement(user_params, 'SurfingQuotaPolicy').text = root.find('.//User/SurfingQuotaPolicy').text
    ET.SubElement(user_params, 'AccessTimePolicy').text = root.find('.//User/AccessTimePolicy').text 
    ET.SubElement(user_params, 'DataTransferPolicy').text = root.find('.//User/DataTransferPolicy').text 
    ET.SubElement(user_params, 'QoSPolicy').text = root.find('.//User/QoSPolicy').text 
    ET.SubElement(user_params, 'SSLVPNPolicy').text = root.find('.//User/SSLVPNPolicy').text 
    ET.SubElement(user_params, 'ClientlessPolicy').text = root.find('.//User/ClientlessPolicy').text 
    ET.SubElement(user_params, 'Status').text = root.find('.//User/Status').text 
    ET.SubElement(user_params, 'L2TP').text = root.find('.//User/L2TP').text 
    ET.SubElement(user_params, 'PPTP').text = root.find('.//User/PPTP').text 
    ET.SubElement(user_params, 'CISCO').text = root.find('.//User/CISCO').text 
    ET.SubElement(user_params, 'QuarantineDigest').text = root.find('.//User/QuarantineDigest').text 
    ET.SubElement(user_params, 'MACBinding').text = root.find('.//User/MACBinding').text 
    ET.SubElement(user_params, 'LoginRestriction').text = root.find('.//User/LoginRestriction').text 
    ET.SubElement(
        user_params, 'ScheduleForApplianceAccess').text = root.find('.//User/ScheduleForApplianceAccess').text 
    ET.SubElement(
        user_params, 'LoginRestrictionForAppliance').text = root.find('.//User/LoginRestrictionForAppliance').text 
    ET.SubElement(user_params, 'IsEncryptCert').text = root.find('.//User/IsEncryptCert').text 
    ET.SubElement(
        user_params, 'SimultaneousLoginsGlobal').text = root.find('.//User/SimultaneousLoginsGlobal').text 
    
    updated_user = ET.tostring(user_params, 'unicode')
    updated_user = '<Set operation="update">'  + updated_user + '</Set>'
    print (updated_user)
    return updated_user

