import asyncio
import threading
import time
import string
import random
import configparser

from azure.eventprocessorhost import (
    EventHubConfig,
    EPHOptions,
    EventProcessorHost
)
from azure.eventhub import EventHubClientAsync, EventData

from eventhubconsumer.splunk_service import SplunkService
from eventhubconsumer.splunk_event_processor import SplunkEventProcessor
from eventhubconsumer.storage import StorageManagerFactory
from eventhubconsumer.test import Constants


WRITE_THREAD_COUNT = 5
MESSAGES_PER_WRITE = 5000
RUN_DURATION = 10

conf = configparser.ConfigParser()
conf.read(Constants.TEST_CONFIG_FILE.value)
eventhub_config = conf[Constants.EVENT_HUB.value]

SERVICE_BUS = eventhub_config[Constants.SERVICE_BUS.value]
EVENT_HUB = eventhub_config[Constants.EVENT_HUB.value]
SAS_POLICY = eventhub_config[Constants.SAS_POLICY.value]
print("Establishing Splunk connection...")
SPLUNK = SplunkService(**conf[Constants.SPLUNK.value])
SAS_KEY = SPLUNK.get_credentials(SAS_POLICY)

conf = EventHubConfig(
    sb_name=SERVICE_BUS,
    eh_name=EVENT_HUB,
    policy=SAS_POLICY,
    sas_key=SPLUNK.get_credentials(SAS_POLICY),
    consumer_group='$Default'
)

opts = EPHOptions()
opts.prefetch_count = 300
opts.max_batch_size = 300
opts.receive_timeout = 10

loop = asyncio.get_event_loop()

storage_manager = StorageManagerFactory.get_instance('file')
EPH = EventProcessorHost(
    event_processor=SplunkEventProcessor,
    ep_params=[SPLUNK],
    eh_config=conf,
    eph_options=opts,
    storage_manager=storage_manager,
    loop=loop
)


async def wait_and_close(h):
    await asyncio.sleep(RUN_DURATION)
    await h.close_async()


def generate_random_string(length=20, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(length))


class EventHubWriter(object):

    def __init__(self, service_bus, event_hub, sas_policy, sas_key):
        self._client = EventHubClientAsync(
            'https://{}.servicebus.windows.net/{}'.format(service_bus, event_hub),
            username=sas_policy,
            password=sas_key
        )

    def write(self, messages, partition_key='DEFAULT'):
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait([asyncio.ensure_future(self.__write_async(partition_key, messages))]))

    async def __write_async(self, partition_key, messages):
        writer = self._client.add_async_sender()
        await self._client.run_async()
        for message in messages:
            data = EventData(message)
            data.partition_key = partition_key.encode('utf-8')
            await writer.send(data)
        await writer.close_async()


print("Creating write connection...")
WRITER = EventHubWriter(
    service_bus=SERVICE_BUS,
    event_hub=EVENT_HUB,
    sas_policy=SAS_POLICY,
    sas_key=SAS_KEY
)


class EventHubWriteThread(threading.Thread):

    def __init__(self):
        super().__init__()
        print("Initializing write thread...")
        self._shutdown = threading.Event()
        self._event_hub = WRITER

    def run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._event_hub.write(
            messages=[generate_random_string() for _ in range(MESSAGES_PER_WRITE)]
        )
        asyncio.get_event_loop().close()

    def stop(self):
        self._shutdown.set()


def write_messages():
    threads = []

    for _ in range(WRITE_THREAD_COUNT):
        t = EventHubWriteThread()
        threads.append(t)
        t.start()

    print("Writing {} messages. This may take a while...".format(WRITE_THREAD_COUNT * MESSAGES_PER_WRITE))

    for t in threads:
        t.join()


def read_messages():
    print("Reading messages...")
    start = time.time()
    tasks = asyncio.gather(
        EPH.open_async(),
        wait_and_close(EPH)
    )
    loop.run_until_complete(tasks)
    print("Read took {}s".format(time.time() - start))


def load_test():
    write_messages()
    read_messages()


if __name__ == "__main__":
    load_test()
