import logging

from dataclasses import dataclass
from json import dumps, JSONDecodeError


class OrderProcessingError(Exception):
    """Base class for all custom exceptions raised during pipeline processing."""

    pass


@dataclass
class EmptyOrdersData(OrderProcessingError):
    """Raised when the API returns no order data to process."""

    response_body: dict


@dataclass
class InvalidJSONResponseError(OrderProcessingError):
    """Raised when the API returns a non-JSON response."""

    response_text: str


class MissingOrderNumberError(OrderProcessingError):
    """Raised when an order item is missing the required 'order_no' field."""

    pass


class OrderProcessingStepError(OrderProcessingError):
    """Base class for errors that occur within an individual pipeline step."""

    pass


class MalformedOrderItemError(OrderProcessingStepError):
    """Raised when an order item is missing an expected field or is structured incorrectly."""

    pass


class OrderPipeline:
    """A resilient pipeline that processes items through a series of steps.

    This pipeline is designed to be robust and maintainable. It isolates
    failures to individual items, passes a shared 'context' object through
    the steps, and returns a list of states to be saved by the caller.

    Attributes:
        steps: A tuple of step objects to be executed in sequence.
    """

    def __init__(self, *steps):
        self.steps = steps

    def execute(self, initial_input, **kwargs):
        """Executes the pipeline, processing each item through the defined steps.

        Args:
            initial_input: The first input to the pipeline, typically an HTTP
                response object.
            **kwargs: Arbitrary keyword arguments that will be added to the
                context for each processed item (e.g., checkpoint data).

        Returns:
            A list of state dictionaries to be saved. Each dictionary is the
            product of a successful run of the pipeline on a single item.

        Raises:
            Exception: Propagates any exception raised by the first
                (extraction) step, as this is considered a critical failure.
        """
        collected_states = []
        # Skip the first step, which is the extraction step.
        processing_steps = self.steps[1:]

        try:
            items_to_process = self.steps[0].execute(initial_input)
        except EmptyOrdersData as empty_orders_data_error:
            logging.info(
                f"API response contained no order data. Pipeline will not run. http_response={str(empty_orders_data_error.response_body)}"
            )
            return []
        except InvalidJSONResponseError as invalid_json_response_error:
            logging.info(
                f"Pipeline failed at initial extraction step http_response={invalid_json_response_error.response_text}",
            )
            return []

        for item in items_to_process:
            try:
                context = {"item": item, **kwargs}
                for step in processing_steps:
                    context = step.execute(context)

                if "state_to_save" in context:
                    collected_states.append(context["state_to_save"])

            except MissingOrderNumberError as missing_order_no_error:
                logging.info(
                    f"Skipping processing order due to missing required order number exception={str(missing_order_no_error)}"
                )
                continue
            except OrderProcessingStepError as order_processing_step_error:
                order_no = item.get("order_no", "UNKNOWN_ORDER")
                logging.info(
                    f"Order processing skipped due to error order_no={order_no} exception={str(order_processing_step_error)}",
                )
                continue

        return collected_states


class OrdersExtractFromAPIResponseStep:
    """Extracts a list of items from a raw API response.

    This step is expected to be the first in a pipeline. It looks for a 'hits'
    key in the JSON response body and returns its value.
    """

    @staticmethod
    def execute(response):
        """Extracts the 'hits' from the response.

        Args:
            response: A requests.Response object.

        Returns:
            A list of items found in the 'hits' key of the response JSON.

        Raises:
            EmptyOrdersData: If the 'hits' key is not found or is empty.
            InvalidJSONResponseError: If the response cannot be decoded as JSON.
        """
        try:
            response_json = response.json()
        except JSONDecodeError:
            raise InvalidJSONResponseError(response_text=response.text)

        hits = response_json.get("hits")

        if not hits:
            raise EmptyOrdersData(
                response_body=response_json,
            )

        return hits


class DictExtractValueByKeyStep:
    """Replaces the context's item with a value from a key within that item.

    This is useful for unwrapping nested objects during pipeline processing.

    Attributes:
        key: The key whose value will be extracted to become the new item.
    """

    def __init__(self, key):
        self.key = key

    def execute(self, context):
        """Executes the value extraction.

        Args:
            context: The shared context dictionary. Expects 'item' to be a
                dictionary containing the specified key.

        Returns:
            The modified context dictionary with 'item' updated.
        """
        context["item"] = context["item"][self.key]
        return context


class OrderInsertInIndexStep:
    """Inserts the processed item into a Splunk index.

    This step uses a provided Splunk indexer object to perform the insertion.

    Attributes:
        splunk_indexer: An object with an `insert` method for indexing data.
    """

    def __init__(self, splunk_indexer):
        self.splunk_indexer = splunk_indexer

    def execute(self, context):
        """Serializes the item to JSON and inserts it into Splunk.

        Args:
            context: The shared context dictionary.

        Returns:
            The context dictionary, unchanged.
        """
        order_str = dumps(context["item"])
        self.splunk_indexer.insert(order_str)
        return context


class OrderExtendEventWithStateStep:
    """Enriches an order item with data from its previously seen state.

    This step adds both a nested `previous_state` object and flattened
    `previous_state_*` fields to the order item for ease of use in Splunk.
    """

    def execute(self, context):
        """Executes the state enrichment.

        It looks for a 'checkpoint' object in the context to find the
        historical state data.

        Args:
            context: The shared context dictionary. May contain a 'checkpoint'
                object with historical data.

        Returns:
            The modified context dictionary with the 'item' potentially updated.
        """
        order = context["item"]
        checkpoint = context.get("checkpoint")

        if not checkpoint:
            return context

        try:
            order_id = order["order_no"]
            previous_state = checkpoint.data.get(order_id)

            if previous_state:
                order["previous_state"] = {
                    "status": previous_state.get("status"),
                    "payment_status": previous_state.get("payment_status"),
                    "export_status": previous_state.get("export_status"),
                    "shipping_status": previous_state.get("shipping_status"),
                }
                order["previous_state_status"] = previous_state.get("status")
                order["previous_state_payment_status"] = previous_state.get(
                    "payment_status"
                )
                order["previous_state_export_status"] = previous_state.get(
                    "export_status"
                )
                order["previous_state_shipping_status"] = previous_state.get(
                    "shipping_status"
                )

        except KeyError:
            raise MissingOrderNumberError(f"Missing an 'order_no' order={str(order)}")
        except Exception as exc:
            raise MalformedOrderItemError(
                f"Failed to enrich order due to an unexpected error exception={str(exc)}"
            )

        return context


class MapOrderToStateStep:
    """Maps an order item to a dictionary representing its checkpoint state.

    The resulting state dictionary is added to the context under the key
    'state_to_save', to be collected by the pipeline orchestrator.
    """

    def execute(self, context):
        """Executes the mapping.

        If the item lacks an 'order_no', an error will be logged and no
        state will be generated for that item.

        Args:
            context: The shared context dictionary.

        Returns:
            The modified context dictionary, potentially with a 'state_to_save'
            key added.
        """
        order = context["item"]
        try:
            order_state = {
                "order_id": order["order_no"],
                "status": order.get("status"),
                "payment_status": order.get("payment_status"),
                "export_status": order.get("export_status"),
                "shipping_status": order.get("shipping_status"),
                "last_ingested_at": order.get("last_modified"),
            }
            context["state_to_save"] = order_state
        except KeyError:
            raise MissingOrderNumberError(
                f"Cannot create order state because 'order_no' is missing order={str(order)}"
            )
        except Exception as exc:
            raise MalformedOrderItemError(
                f"Failed to map order to state due to an unexpected error exception={str(exc)}"
            )

        return context
