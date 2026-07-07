import os
import time
import sys

from datetime import datetime, timezone

from azure.eventprocessorhost import AbstractEventProcessor

from logger import logger

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"


class SplunkEventProcessor(AbstractEventProcessor):
    def __init__(self, params=None):
        super(SplunkEventProcessor, self).__init__(params)
        self._splunk = params[0]

    async def open_async(self, context):
        logger.info("Starting Splunk processor for partition {}".format(context.partition_id))
        logger.debug("Using token {}".format(context.host.eh_config.rest_token))

    async def close_async(self, context, reason):
        logger.info("Closing Splunk connection for partition {}: {}".format(
            context.partition_id, reason
        ))

    async def process_events_async(self, context, messages):
        start_time = time.time()
        logger.info("Received messages from partition {}\tOffset: {}\tSequence number: {}".format(
            context.partition_id, context.offset, context.sequence_number))
        processed_at = datetime.strftime(datetime.now(timezone.utc), DATETIME_FORMAT)
        for message in messages:
            # write a message to Splunk containing all relevant params
            print(("{}|message={}|eventhub={}|eh_namespace={}|sas_policy={}|" + 
                    "consumer_group={}|partition={}|offset={}|sequence_number={}").format(
                processed_at,
                message.body_as_str(),
                context.host.eh_config.eh_name,
                context.host.eh_config.sb_name,
                context.host.eh_config.policy,
                context.host.eh_config.consumer_group,
                context.partition_id,
                message.offset.value,
                message.sequence_number
            ))
        logger.debug("Batch read of {} messages took {}s".format(len(messages), time.time() - start_time))
        await context.checkpoint_async()

    async def process_error_async(self, context, error):
        logger.error("Error processing message from partition {} at offset {}: {}".format(
            context.partition_id, context.offset, error
        ))
