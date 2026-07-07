JOB_BASE = {
    'job_desc': 'desc',
    'job_name': 'name',
    'job_status': 'status',
    'job_created_time': 'created_at',
    'job_updated_time': 'updated_at',
    'job_ran_by': 'verodin_user'
}

JOB_ACTION_BASE = {
    'ja_id': 'id',
    'ja_status': 'status',
    'blocked': 'blocked',
    'block_desc': 'blocked_desc',
    'detected': 'detected',
    'alerted': 'alerted',
    'ja_ended_at': 'ended_at',
    'ja_updated_at': 'updated_at',
    'ja_email_status': 'email_status',
    'ja_action_order': 'action_order',
    'ja_conversation': 'conversations',
    'ja_tags': 'tags',
    'ja_attacker_status': 'attacker_status',
}

JA_SOURCE_ACTOR = {
    'source_actor': 'name',
    'source_actor_ip': 'ip',
    'source_actor_hostname': 'hostname',
    'source_actor_fq_hostname': 'fq_hostname'
}

JA_DESTINATION_ACTOR = {
    'destination_actor': 'name',
    'destination_actor_ip': 'ip',
    'destination_actor_hostname': 'hostname',
    'destination_actor_fq_hostname': 'fq_hostname'
}

JA_BLOCKING_SECTECH = {
    'action_blocking_sectech_product': 'product',
    'action_blocking_sectech_vendor': 'vendor',
    'action_blocking_sectech_id': 'id'
}

ACTION_LIST = {
    'action_control_tags': 'control_tags',
    'action_verodin_tags': 'verodin_tags',
    'action_user_tags': 'user_tags',
    'action_src_dst_tags': 'src_destination_tags'
}

ACTION_DIMENTIONS = {
    'action_attack_vector': 'Attack Vector',
    'action_covert': 'Covert',
    'action_stage_of_attack': 'Stage of Attack',
    'action_attacker_location': 'Attacker Location',
    'action_os_platform': 'OS/Platform',
    'action_behavior_type': 'Behavior Type'
}

INTEGRATION_EVENT = {
    'sectech_event_id': 'id',
    'sectech_source_host': 'host',
    'event_match_type': 'match_type',
    'event_source_ip': 'src_ip',
    'event_source_port': 'src_port',
    'event_destination_ip': 'dest_ip',
    'event_destination_port': 'dest_port',
    'event_description': 'description',
    'event_computer': 'computer',
    'event_uid': 'uid',
    'event_host': 'host',
    'event_user': 'user',
    'event_url': 'url',
    'event_sig_id': 'sid',
    'event_email_recipient': 'email_recipient',
    'event_email_sender': 'email_sender',
    'event_email_subject': 'email_subject',
    'base_event_uids': 'base_event_uids',
    'event_start_time': 'start_time',
    'event_filehashes': 'filehashes',
    'event_raw_event': 'raw_event'
}

JAE_SECTECH_DEVICE = {
    'sectech_name': 'name',
    'sectech_vendor': 'vendor',
    'sectech_product': 'product',
    'sectech_prevention_enabled': 'prevention_enabled',
    'sectech_id': 'security_technology_id'
}

HOST_EVENT = {
    'sectech_event_id': 'id',
    'sectech_source_host': 'computer',
    'sectech_command': 'cmd',
    'sectech_source_log_file': 'src_log_file',
    'event_description': 'message',
    'event_computer': 'jae_src_host',
    'event_user': 'user'
}

HOST_JAE_SECTECH_DEVICE = {
    'sectech_name': 'name',
    'sectech_vendor': 'vendor',
    'sectech_product': 'product',
    'sectech_prevention_enabled': 'prevention_enabled',
    'sectech_id': 'security_technology_id'
}
