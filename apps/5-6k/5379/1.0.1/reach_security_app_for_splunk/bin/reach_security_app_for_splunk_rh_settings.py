
import reach_security_app_for_splunk_declare
import splunk.admin as admin
import splunk.rest as rest
import os

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import reach_search_execution_helper
import reach_logger_manager as log

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'auto_search',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'url',
        required=False,
        encrypted=False,
        default='https://api.reach.security/v1/splunk',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default='86400',
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ),
    field.RestField(
        'starts_from',
        required=True,
        encrypted=False,
        default="90",
        validator=None
    ),
    field.RestField(
        'products',
        required=True,
        encrypted=False,
        default='proofpoint_tap,pan_os,active_directory',
        validator=None
    ),
    field.RestField(
        'anonymize_fields',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'fields_to_anonymize',
        required=False,
        encrypted=False,
        default='ccAddresses{},cn,dest_hostname,directReports,displayName,distinguishedName,dvc_name,file_name,fromAddress{},givenName,headerFrom,headerReplyTo,mail,mailNickname,managedBy,managedObjects,manager,memberOf,name,proxyAddresses,recipient{},sAMAccountName,sender,sn,src_ip,toAddresses{},user,userPrincipalName',
        validator=None
    ),
    field.RestField(
        'result_fields',
        required=True,
        encrypted=False,
        default='product_name,_raw,_time,accountExpires,action,app,app:category,app:is_saas,app:is_sanctioned,app:subcategory,app_default_ports,badPasswordTime,badPwdCount,c,category,ccAddresses{},client_location,CN,cn,co,company,completelyRewritten,content_version,ContentType,countryCode,DC,dcName,department,departmentNumber,description,dest,dest_class,dest_hostname,dest_location,dest_name,dest_port,dest_translated_ip,dest_translated_port,dest_zone,direction,directReports,displayName,Disposition,distinguishedName,dvc_name,eventType,eventtype,file_name,file_sha_256,Filename,fromAddress{},givenName,headerFrom,headerReplyTo,host,http_category,http_method,impostorScore,l,lastLogon,lastLogonTimestamp,localPolicyFlags,location,lockoutTime,log_subtype,logonCount,logonHours,mail,mailNickname,malwareScore,managedBy,managedObjects,manager,memberOf,messageID,messageTime,misc,mS-DS-ConsistencyGuid,mS-DS-SourceAnchor,name,o,objectCategory,objectClass,objectGUID,operatingSystem,operatingSystemServicePack,operatingSystemVersion,OU,phishScore,physicalDeliveryOfficeName,PolicyRoutes,postalCode,primaryGroupID,proxyAddresses,pwdLastSet,quarantineFolder,quarantineRule,raw_category,recipient{},rule,sAMAccountName,SandboxStatus,sender,senderIP,server_ip,severity,signature,signature_id,sn,source_zone,spamScore,src_class,src_ip,src_location,src_port,src_translated_ip,src_translated_port,src_zone,st,streetAddress,sub_type,subject,Threat,threat,threat:category,threat:cve,threat:name,threat_category,threat_id,ThreatClassification,ThreatID,threatsInfoMap{}.campaignID,threatsInfoMap{}.classification,ThreatStatus,ThreatTime,ThreatType,ThreatUrl,title,toAddresses{},url,user,userAccountControl,userAccountPropertyFlag,userPrincipalName,vendor_action,whenChanged,whenCreated',
        validator=None
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'reach_security_app_for_splunk_settings',
    models=[
        model_proxy, 
        model_logging, 
        model_additional_parameters
    ],
)

class CustomSettingsHandler(ConfigMigrationHandler):
    """
    Custom setting handler handler
    """

    def __init__(self, *args, **kwargs):
        ConfigMigrationHandler.__init__(self, *args, **kwargs)

    def modify_scripted_input(self):
        """
        Enable/Disable the periodic scripted input on save
        """
        action = "enable" if int(self.payload.get('auto_search', 0)) else "disable"
        encoded_script_name = "%24SPLUNK_HOME%252Fetc%252Fapps%252Freach_security_app_for_splunk%252Fbin%252Freach_input_periodic_execution.py"
        logger = log.setup_logging('reach_periodic_execution', self.getSessionKey())
        interval =  int(86400) if self.payload.get('interval', 86400)=="" else int(self.payload.get('interval', 86400))
        reach_search_execution_helper.disable_enable_script(action, encoded_script_name, self.getSessionKey(), logger, interval=interval)

    def validate(self):
        """
        Check if the given value is valid.
        """
        auto_search = self.payload.get('auto_search')
        password = self.payload.get('password')

        if int(auto_search) and not password:
            msg = "Reach API Key is required when 'Automatic Search & Export' is enabled"
            raise admin.ArgValidationException(msg)

    def handleEdit(self, conf_info):
        """
        Handles the edit operation.
        """
        if self.payload.get('products'):
            self.validate()
            logger = log.setup_logging('reach_setup', self.getSessionKey())
            # Update the macro as per configuration
            products, status = reach_search_execution_helper.update_configured_macro(
                self.getSessionKey(), logger, self.payload['products'], self.payload.get('starts_from', 90))
            if not status:
                msg = "Selected sourcetype is not having any data in selected time range. Please configure the data collection"
                raise admin.ArgValidationException(msg)

        ConfigMigrationHandler.handleEdit(self, conf_info)

        if self.payload.get('interval', 86400)=="":
            conf_endpoint = "/servicesNS/nobody/{}/configs/conf-reach_security_app_for_splunk_settings/"\
                "additional_parameters".format(__file__.split(os.sep)[-3])
            try:
                rest.simpleRequest(conf_endpoint, method='POST', sessionKey=self.getSessionKey(), postargs={"interval": "86400"}, raiseAllErrors=True)
            except Exception as e:
                logger.error("Reach Error: Error while updating interval in "
                              "reach_security_app_for_splunk_settings.conf file. Error: {}".format(str(e)))

        if self.payload.get('products'):
            # Update scripted input
            self.modify_scripted_input()

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomSettingsHandler,
    )
