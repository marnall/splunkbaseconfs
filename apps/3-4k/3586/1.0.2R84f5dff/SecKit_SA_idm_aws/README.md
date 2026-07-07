# Security Kit #

##Identity Management AWS Components##
 ``SecKit_SA_idm_aws``

### Introduction ###

This purpose of this Splunk add on is to provide a tool for the generation of assets for AWS virtual compute instances supporting Splunk Enterprise Security.

### Pre Installation ###
* Ensure SecKit_TA_idm_common.spl has been installed and configured.
* Install the Splunk Addon for AWS on the enterprise search head
* Install the Splunk App for AWS on a forwarder and collect describe events

### Installation ###
* Install SecKit_TA_idm_aws.spl on the enterprise security search head
* Update the macro ``seckit_idm_aws_index`` with the proper index name for your AWS events
* Review search schedules and windows tune if needed for your environment.

### Configuration ###

Each step is optional, and can be executed incrementally as additional information is gathered for your environment. The most precise available value will be utilize.

* Review the calucated value of **bunit** in the assets list created if a better value can be calculated update the macro ``seckt_idm_aws_ec2_bunit_custom`` to provide the formula
* Review the calucated value of **owner** in the assets list created if a better value can be calculated update the macro ``seckt_idm_aws_ec2_owner_custom`` to provide the formula
* Review the calucated value of **priority** in the assets list created if a better value can be calculated update the macro ``seckt_idm_aws_ec2_priority_custom`` to provide the formula
* Review the calucated value of **dns** in the assets list created if additional values can be calculated update the macro ``seckt_idm_aws_ec2_dns_custom`` to provide the formula
* Review the calucated value of **ip** in the assets list created if additional values can be calculated update the macro ``seckt_idm_aws_ec2_ip_custom`` to provide the formula
* Review the calucated value of **category** in the assets list created if additional values can be calculated update the macro ``seckt_idm_aws_ec2_category_custom`` to provide the formula

## Scheduled Searches (Saved searches)

* ``seckit_idm_aws_pre_account_id_vpc_gen`` This search runs every two hours and updates the lookup ``seckit_idm_aws_pre_account_vpc_lookup`` containing all unique account IDs present in the event stream this lookup can be used to enrich the asset data for the purpose of categorization and prioritization
* ``seckit_idm_aws_assets_ec2_gen`` This search runs every 5 minutes and updates the lookup data used by ES Identity merge to populate the ES asset center.

## Support ##
Direct contact Community Support as best effort Ryan Faircloth rfarcloth@splunk.com

[Issue Tracker](https://bitbucket.org/SPLServices/seckit_sa_idm_aws/issues?status=new&status=open)

### Source ###
[bitbucket](https://bitbucket.org/SPLServices/seckit_sa_idm_aws)


### Blog ###

Follow me and seek more knowledge at <http://www.rfaircloth.com/2016/01/07/making-asset-data-useful-with-splunk-enterprise-security/>
