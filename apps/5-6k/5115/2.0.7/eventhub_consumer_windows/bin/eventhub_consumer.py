import asyncio
import sys

from xml.dom import minidom
from xml.sax import saxutils

from azure.storage.blob import BlockBlobService
from azure.eventprocessorhost import (
    EventProcessorHost,
    EventHubConfig,
    EPHOptions
)
from azure.eventhub import EventHubClientAsync
from uamqp.errors import AMQPConnectionError

from constants import APP_NAME, PASSWORD_MASK
from eventhub import EventHub
from logger import logger
from splunk_event_processor import SplunkEventProcessor
from splunk_service import SplunkService
from storage import StorageManagerFactory

script_input = sys.stdin.read()

SCHEME = """<scheme>
    <title>Azure EventHub Consumer</title>
    <description>Get data from a configured Azure EventHub.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>simple</streaming_mode>

    <endpoint>
        <args>
            <arg name="name">
                <title>Connection Name</title>
                <description>Splunk identifier for the new EventHub connection.</description>
            </arg>

            <arg name="eventhub_namespace">
                <title>EventHub Namespace</title>
                <description>The Azure namespace the EventHub instance belongs to.</description>
            </arg>

            <arg name="eventhub_name">
                <title>EventHub Name</title>
                <description>The name of the Azure EventHub to retrieve data from.</description>
            </arg>

            <arg name="sas_policy">
                <title>SAS Policy</title>
                <description>The SAS policy name.</description>
            </arg>

            <arg name="sas_key">
                <title>SAS Key</title>
                <description>The SAS credential key.</description>
            </arg>

            <arg name="storage_type">
                <title>Storage Type</title>
                <description>Storage type used for EventHub checkpoint data.</description>
            </arg>

            <arg name="blob_storageaccount">
                <title>Azure Blob Storage Account</title>
                <description>Azure Blob storage account name. Required when using Blob storage.</description>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="blob_storageaccount_key">
                <title>Azure Blob Storage Account Key</title>
                <description>Azure Blob storage account credential key. Required when using Blob storage.</description>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="blob_container">
                <title>Azure Blob Container</title>
                <description>Azure Blob storage container. Required when using Blob storage.</description>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="consumer_group">
                <title>Consumer Group</title>
                <description>Azure EventHub consumer group.</description>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="prefetch">
                <title>Prefetch Count</title>
                <description>Number of messages to pre-fetch from each partition.</description>
                <data_type>number</data_type>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="timeout">
                <title>Timeout</title>
                <description>Azure EventHub read timeout (in seconds).</description>
                <data_type>number</data_type>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="run_duration">
                <title>Run Duration</title>
                <description>Number of seconds the Event Processor will run for. Should generally be less than the input interval.</description>
                <data_type>number</data_type>
                <required_on_create>false</required_on_create>
            </arg>

        </args>
    </endpoint>
</scheme>
"""


async def wait_and_close(host, duration):
    """
    Run EventProcessorHost for duration seconds then shutdown.
    """
    await asyncio.sleep(duration)
    await host.close_async()


class Consumer:

    def __init__(self):
        conf = get_config()
        self.eventhub = EventHub(**conf)
        self.input_name = conf.get('name')
        self.checkpoint_dir = conf.get('checkpoint_dir')
        self.splunk = SplunkService(session_key=self.get_session_key(), app=APP_NAME)
        self.mask_credentials()

    @staticmethod
    def get_session_key():
        doc = minidom.parseString(script_input)
        node = doc.documentElement.getElementsByTagName('session_key')[0]
        if node and node.firstChild and \
            node.firstChild.nodeType == node.firstChild.TEXT_NODE:
                return node.firstChild.data
        return None

    def mask_credentials(self):
        # the first time we run a new input, we need to mask the plaintext password
        # because modular input configuration doesn't allow us to create passwords.conf
        # entries natively
        update_conf = self.eventhub.as_dict()
        update = False
        for c in [
            {
                'username': self.eventhub.sas_policy, 'password': self.eventhub.sas_key, 'realm': self.eventhub.realm,
                'pkey': 'sas_key'  # needed to mask the password in inputs.conf
            },
            {
                'username': self.eventhub.storageaccount, 'password': self.eventhub.blob_key, 'realm': self.eventhub.blob_realm,
                'pkey': 'blob_storageaccount_key'
            }
        ]:
            if c['username'] and c['password'] and c['password'] != PASSWORD_MASK:
                self.splunk.store_credentials(c['username'], c['password'], realm=c['realm'])
                update_conf[c['pkey']] = PASSWORD_MASK
                update = True
        if update:
            self.splunk.mask_credentials(self.input_name, **update_conf)

    def execute(self):
        loop = asyncio.get_event_loop()
        try:
            sas_key = self.splunk.get_credentials(self.eventhub.sas_policy, realm=self.eventhub.realm)
            eventhub_config = EventHubConfig(
                sb_name=self.eventhub.namespace,
                eh_name=self.eventhub.event_hub,
                policy=self.eventhub.sas_policy,
                sas_key=sas_key.content.clear_password,
                consumer_group=self.eventhub.consumer_group
            )
            opts = EPHOptions()
            opts.prefetch_count = int(self.eventhub.prefetch)
            opts.max_batch_size = int(self.eventhub.prefetch)
            opts.receive_timeout = int(self.eventhub.timeout)
            kwargs = {}
            if self.eventhub.storage and self.eventhub.storage == 'blob':
                if not self.eventhub.container:
                    raise ValueError("No container name specified for blob storage!")
                if not self.eventhub.storageaccount:
                    raise ValueError("No storage account specified for blob storage!")
                storageaccount_key = self.splunk.get_credentials(
                    self.eventhub.storageaccount,
                    realm=self.eventhub.blob_realm
                )
                kwargs.update({
                    'storage_account_name': self.eventhub.storageaccount,
                    'storage_account_key': storageaccount_key.content.clear_password,
                    'lease_container_name': self.eventhub.container
                })
            elif not self.eventhub.storage or self.eventhub.storage == 'file':
                kwargs.update({'storage_dir': self.checkpoint_dir})
            storage_manager = StorageManagerFactory.get_instance(self.eventhub.storage or 'file', **kwargs)
            host = EventProcessorHost(
                event_processor=SplunkEventProcessor,
                ep_params=[self.splunk],
                eh_config=eventhub_config,
                eph_options=opts,
                storage_manager=storage_manager,
                loop=loop
            )
            loop.run_until_complete(asyncio.gather(
                host.open_async(),
                wait_and_close(host, int(self.eventhub.run_duration))
            ))
        except Exception as e:
            # The EPH partition manager throws a generic exception, so we need a broad catch
            logger.error(f"Unable to retrieve events from EventHub {self.eventhub.event_hub}. "
                + f"Are all connection parameters correct?\nUnderlying error was: {repr(e)}")
        finally:
            loop.stop()


def do_scheme():
    print(SCHEME)


def print_error(s):
    print("<error><message>%s</message></error>" % saxutils.escape(s))


def validate_conf(config, key):
    if key not in config:
        raise Exception("Invalid configuration received from Splunk: key '%s' is missing." % key)


def get_validation_data():
    val_data = {}

    # parse the validation XML
    doc = minidom.parseString(script_input)
    root = doc.documentElement

    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data


def validate_blob_storage_args(conf):
    storage_type = conf["storage_type"]
    storage_account_key = conf["blob_storageaccount_key"]
    if storage_type != 'blob':
        raise Exception(f"Blob storage account value was set, but storage type is set to {storage_type}")
    if "blob_storageaccount_key" not in conf:
        raise Exception("Blob storage account value was set, but key value is missing.")
    if "blob_container" not in conf:
        raise Exception("Blob storage account value was set, but container value is missing.")
    if storage_account_key != PASSWORD_MASK:
        try:
            # attempt to connect to the Blob service to validate the configured credentials
            BlockBlobService(
                account_name=conf["blob_storageaccount"],
                account_key=storage_account_key
            ).list_containers()
        except Exception:
            raise Exception("Couldn't establish connection to Blob service - are the connection parameters correct?")


def validate_eventhub_connection(eventhub, namespace, sas_policy, sas_key):
    _client = EventHubClientAsync(
        'https://{}.servicebus.windows.net/{}'.format(namespace, eventhub),
        username=sas_policy,
        password=sas_key
    )


def validate_required_args(conf):
    validate_conf(conf, "eventhub_name")
    validate_conf(conf, "eventhub_namespace")
    validate_conf(conf, "sas_policy")
    validate_conf(conf, "sas_key")
    if conf["sas_key"] != PASSWORD_MASK:
        try:
            validate_eventhub_connection(
                conf["eventhub_name"],
                conf["eventhub_namespace"],
                conf["sas_policy"],
                conf["sas_key"]
            )
        except Exception:
            raise Exception("Could not establish connection to EventHub - are the connection parameters correct?")
    validate_conf(conf, "storage_type")
    if "blob_storageaccount" in conf:
        validate_blob_storage_args(conf)
    elif conf["storage_type"] == 'blob':
        raise Exception("Blob storage was selected, but storage account value is missing.")


def validate_arguments():
    val_data = get_validation_data()

    try:
        session_key = val_data.get('session_key', None)
        if session_key:
            eventhub = EventHub(**val_data)
            splunk = SplunkService(session_key=session_key, app=APP_NAME)
            validate_eventhub_connection(
                eventhub=eventhub.event_hub,
                namespace=eventhub.namespace,
                sas_policy=eventhub.sas_policy,
                sas_key=splunk.get_credentials(eventhub.sas_policy, realm=eventhub.realm)
            )
        else:  # if we don't have a session key, just check for required params
            validate_required_args(val_data)
    except Exception as e:
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(1)


# read XML configuration passed from splunkd
def get_config():
    config = {}

    try:
        # parse the config XML
        doc = minidom.parseString(script_input)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data

        node = root.getElementsByTagName('checkpoint_dir')[0]
        if node and node.firstChild and \
            node.firstChild.nodeType == node.firstChild.TEXT_NODE:
                config['checkpoint_dir'] = node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

        # make sure these keys are present (required)
        validate_required_args(config)
        validate_conf(config, "name")
        validate_conf(config, "checkpoint_dir")
    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))
    return config


def run():
    Consumer().execute()

def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    sys.exit(2)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        else:
            usage()
    else:
        run()

    sys.exit(0)
