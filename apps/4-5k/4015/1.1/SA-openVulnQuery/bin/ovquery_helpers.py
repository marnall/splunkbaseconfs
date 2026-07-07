from splunk import entity

def decrypt_username_password(confDict, app_name, session_key):
    entities = entity.getEntities(
        ['admin', 'passwords'],
        namespace=app_name,
        owner='nobody',
        sessionKey=session_key,
    )
    for i, c in entities.items():
        return c['username'], c['clear_password']

