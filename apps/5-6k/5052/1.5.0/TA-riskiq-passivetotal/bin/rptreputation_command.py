import ta_riskiq_passivetotal_declare    # noqa: F401
import sys
import traceback
import time
import json
import six

from errors import QueryFieldNotExistsError
from passivetotal_utils import setup_logging, nested_dict_iter
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from command_base import CommandPTClient

TAB = 'reputation'


@Configuration()
class RPTReputation(EventingCommand):
    """
    This command can be used as generating command as well as transforming command.

    When used as generating command, it returns reputaion events of the given IP addresses or Domain,
    When used as transforming command,
    it enriches the reputation information to the events that are returned from Splunk search.

    Generating command will have priority over transforming command.
    """

    query = Option(
        doc='''**Syntax:** **query=***<query>*
        **Description:** IP address/Domain for which repuation events needs to be retrieved from PassiveTotal''',
        name='query', require=False
    )

    query_field = Option(
        doc='''
        **Syntax:** **query_field=***<query_field>*
        **Description:** Name of the field representing query in Splunk events''',
        name='query_field', require=False
    )

    def fetch_reputation(self, query):
        """Fetch reputation data from API."""
        self.logger.info('Fetching reputation for query: {}'.format(query))
        params = {'query': query}
        return self.pt_client.get_tab(TAB, params)

    def make_splunk_event(self, event, query):
        """Make Splunk event out of given raw event."""
        splunk_event = {
            '_time': time.time(),
            '_raw': json.dumps(event)
        }

        # Show extracted fields on left side of Splunk Search UI
        splunk_event.update(nested_dict_iter(event))

        return splunk_event

    def get_reputation(self, query, logger):
        """Get final reputation event."""
        logger.info('Processing the query "{}"'.format(query))
        res = self.fetch_reputation(query)
        res['query'] = query
        event = self.make_splunk_event(res, query)
        return event

    def transform(self, records):
        """Enrich given records."""
        query = self.query
        query_field = self.query_field

        if getattr(self.search_results_info, "auth_token") is None:
            return

        session_key = self.search_results_info.auth_token
        logger = setup_logging(session_key=session_key)

        if (not self.search_results_info) or (self.metadata.preview):
            return

        start_time = time.time()

        if isinstance(query, six.string_types):
            query = query.strip()
        if isinstance(query_field, six.string_types):
            query_field = query_field.strip()

        if query and query_field:
            err_msg = (
                'Please use parameter "query" to make rptreputation work as generating command '
                'or use parameter "query_field" to make rptreputation work as transforming command.'
            )
            logger.error(err_msg)
            self.write_error(err_msg)
            exit(1)

        logger.info('Start rptrepuation command')
        processed_queries = set()
        count = 0
        try:
            self.pt_client = CommandPTClient(session_key)
            if query:
                # Act as a generating command
                logger.info('Parameters received: query="{}"'.format(query))

                event = self.get_reputation(query, logger)
                yield event
                count += 1

            elif query_field:
                # Act as a transforming command
                logger.info('Parameters received: query_field="{}"'.format(query_field))

                is_field_exists = False
                for record in records:
                    query = record.get(query_field)
                    if not query:
                        continue
                    is_field_exists = True

                    if isinstance(query, six.string_types):
                        if query in processed_queries:
                            continue
                        processed_queries.add(query)

                        event = self.get_reputation(query, logger)
                        yield event
                        count += 1

                    elif isinstance(query, list):
                        for query_ in query:
                            if query_ in processed_queries:
                                continue
                            processed_queries.add(query_)

                            try:
                                event = self.get_reputation(query_, logger)
                                yield event
                                count += 1
                            except Exception:
                                err_msg = 'Error occured while executing rptreputation command - Traceback: {}'.format(
                                    traceback.format_exc())
                                logger.error(err_msg)

                if not is_field_exists:
                    raise QueryFieldNotExistsError('Provided query_field does not exists in any events.')

            else:
                err_msg = "Please specify exactly one parameter from 'query' and 'query_field' with some value."
                logger.error(err_msg)
                self.write_error(err_msg)
                exit(1)

        except QueryFieldNotExistsError as ex:
            warn_msg = 'Warning: {}'.format(ex)
            logger.warning(warn_msg)
            self.write_warning(warn_msg)

        except Exception as ex:
            logger.error('Error occured while executing rptreputation command: Traceback: {}'.format(
                traceback.format_exc()))
            self.write_error('Error: {}'.format(ex))
            exit(1)

        end_time = time.time()

        logger.info('Total output events={}'.format(count))
        logger.info("Time taken to fetch all events is {} seconds".format(int(end_time - start_time)))
        logger.info("Completed the execution of rptreputation command")


dispatch(RPTReputation, sys.argv, sys.stdin, sys.stdout, __name__)
