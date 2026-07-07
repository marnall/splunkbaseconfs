[<stanza name>]

action.crowdstrike_ioc_count = [0|1]
    * Enable action
    
action.crowdstrike_ioc_count.param.indicator_type = <string>
   * indicator_type here

action.crowdstrike_ioc_count.param.indicator_value = <string>
   * indicator_value here

action.crowdstrike_change_detection_state = [0|1]
    * Enable action
    
action.crowdstrike_change_detection_state.param.detection_id = <string>
   * detection_id here

action.crowdstrike_change_detection_state.param.detection_status = <string>
   * detection_status here

action.crowdstrike_ioc_upload = [0|1]
   * Enable action

action.crowdstrike_upload_ioc.param.indicator_type = <string>
   * indicator_type here

action.crowdstrike_upload_ioc.param.indicator_value = <string>
   * indicator_value here

action.crowdstrike_upload_ioc.param.policy = <string>
   * policy that should be enacted (detect or none)

action.crowdstrike_upload_ioc.param.share_level = <string>
   * share_level of indicator, default is red

action.crowdstrike_upload_ioc.param.expiration_days = <integer>
   * expiration_days of indicator, default is 30 days

action.crowdstrike_upload_ioc.param.description = <string>
   * description of indicator within 200 characters

action.crowdstrike_upload_ioc.param.source = <string>
   * source this indicator originated within 200 characters