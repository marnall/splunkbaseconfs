import os
import io
import six.moves.configparser
from splunk.clilib.bundle_paths import make_splunkhome_path


def conf_stanzas(my_app, file):
    """Get Conf file stanzas."""
    conf_parser = six.moves.configparser.ConfigParser()
    conf = os.path.join(make_splunkhome_path(["etc", "apps", my_app, "local", file]))
    stanzas = []
    if os.path.isfile(conf):
        with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
            conf_parser.readfp(conffp)
        stanzas = conf_parser.sections()
    return conf, conf_parser, stanzas


path = os.path.abspath(__file__)
app_name = path.split('/')[-3] if '/' in path else path.split('\\')[-3]

inputs_conf, inputs_config, input_stanzas = conf_stanzas(app_name, "inputs.conf")
accounts_conf, accounts_config, acc_stanzas = conf_stanzas(app_name, "ta_netapp_eseries_account.conf")

for stanza in input_stanzas:
    if accounts_config.get(inputs_config.get(stanza, "global_account"), "password"):
        inputs_config.set(stanza, "disabled", "0")

with open(inputs_conf, 'w') as f:
    inputs_config.write(f)
