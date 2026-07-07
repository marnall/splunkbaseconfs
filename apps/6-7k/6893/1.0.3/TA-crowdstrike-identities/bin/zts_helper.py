

def zts_logger(msg, action, event_type, stanza, hostname, **kwargs):
    """ To help with consistent logging format
    :param msg: message for log
    :param action: event outcome (started|success|failure|aborted)
    :param event_type: type of event
    :param stanza: stanza for event
    :param hostname: hostname of event
    :param kwargs: any kv pair
    
    zts_logger(
            msg='message',
            action='success',
            event_type=event_type,
            stanza=stanza,
            hostname=hostname
        )
    """
    event_log = f'msg="{msg}", action="{action}", event_type="{event_type}", input_stanza="{stanza}", hostname="{hostname}"'
    for key, value in kwargs.items():
        event_log = event_log + f', {key}="{value}"'

    return event_log
