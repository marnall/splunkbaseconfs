import ta_netapp_eseries_declare  # noqa:F401
from netapp_connect import NetAppConnection
import netapp_eseries_utility as utility
import splunk.entity as entity


def validate_input(helper, definition):
    """Validate Input."""
    pass


def collect_events(helper, ew):
    """Collect Events."""
    global_account_dict = helper.get_arg('global_account')
    web_proxy = global_account_dict["web_proxy"]
    username = global_account_dict["username"]
    password = global_account_dict["password"]
    verify_ssl = global_account_dict["verify_ssl"]
    ip1 = helper.get_arg('ip1')
    ip2 = helper.get_arg('ip2')
    register_password = helper.get_arg('register_password')
    index = helper.get_arg('index')
    name = helper.get_input_stanza_names()
    my_app = helper.get_app_name()
    entities = entity.getEntities(
        ['admin', 'passwords'],
        namespace=my_app, owner='nobody',
        sessionKey=helper.context_meta.get("session_key"),
        search=my_app
    )
    proxy_settings = utility.getProxySettings(my_app, entities)

    if 'verify_ssl' not in global_account_dict:
        verify_ssl = utility.get_verify_ssl()
    else:
        verify_ssl = False if verify_ssl in ["0", "False", "F", "false", "f"] else True

    netapp_connection = NetAppConnection(web_proxy, username, password, proxy_settings, verify_ssl)

    system_id = utility.registerArray(ip1, ip2, register_password, netapp_connection)
    helper.log_info("NetApp ESeries: Array with ID: " + system_id + " is registered in the web proxy.")
    helper.log_info("NetApp ESeries: Started monitoring the array...")
    utility.monitorArray(helper, ew, index, system_id, netapp_connection)
    helper.log_info("NetApp ESeries: Finished monitoring the array")

    check_point = str(name) + str(system_id)
    state = helper.get_check_point(check_point)

    # Executing saved searches on first time enabling the mod input
    if not state:
        helper.log_info("NetApp ESeries: Running Savedsearches...")
        try:
            utility.run_saved_searches(index, helper.context_meta['session_key'])
        except Exception as e:
            helper.log_error("NetApp Eseries Error: Error while executing the savedsearches : {}".format(str(e)))
        else:
            helper.log_info("NetApp ESeries: Finished Running Savedsearches")
            state = {"savedsearch_ran": 1}
            helper.save_check_point(check_point, state)
