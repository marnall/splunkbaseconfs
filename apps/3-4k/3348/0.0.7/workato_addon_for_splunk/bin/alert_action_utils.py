import fix_path

callback_search_param = 'action.workato.param.callback_urls'
workato_alert_action = 'action.workato'

def has_workato_alert_action(saved_search):
    if workato_alert_action in saved_search.content:
        if saved_search[workato_alert_action] == '1':
            return True
    return False

def iterate_callbacks_from_string(s):
    for v in s.split('|'):
        v=v.strip()
        if v:
            yield v

def iterate_callbacks(saved_search):
    if callback_search_param in saved_search.content:
        callbacks = saved_search[callback_search_param]
        for v in iterate_callbacks_from_string(callbacks):
            yield v

def get_callback_count(saved_search):
    cnt = 0
    for callback in iterate_callbacks(saved_search):
        cnt += 1
    return cnt

def add_callback(saved_search, callback_url):
    callbacks = list(iterate_callbacks(saved_search))
    if callback_url in callbacks:
        raise Exception('url already registered')
    callbacks.append(callback_url)
    kwargs = {
        "actions": "workato",
        callback_search_param: '|'.join(callbacks),
        }
    saved_search.update(**kwargs)

def remove_callback(saved_search, callback_url):
    callbacks = list(iterate_callbacks(saved_search))
    if callback_url in callbacks:
        callbacks.remove(callback_url)
        kwargs = {
            "actions": "workato",
            callback_search_param: '|'.join(callbacks),
            }
        saved_search.update(**kwargs)
