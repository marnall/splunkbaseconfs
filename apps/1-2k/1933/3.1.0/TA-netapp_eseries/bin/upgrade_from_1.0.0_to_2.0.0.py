import os
import io
import six.moves.configparser
from six.moves import range
from shutil import copyfile, move
from splunk.clilib.bundle_paths import make_splunkhome_path

path = os.path.abspath(__file__)
app_name = path.split('/')[-3] if '/' in path else path.split('\\')[-3]


def transition_inputs(app_name):
    """Transition Inputs."""
    if os.path.isfile(os.path.join(make_splunkhome_path(["etc", "apps", app_name, "local", "inputs.conf.bkp"]))) or \
            os.path.isfile(os.path.join(make_splunkhome_path(
                ["etc", "apps", app_name, "local", "ta_netapp_eseries_account.conf"]))):
        print("\nInputs are already configured!\n")
        return None

    inputs_config = six.moves.configparser.ConfigParser()
    inputs_conf = os.path.join(make_splunkhome_path(["etc", "apps", app_name, "local", "inputs.conf"]))
    inputs_stanzas = []

    bkp_path = os.path.join(make_splunkhome_path(["etc", "apps", app_name, "local", "inputs.conf.bkp"]))
    if os.path.isfile(inputs_conf):
        copyfile(inputs_conf, bkp_path)
        with io.open(inputs_conf, 'r', encoding='utf_8_sig') as inputconffp:
            inputs_config.readfp(inputconffp)
        inputs_stanzas = inputs_config.sections()

    else:
        return
    uniqueness = {}
    config_data = []
    stanza_prefix = "rest://ESeries"
    for stanza in inputs_stanzas:
        if stanza.startswith(stanza_prefix):
            web_proxy = inputs_config.get(stanza, 'endpoint').split('https://')[1].split('/devmgr')[0]
            system_id = inputs_config.get(stanza, 'host')
            username = inputs_config.get(stanza, 'auth_user')
            if web_proxy + "-" + username not in uniqueness.keys():
                uniqueness[web_proxy + "-" + username] = []
                config_data.append(
                    {
                        "name": "Proxy_Instance_" + username + "_" + web_proxy.split('.')[2]
                                + "_" + web_proxy.split('.')[3].split(':')[0],
                        "web_proxy": web_proxy,
                        "username": inputs_config.get(stanza, 'auth_user'),
                        "password": inputs_config.get(stanza, 'auth_password')

                    }
                )
            else:
                if system_id not in uniqueness[web_proxy + "-" + username]:
                    uniqueness[web_proxy + "-" + username].append(system_id)
                    new_section = "netapp_eseries://ESeries_" + system_id.split('-')[-1] + "_" + username
                    inputs_config.add_section(new_section)
                    inputs_config.set(new_section, 'interval', '60')
                    inputs_config.set(new_section, 'index', inputs_config.get(stanza, 'index'))
                    inputs_config.set(new_section, 'global_account',
                                      "Proxy_Instance_" + username + "_" + web_proxy.split('.')[2] + "_"
                                      + web_proxy.split('.')[3].split(':')[0])
                    inputs_config.set(new_section, 'system_id', system_id)
                    inputs_config.set(new_section, 'disabled', '1')

            inputs_config.remove_section(stanza)

        elif stanza.startswith("script"):
            inputs_config.remove_section(stanza)

    with open(inputs_conf, 'w') as f:
        inputs_config.write(f)

    return config_data


if __name__ == "__main__":
    try:
        # handling indexes.conf
        default_data = {}
        for folder_name in os.listdir(make_splunkhome_path(["etc", "apps", app_name])):
            if folder_name.startswith('default.old'):
                default_indexes_conf = make_splunkhome_path(["etc", "apps", app_name, folder_name, "indexes.conf"])
                default_indexes_config = six.moves.configparser.ConfigParser()
                with io.open(default_indexes_conf, 'r', encoding='utf_8_sig') as defaultindexesconffp:
                    default_indexes_config.readfp(defaultindexesconffp)

                default_data["homePath"] = default_indexes_config.get("eseries", "homePath")
                default_data["coldPath"] = default_indexes_config.get("eseries", "coldPath")
                default_data["thawedPath"] = default_indexes_config.get("eseries", "thawedPath")
                default_data["maxHotBuckets"] = default_indexes_config.get("eseries", "maxHotBuckets")

        local_indexes_conf = make_splunkhome_path(["etc", "apps", app_name, "local", "indexes.conf"])
        local_indexes_config = six.moves.configparser.ConfigParser()
        if os.path.exists(local_indexes_conf):
            with io.open(local_indexes_conf, 'r', encoding='utf_8_sig') as localindexesconffp:
                local_indexes_config.readfp(localindexesconffp)
            indexes_stanzas = local_indexes_config.sections()

            with open(default_indexes_conf, 'r') as default_indexes_fp:
                old_indexes_data = default_indexes_fp.read()

            if "eseries" not in indexes_stanzas:
                with open(local_indexes_conf, 'a') as local_indexes_fp:
                    local_indexes_fp.write('\n')
                    local_indexes_fp.write(old_indexes_data)
            else:
                for stanza in indexes_stanzas:
                    if stanza == "eseries":
                        default_params = ["homePath", "coldPath", "thawedPath", "maxHotBuckets"]
                        for param in default_params:
                            if not local_indexes_config.has_option("eseries", param):
                                local_indexes_config.set("eseries", param, default_data[param])
                        with open(local_indexes_conf, 'w') as f:
                            local_indexes_config.write(f)
                        break
        else:
            copyfile(default_indexes_conf, local_indexes_conf)

        # handling inputs and accounts
        flag = 1
        config_data = transition_inputs(app_name)
        if config_data:
            accounts_config = six.moves.configparser.ConfigParser()
            accounts_conf = os.path.join(
                make_splunkhome_path(["etc", "apps", app_name, "local", "ta_netapp_eseries_account.conf"]))

            open(accounts_conf, 'a').close()

            with io.open(accounts_conf, 'r', encoding='utf_8_sig') as accountconffp:
                accounts_config.readfp(accountconffp)

            for i in range(len(config_data)):
                new_section = config_data[i]["name"]
                accounts_config.add_section(new_section)
                accounts_config.set(new_section, 'web_proxy', config_data[i]["web_proxy"])
                accounts_config.set(new_section, 'verify_ssl', 0)
                accounts_config.set(new_section, 'username', config_data[i]["username"])
                accounts_config.set(new_section, 'password', "")

            with open(accounts_conf, 'w') as f:
                accounts_config.write(f)
        try:
            new_path = make_splunkhome_path(["etc", "apps", app_name, "bin", "old_files"])
            old_path = make_splunkhome_path(["etc", "apps", app_name, "bin"])
            if not os.path.exists(new_path):
                os.mkdir(new_path)
                files = ["Add_Array.sh", "add_array_to_proxy.sh", "create_splunk_inputs_for_array.sh",
                         "oauthlib-0.4.2-py2.7.egg", "requests_oauth-0.4.1-py2.7.egg",
                         "requests_oauth2-0.2.0-py2.7.egg", "requests_oauthlib-0.3.2-py2.7.egg",
                         "requests-2.0.0-py2.7.egg", "splunk_sdk-1.0.0-py2.7.egg", "uuid-1.30-py2.7.egg",
                         "authhandlers.py", "responsehandlers.py", "rest.py", "SANtricity_get_webproxy_details.py",
                         "tokens.py", "upgrade_from_0.9_to_1.0.py"]
                for file in files:
                    move(old_path + "/" + file, new_path)
        except Exception:
            print("Unable to trasfer old files to a designated folder.\nPlease check folder permissions.")

    except Exception as e:
        print("Unable to properly transit input configuration!\nPlease run the script again.\n" + str(e))
